# -*- coding: utf-8 -*-
"""我的媒体库插件测试。

按 MoviePilot V3 约定，测试放在仓库根tests/v3/<plugin_id>/，
并以与生产一致的 app.plugins.<plugin_id> 路径导入插件源码。

这些测试只覆盖纯逻辑与安全边界，不触碰公网、真实媒体库或用户数据库。
"""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = REPO_ROOT / "plugins.v3" / "mylibrary"


def _ensure_host_stub() -> None:
    """在没有 MoviePilot 宿主时注入最小 _PluginBase 桩。

    官方推荐用宿主 .venv 跑测试（../MoviePilot/.venv/bin/python -m pytest），
    这样走的是真实 app.plugins 导入路径。本函数只用于仓库独立运行测试的兜底场景，
    让 CI 或贡献者不装宿主也能跑纯逻辑断言——桩只提供插件用到的接口。
    """
    try:
        import app.plugins  # noqa: F401
        return
    except ImportError:
        pass

    import types

    class _PluginBase:
        """最小宿主桩，仅覆盖插件声明过的接口。"""

        def __init__(self, *args, **kwargs):
            pass

        def init_plugin(self, config=None):
            pass

        def get_state(self):
            return True

        def get_form(self):
            return [], {}

        def get_api(self):
            return []

        def get_page(self):
            return []

        def stop_service(self):
            pass

    app_mod = types.ModuleType("app")
    plugins_mod = types.ModuleType("app.plugins")
    plugins_mod._PluginBase = _PluginBase
    app_mod.plugins = plugins_mod
    sys.modules["app"] = app_mod
    sys.modules["app.plugins"] = plugins_mod

    # 海报接口返回 fastapi Response；独立跑测试时用等价桩替代。
    try:
        import fastapi  # noqa: F401
        return
    except ImportError:
        pass

    class _Response:
        """最小 Response 桩，字段与 fastapi.responses.Response 对齐。"""

        def __init__(self, content=b"", status_code=200, media_type=None):
            self.body = content
            self.status_code = status_code
            self.media_type = media_type

    fastapi_mod = types.ModuleType("fastapi")
    responses_mod = types.ModuleType("fastapi.responses")
    responses_mod.Response = _Response
    fastapi_mod.responses = responses_mod
    sys.modules["fastapi"] = fastapi_mod
    sys.modules["fastapi.responses"] = responses_mod


