#!/usr/bin/env python3
"""发布前统一检查：官方 CSS 门禁 + 版本一致性 + 隐私扫描。

官方文档要求提交前运行版本门禁、CSS 门禁与 git diff --check。
本脚本把可自动化的部分收拢成一条命令，避免漏项。

用法：
    python .github/scripts/preflight.py
退出码 0 表示全部通过。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ID = "mylibrary"
PLUGIN_DIR = ROOT / "plugins.v3" / PLUGIN_ID
INIT = PLUGIN_DIR / "__init__.py"
INDEX = ROOT / "package.v3.json"

errors: list[str] = []


def fail(msg: str) -> None:
    print("  [FAIL] %s" % msg)
    errors.append(msg)


def ok(msg: str) -> None:
    print("  [OK]   %s" % msg)


def check_versions() -> None:
    """plugin_version、索引 version、最新 history 三者必须一致（官方硬性规则）。"""
    print("\n=== 版本一致性 ===")
    src = INIT.read_text(encoding="utf-8")
    plugin_version = re.search(r'plugin_version\s*=\s*"([^"]+)"', src).group(1)
    index = json.loads(INDEX.read_text(encoding="utf-8"))["MyLibrary"]
    index_version = index["version"]
    history = list(index["history"].keys())
    latest = history[0]
    if plugin_version == index_version == latest.lstrip("v"):
        ok("plugin_version / index / history 一致：%s" % plugin_version)
    else:
        fail(
            "版本不一致：plugin_version=%s, index=%s, history=%s"
            % (plugin_version, index_version, latest)
        )

    keys = list(index["history"].keys())
    ordered = sorted(
        keys, key=lambda s: [int(x) for x in s.lstrip("v").split(".")], reverse=True
    )
    if keys == ordered:
        ok("history 按语义版本降序")
    else:
        fail("history 未降序：%s" % keys)

    if not index.get("system_version", "").startswith(">="):
        fail(
            "system_version 应为 PEP440（如 >=3.0.0），当前 %r"
            % index.get("system_version")
        )
    else:
        ok("system_version = %s" % index["system_version"])

    if index.get("release") is not True:
        fail("联邦插件必须在索引中设置 release: true")
    else:
        ok("release = true")


def check_federation_css() -> None:
    """不得发布 Vuetify/MDI 全局基础样式（官方 8.3 强制要求）。"""
    print("\n=== 联邦 CSS 隔离（官方门禁）===")
    shared = sorted(PLUGIN_DIR.glob("**/__federation_shared_vuetify/styles-*.css"))
    for css in shared:
        fail("%s: 不得发布 Vuetify 共享基础样式" % css.relative_to(ROOT))

    remote_entries = sorted(PLUGIN_DIR.glob("**/remoteEntry.js"))
    if not remote_entries:
        fail("缺少 remoteEntry.js，前端可能未构建")
        return
    for entry in remote_entries:
        text = entry.read_text(encoding="utf-8")
        for array_source in re.findall(
            r"dynamicLoadingCss\s*\(\s*\[([^]]*)]", text, re.DOTALL
        ):
            for css_path in re.findall(r"['\"]([^'\"]+\.css)['\"]", array_source):
                target = (entry.parent / css_path).resolve()
                if not target.is_file():
                    fail("remoteEntry 引用的 CSS 不存在：%s" % css_path)
    if not errors:
        ok("remoteEntry 引用的 CSS 均存在，且无 Vuetify 共享样式")


def check_no_leaks() -> None:
    """仓库不得包含个人路径、内网地址或凭据。"""
    print("\n=== 隐私扫描 ===")
    patterns = [
        (r"192\.168\.\d+\.\d+", "内网 IP"),
        (r"/vol2/1000/", "个人 NAS 路径"),
        (r"sk-[A-Za-z0-9]{16,}", "疑似密钥"),
        (r"gh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    ]
    leaks = []
    skip_dirs = {"node_modules", ".git", "__pycache__"}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix not in {".py", ".md", ".json", ".vue", ".js", ".css"}:
            continue
        if path.name == Path(__file__).name:
            continue  # 本脚本含检测模式串
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, label in patterns:
            if re.search(pattern, text):
                leaks.append("%s -> %s" % (path.relative_to(ROOT), label))
    for leak in leaks:
        fail("泄漏：%s" % leak)
    if not leaks:
        ok("无个人路径 / 内网地址 / 凭据")


def check_tests() -> None:
    """运行单元测试。"""
    print("\n=== 单元测试 ===")
    tests = ROOT / "tests" / "v3" / PLUGIN_ID
    if not tests.is_dir():
        fail("缺少 tests/v3/%s/" % PLUGIN_ID)
        return
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover",
         "-s", str(tests), "-p", "test_*.py"],
        capture_output=True, text=True,
    )
    tail = (r.stderr or r.stdout).strip().splitlines()
    if r.returncode == 0:
        summary = [x for x in tail if x.startswith("Ran ") or x.startswith("OK")]
        ok(" ".join(summary) or "全部通过")
    else:
        fail("测试失败：\n%s" % "\n".join(tail[-15:]))


def main() -> int:
    print("MoviePilot 插件发布前检查：%s" % ROOT)
    check_versions()
    check_federation_css()
    check_no_leaks()
    check_tests()

    print("\n" + "=" * 50)
    if errors:
        print("检查未通过，共 %d 项：" % len(errors))
        for e in errors:
            print("  - %s" % e)
        return 1
    print("全部检查通过，可以提交")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())