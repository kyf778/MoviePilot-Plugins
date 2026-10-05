#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布前一致性校验（按 MoviePilot-Plugins 官方提交规则）"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.join(ROOT, "package.v3.json")
PLUGIN_DIR = os.path.join(ROOT, "plugins.v3", "mylibrary")
INIT = os.path.join(PLUGIN_DIR, "__init__.py")

fails = []


def ok(msg):
    print("  [OK]   %s" % msg)


def bad(msg):
    print("  [FAIL] %s" % msg)
    fails.append(msg)


print("=== 1. Python 编译 ===")
for f in [INIT, os.path.join(ROOT, "tools", "fetch_douban_ids.py")]:
    r = subprocess.run([sys.executable, "-m", "py_compile", f],
                       capture_output=True, text=True)
    if r.returncode == 0:
        ok(os.path.relpath(f, ROOT))
    else:
        bad("%s 编译失败: %s" % (f, r.stderr.strip()[:200]))

print("\n=== 2. 版本一致性 ===")
idx = json.load(open(IDX, encoding="utf-8"))["MyLibrary"]
src = open(INIT, encoding="utf-8").read()
pv = re.search(r'plugin_version\s*=\s*"([^"]+)"', src).group(1)
iv = idx["version"]
hv = list(idx["history"].keys())[0]
print("  plugin_version = %s" % pv)
print("  索引 version   = %s" % iv)
print("  history 首项   = %s" % hv)
if pv == iv == hv.replace("v", ""):
    ok("三者一致")
else:
    bad("版本不一致")

print("\n=== 3. history 降序排列 ===")
keys = list(idx["history"].keys())
expect = sorted(keys, key=lambda s: [int(x) for x in s.lstrip("v").split(".")],
                reverse=True)
if keys == expect:
    ok("降序正确")
else:
    bad("history 未按语义版本降序: %s" % keys)

print("\n=== 4. 目录名 = 主类名小写 ===")
cls = re.search(r"^class (\w+)", src, re.M).group(1)
if cls.lower() == "mylibrary":
    ok("%s -> %s" % (cls, "mylibrary"))
else:
    bad("主类 %s 与目录 mylibrary 不匹配" % cls)

print("\n=== 5. 索引必需字段 ===")
req = ["id", "name", "description", "author", "version", "labels",
       "category", "icon", "system_version", "history"]
miss = [k for k in req if k not in idx]
if miss:
    bad("缺字段: %s" % miss)
else:
    ok("齐全")

print("\n=== 6. system_version 为 PEP440 ===")
sv = idx.get("system_version", "")
if sv.startswith(">="):
    ok(sv)
else:
    bad("system_version 应形如 '>=3.0.0'，当前 %r" % sv)

print("\n=== 7. 无个人路径/内网地址泄漏 ===")
leaks = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames
                   if d not in ("node_modules", ".git", "__pycache__")]
    for fn in filenames:
        if not fn.endswith((".py", ".md", ".json", ".vue", ".js")):
            continue
        if fn == os.path.basename(__file__):
            continue   # 校验器自身包含检测用的模式串，跳过
        p = os.path.join(dirpath, fn)
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for pat in [r"192\.168\.\d+\.\d+", r"/vol2/", r"nastools", r"Iz1rMI6I"]:
            if re.search(pat, txt):
                leaks.append("%s -> %s" % (os.path.relpath(p, ROOT), pat))
if leaks:
    for l in leaks:
        bad("泄漏: %s" % l)
else:
    ok("无个人路径/内网地址")

print("\n=== 8. 构建产物存在 ===")
dist = os.path.join(PLUGIN_DIR, "dist", "assets")
if os.path.isfile(os.path.join(dist, "remoteEntry.js")):
    n = len(os.listdir(dist))
    ok("dist/assets 存在（%d 个文件，含 remoteEntry.js）" % n)
else:
    bad("缺少 dist/assets/remoteEntry.js")

print("\n=== 9. 图标可访问 ===")
icon_url = idx.get("icon", "")
if icon_url.startswith("https://raw.githubusercontent.com/"):
    ok(icon_url)
else:
    bad("icon 应为 raw.githubusercontent.com 完整 URL")

print("\n" + "=" * 46)
if fails:
    print("校验未通过，共 %d 项：" % len(fails))
    for f in fails:
        print("  - %s" % f)
    sys.exit(1)
print("全部校验通过 ✅")