def _load_plugin_module():
    """按 app.plugins.mylibrary 路径加载插件，缺失宿主时回退到文件路径。

    官方要求优先使用与生产一致的模块路径，避免同一插件以两个模块名
    重复加载、重复执行注册副作用；宿主不在本仓库时用文件路径兜底。
    """
    _ensure_host_stub()
    try:
        return importlib.import_module("app.plugins.mylibrary")
    except Exception:
        pass
    spec = importlib.util.spec_from_file_location(
        "mylibrary_under_test", PLUGIN_DIR / "__init__.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["mylibrary_under_test"] = module
    spec.loader.exec_module(module)
    return module


mod = _load_plugin_module()
MyLibrary = mod.MyLibrary


class _NfoBuilder:
    """在临时目录里写真实 nfo 文件——插件用 ET.parse 收路径，不收 Element。"""

    def __init__(self, base: Path):
        self.base = base
        self.count = 0

    def write(self, tag="movie", **fields):
        self.count += 1
        parts = []
        for key, value in fields.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                for item in value:
                    parts.append("  <%s>%s</%s>" % (key, item, key))
            else:
                parts.append("  <%s>%s</%s>" % (key, value, key))
        path = self.base / ("test%d.nfo" % self.count)
        path.write_text(
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<%s>\n%s\n</%s>\n"
            % (tag, "\n".join(parts), tag),
            encoding="utf-8",
        )
        return path


class TestMetadataParsing(unittest.TestCase):
    """nfo 解析：只提取存在的字段，缺字段不报错。"""

    def setUp(self):
        self.plugin = MyLibrary()
        self.tmp = tempfile.TemporaryDirectory()
        self.nfo = _NfoBuilder(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_basic_fields(self):
        f = self.nfo.write(
            tag="movie",
            title="星际穿越",
            year=2014,
            plot="一段关于宇宙的故事",
            rating="8.6",
        )
        meta = self.plugin._parse_nfo([f])
        self.assertEqual(meta.get("title"), "星际穿越")
        self.assertEqual(meta.get("year"), "2014")
        self.assertEqual(meta.get("rating"), "8.6")
        self.assertIn("宇宙", meta.get("overview", ""))

    def test_missing_fields_do_not_raise(self):
        f = self.nfo.write(tag="movie", title="只有一个标题")
        meta = self.plugin._parse_nfo([f])
        self.assertEqual(meta.get("title"), "只有一个标题")
        self.assertEqual(meta.get("rating", ""), "")

    def test_multiple_nfo_files_are_merged(self):
        """剧集常有 tvshow.nfo + 单集 nfo，后者不应覆盖前者的片名与简介。"""
        a = self.nfo.write(tag="tvshow", title="剧名", year=2018, plot="总简介")
        b = self.nfo.write(tag="episode", title="第一集")
        meta = self.plugin._parse_nfo([a, b])
        self.assertEqual(meta.get("title"), "剧名")
        self.assertIn("总简介", meta.get("overview", ""))

    def test_no_nfo_returns_empty(self):
        self.assertEqual(self.plugin._parse_nfo([]), {})

    def test_malformed_nfo_is_skipped_not_fatal(self):
        bad = Path(self.tmp.name) / "broken.nfo"
        bad.write_text("<movie><title>未闭合", encoding="utf-8")
        good = self.nfo.write(tag="movie", title="好文件")
        meta = self.plugin._parse_nfo([bad, good])
        self.assertEqual(meta.get("title"), "好文件")


class TestPathSafety(unittest.TestCase):
    """海报接口的目录穿越防护：这是插件唯一对外暴露的文件读取入口。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "影片 (2020)").mkdir()
        (self.root / "影片 (2020)" / "poster.jpg").write_bytes(b"fake-jpeg")
        self.plugin = MyLibrary()
        self.plugin._library_path = str(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_traversal_is_blocked(self):
        for evil in ("../../etc/passwd", "../secret.txt", "/etc/passwd"):
            resp = self.plugin.api_poster(path=evil)
            self.assertIn(
                resp.status_code, (403, 404),
                "目录穿越必须被拒绝: %s -> %s" % (evil, resp.status_code),
            )

    def test_valid_path_is_served(self):
        resp = self.plugin.api_poster(path="影片 (2020)/poster.jpg")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, b"fake-jpeg")

    def test_empty_path_is_404(self):
        self.assertEqual(self.plugin.api_poster(path="").status_code, 404)


class TestHumanSize(unittest.TestCase):
    """体积格式化：纯展示逻辑。"""

    def test_formats_bytes(self):
        f = MyLibrary._human_size
        self.assertEqual(f(0), "0 B")
        self.assertIn("KB", f(1024))
        self.assertIn("MB", f(1024 * 1024))
        self.assertIn("GB", f(3 * 1024 ** 3))


class TestDoubanCache(unittest.TestCase):
    """豆瓣 id 缓存：只读 .douban_ids.json，格式异常时必须静默降级。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        plugin = MyLibrary()
        plugin._library_path = str(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_cache_returns_empty(self):
        plugin = MyLibrary()
        plugin._library_path = str(self.root)
        self.assertEqual(plugin._load_douban_ids(), {})

    def test_valid_cache_is_parsed(self):
        (self.root / ".douban_ids.json").write_text(
            '{"碟中谍 (1996)": {"douban_id": "1292484"}}', encoding="utf-8"
        )
        plugin = MyLibrary()
        plugin._library_path = str(self.root)
        self.assertEqual(plugin._load_douban_ids(), {"碟中谍 (1996)": "1292484"})

    def test_corrupt_cache_degrades_quietly(self):
        (self.root / ".douban_ids.json").write_text("{ not json", encoding="utf-8")
        plugin = MyLibrary()
        plugin._library_path = str(self.root)
        self.assertEqual(plugin._load_douban_ids(), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)