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

# 官方门禁脚本输出中文；Windows 控制台默认 GBK 会直接抛 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

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


def run_official_gate(script: str, *args: str) -> None:
    """调用从官方仓库原样 vendor 的门禁脚本。

    这些脚本直接取自 jxxghp/MoviePilot-Plugins，判定逻辑与官方 CI 一致。
    本仓库不重写规则，避免两边漂移——自己写的近似实现曾经漏判过
    「package.json 版本跃迁」这类官方才有的约束。
    """
    path = ROOT / ".github" / "scripts" / script
    if not path.is_file():
        fail("缺少官方门禁脚本 %s" % script)
        return
    r = subprocess.run(
        [sys.executable, str(path), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    detail = (r.stdout or r.stderr or "").strip().splitlines()
    if r.returncode == 0:
        ok("%s -> %s" % (script, detail[-1] if detail else "通过"))
    else:
        fail("%s 失败：\n%s" % (script, "\n".join(detail[-12:])))


def check_versions() -> None:
    """版本一致性直接交给官方 check_plugin_versions.py 判定。"""
    print("\n=== 版本一致性（官方门禁）===")
    run_official_gate("check_plugin_versions.py", "package.v3.json")

    # 官方脚本不检查这两项，本仓库额外自查。
    index = json.loads(INDEX.read_text(encoding="utf-8"))["MyLibrary"]
    if index.get("release") is not True:
        fail("联邦插件必须在索引中设置 release: true")
    else:
        ok("release = true")
    if not str(index.get("system_version", "")).startswith(">="):
        fail("system_version 应为 PEP440（如 >=3.0.0）")
    else:
        ok("system_version = %s" % index["system_version"])


def check_federation_css() -> None:
    """联邦 CSS 隔离直接交给官方 check_federation_css.py 判定。"""
    print("\n=== 联邦 CSS 隔离（官方门禁）===")
    run_official_gate("check_federation_css.py", "--root", str(ROOT))


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
    """运行单元测试。

    走 tests/run.py（与官方仓库同一个回归入口），优先 pytest；
    环境未安装 pytest 时回退 unittest discover，让不装依赖的贡献者
    也能跑。两条路径都失败才算不通过。
    """
    print("\n=== 单元测试 ===")
    runner = ROOT / "tests" / "run.py"
    if not runner.is_file():
        fail("缺少 tests/run.py 回归入口")
        return

    attempts = (
        ("pytest", [sys.executable, str(runner), "-q"]),
        ("unittest", [
            sys.executable, "-m", "unittest", "discover",
            "-s", str(ROOT / "tests" / "v3" / PLUGIN_ID), "-p", "test_*.py",
        ]),
    )
    last_error = ""
    for name, cmd in attempts:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(ROOT))
        if r.returncode == 0:
            tail = (r.stdout or r.stderr or "").strip().splitlines()
            summary = next(
                (x for x in reversed(tail)
                 if "passed" in x or x.startswith("OK") or x.startswith("Ran ")),
                "全部通过",
            )
            ok("%s：%s" % (name, summary.strip()))
            return
        combined = (r.stdout or "") + (r.stderr or "")
        # 缺 pytest 时 Python 的报错文本在 3.10+ 带引号：No module named 'pytest'
        if "No module named" in combined and "pytest" in combined:
            continue  # 没装 pytest，换下一种方式
        last_error = combined.strip().splitlines()[-15:]
        break
    fail("测试失败：\n%s" % "\n".join(last_error or ["无法运行测试"]))


def check_compile() -> None:
    """Python 编译检查（官方清单第一项）。"""
    print("\n=== Python 编译 ===")
    targets = [INIT, ROOT / "tools" / "fetch_douban_ids.py"]
    targets += sorted((ROOT / "tests").rglob("*.py"))
    targets += sorted((ROOT / ".github").rglob("*.py"))
    for path in targets:
        if not path.is_file():
            continue
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            ok(path.relative_to(ROOT).as_posix())
        else:
            fail("编译失败 %s: %s" % (path.relative_to(ROOT), r.stderr.strip()[:200]))


def main() -> int:
    print("MoviePilot 插件发布前检查：%s" % ROOT)
    check_compile()
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