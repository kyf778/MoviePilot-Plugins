"""插件仓测试回归入口。

官方 tests/run.py 会按代际（ci / v3 / v2）分独立子进程运行，避免同名插件包
互相覆盖。本仓库目前只有 V3 插件，因此只保留 v3 分组，但保留同样的结构，
将来新增插件或 CI 工具用例时可以直接扩展。

用法：
    python tests/run.py            # 运行全部测试
    python tests/run.py -v         # 透传 pytest 参数
"""
import subprocess
import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parent

# 按代际顺序运行，各分组使用独立子进程
GENERATIONS = ("ci", "v3", "v2")


def _contains_tests(path: Path) -> bool:
    """判断目录中是否存在测试用例文件。"""
    return path.is_dir() and any(path.rglob("test_*.py"))


def _generation_targets(generation: str) -> list[Path]:
    """返回一个独立 pytest 会话需要执行的测试目标。"""
    target = _TESTS_DIR / generation
    return [target] if _contains_tests(target) else []


def _run_generation(generation: str, extra_args: list) -> int:
    """在独立子进程运行一个测试分组；该组无用例则跳过。"""
    targets = _generation_targets(generation)
    if not targets:
        return 0
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "pytest",
            *(str(target) for target in targets),
            *extra_args,
        ],
        cwd=str(_REPO_ROOT),
    )


if __name__ == "__main__":
    extra = sys.argv[1:]
    exit_code = 0
    ran_any = False
    for generation in GENERATIONS:
        targets = _generation_targets(generation)
        if not targets:
            continue
        ran_any = True
        print(f"\n===== 运行 {generation} 测试 =====", flush=True)
        exit_code = exit_code or _run_generation(generation, extra)

    if not ran_any:
        print("没有找到测试用例，退出码 0（跳过）")
    sys.exit(exit_code)