# -*- coding: utf-8 -*-
"""我的媒体库插件测试。

按 MoviePilot V3 约定，测试放在仓库根tests/v3/<plugin_id>/，
并以与生产一致的 app.plugins.<plugin_id> 路径导入插件源码。

这些测试只覆盖纯逻辑与安全边界，不触碰公网、真实媒体库或用户数据库。
"""

import importlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

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


class TestDoubanAutoFetch(unittest.TestCase):
    """豆瓣 ID 自动补齐：解析、挑选、缺漏检测与线程生命周期。

    这些测试不联网——网络入口 _douban_http_get 在需要时被替换。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _plugin(self) -> "MyLibrary":
        plugin = MyLibrary()
        plugin._library_path = str(self.root)
        return plugin

    # ---- 目录名解析 ----
    def test_parse_dirname_with_year(self):
        self.assertEqual(
            MyLibrary._douban_parse_dirname("碟中谍 (1996)"), ("碟中谍", "1996")
        )

    def test_parse_dirname_keeps_inner_spaces(self):
        self.assertEqual(
            MyLibrary._douban_parse_dirname("复仇者联盟 4 (2019)"),
            ("复仇者联盟 4", "2019"),
        )

    def test_parse_dirname_without_year(self):
        self.assertEqual(MyLibrary._douban_parse_dirname("国配经典"), ("国配经典", ""))

    # ---- 标题归一化 ----
    def test_normalize_ignores_punctuation_and_case(self):
        n = MyLibrary._douban_normalize
        self.assertEqual(n("Spider-Man: Homecoming"), n("spiderman homecoming"))
        self.assertEqual(n("无间道Ⅲ"), n("无间道Ⅲ"))

    # ---- 搜索结果解析 ----
    def test_parse_search_extracts_subject(self):
        html = (
            '<ul>'
            '<li><a href="/movie/subject/1292484/"><img src="a.jpg"/>'
            '<div class="subject-info"><span class="subject-title">碟中谍</span>'
            '<p class="subject-abstract">汤姆·克鲁斯 / 1996 / 动作</p></div></a></li>'
            '<li><a href="/movie/subject/1292484/">重复项</a></li>'
            '<li><a href="/movie/subject/1295644/"><div class="subject-info">'
            '<span class="subject-title">碟中谍2</span>'
            '<p class="subject-abstract">2000 / 动作</p></div></a></li>'
            '</ul>'
        )
        got = MyLibrary._douban_parse_search(html)
        self.assertEqual(got, [("1292484", "碟中谍", "1996"), ("1295644", "碟中谍2", "2000")])

    def test_parse_search_ignores_non_movie_links(self):
        html = '<li><a href="/book/subject/123/"><span class="subject-title">书</span></a></li>'
        self.assertEqual(MyLibrary._douban_parse_search(html), [])

    # ---- 反爬识别 ----
    def test_rate_limit_page_detected(self):
        page = '{"error_info": "搜索访问太频繁，请稍后再试"}'
        self.assertTrue(MyLibrary._douban_is_rate_limited(page))

    def test_normal_page_is_not_rate_limited(self):
        self.assertFalse(MyLibrary._douban_is_rate_limited("<li>正常结果</li>"))
        self.assertFalse(MyLibrary._douban_is_rate_limited(""))

    # ---- 候选挑选 ----
    def test_pick_prefers_matching_year(self):
        cands = [("111", "碟中谍", "2000"), ("222", "碟中谍", "1996")]
        sid, year = MyLibrary._douban_pick(cands, "碟中谍", "1996")
        self.assertEqual((sid, year), ("222", "1996"))

    def test_pick_rejects_unrelated_candidate(self):
        """宁可不给 id（前端回退搜索页），也不能挂错豆瓣链接。"""
        cands = [("999", "完全无关的电影", "2011")]
        self.assertEqual(MyLibrary._douban_pick(cands, "碟中谍", "1996"), (None, ""))

    def test_pick_handles_empty_candidates(self):
        self.assertEqual(MyLibrary._douban_pick([], "任意", "2000"), (None, ""))

    # ---- 缺漏检测 ----
    def test_todo_only_lists_dirs_with_nfo_and_no_id(self):
        (self.root / "缺失 (2020)").mkdir()
        (self.root / "缺失 (2020)" / "movie.nfo").write_text("<movie/>", encoding="utf-8")
        (self.root / "已缓存 (2019)").mkdir()
        (self.root / "已缓存 (2019)" / "movie.nfo").write_text("<movie/>", encoding="utf-8")
        (self.root / "没nfo (2018)").mkdir()
        (self.root / "没nfo (2018)" / "movie.mkv").write_bytes(b"x")
        (self.root / ".隐藏").mkdir()
        (self.root / ".douban_ids.json").write_text(
            '{"已缓存 (2019)": {"douban_id": "123"}}', encoding="utf-8"
        )
        todo = self._plugin()._douban_todo()
        self.assertEqual(todo, [("缺失 (2020)", "缺失", "2020")])

    def test_todo_skips_failed_in_this_session(self):
        (self.root / "查不到 (2020)").mkdir()
        (self.root / "查不到 (2020)" / "movie.nfo").write_text("<movie/>", encoding="utf-8")
        self.assertEqual(self._plugin()._douban_todo({"查不到 (2020)"}), [])

    def test_todo_empty_cache_returns_all_missing(self):
        for name in ("甲 (2001)", "乙 (2002)"):
            (self.root / name).mkdir()
            (self.root / name / "movie.nfo").write_text("<movie/>", encoding="utf-8")
        self.assertEqual(
            [t[0] for t in self._plugin()._douban_todo()], ["乙 (2002)", "甲 (2001)"]  # sorted 按目录名
        )

    def test_todo_without_library_path_is_empty(self):
        plugin = MyLibrary()
        self.assertEqual(plugin._douban_todo(), [])

    # ---- 落盘 ----
    def test_save_merges_and_keeps_existing_entries(self):
        cache = self.root / ".douban_ids.json"
        cache.write_text('{"旧片 (1990)": {"douban_id": "1"}}', encoding="utf-8")
        plugin = self._plugin()
        plugin._douban_save("新片 (2020)", "888", "新片", "2020", "2020")
        raw = json.loads(cache.read_text(encoding="utf-8"))
        self.assertEqual(raw["旧片 (1990)"]["douban_id"], "1")
        self.assertEqual(raw["新片 (2020)"]["douban_id"], "888")
        self.assertEqual(raw["新片 (2020)"]["match_year"], "2020")
        self.assertFalse((self.root / ".douban_ids.json.tmp").exists())

    def test_save_recovers_from_corrupt_cache(self):
        cache = self.root / ".douban_ids.json"
        cache.write_text("{ 坏文件", encoding="utf-8")
        self._plugin()._douban_save("新片 (2020)", "888", "新片", "2020")
        raw = json.loads(cache.read_text(encoding="utf-8"))
        self.assertEqual(raw["新片 (2020)"]["douban_id"], "888")

    def test_cache_written_by_plugin_is_readable(self):
        """自动补齐写出的格式必须与只读解析、与手动脚本保持一致。"""
        plugin = self._plugin()
        plugin._douban_save("新片 (2020)", "888", "新片", "2020", "2020")
        self.assertEqual(plugin._load_douban_ids(), {"新片 (2020)": "888"})

    # ---- 限流不落盘 ----
    def test_search_reports_rate_limit_without_candidates(self):
        plugin = self._plugin()
        with mock.patch.object(
            MyLibrary, "_douban_http_get", return_value='{"error_info":"搜索访问太频繁"}'
        ):
            cands, limited = plugin._douban_search("碟中谍")
        self.assertTrue(limited)
        self.assertEqual(cands, [])

    def test_search_parses_candidates_when_ok(self):
        html = ('<li><a href="/movie/subject/1292484/">'
                '<span class="subject-title">碟中谍</span><p>1996</p></a></li>')
        with mock.patch.object(MyLibrary, "_douban_http_get", return_value=html):
            cands, limited = MyLibrary._douban_search("碟中谍")
        self.assertFalse(limited)
        self.assertEqual(cands, [("1292484", "碟中谍", "1996")])

    # ---- 线程生命周期 ----
    def test_no_worker_when_plugin_disabled(self):
        plugin = self._plugin()
        plugin.init_plugin({"enabled": False, "library_path": str(self.root), "douban_auto": True})
        self.assertIsNone(plugin._douban_thread)

    def test_no_worker_when_auto_disabled(self):
        plugin = self._plugin()
        plugin.init_plugin({"enabled": True, "library_path": str(self.root), "douban_auto": False})
        self.assertIsNone(plugin._douban_thread)

    def test_worker_starts_and_stops_cleanly(self):
        plugin = self._plugin()
        plugin.init_plugin({"enabled": True, "library_path": str(self.root), "douban_auto": True})
        thread = plugin._douban_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.is_alive())
        plugin.stop_service()
        self.assertFalse(thread.is_alive())

    def test_reinit_does_not_stack_workers(self):
        """配置反复保存时不能越堆越多线程。"""
        plugin = self._plugin()
        cfg = {"enabled": True, "library_path": str(self.root), "douban_auto": True}
        plugin.init_plugin(cfg)
        first = plugin._douban_thread
        plugin.init_plugin(cfg)
        self.assertIsNot(first, plugin._douban_thread)
        self.assertFalse(first.is_alive())
        plugin.stop_service()

    def test_worker_with_nothing_missing_stays_idle(self):
        """没有待补条目时不得发起任何请求（豆瓣反爬经不起空转）。"""
        plugin = self._plugin()
        calls = []
        with mock.patch.object(
            MyLibrary, "_douban_http_get", side_effect=lambda *a, **k: calls.append(a) or ""
        ):
            plugin.init_plugin({"enabled": True, "library_path": str(self.root), "douban_auto": True})
            time.sleep(0.3)
            plugin.stop_service()
        self.assertEqual(calls, [])

    def test_get_form_defaults_auto_on(self):
        _, default = MyLibrary().get_form()
        self.assertTrue(default.get("douban_auto"))


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