#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为媒体库每个影片获取豆瓣 subject id，缓存到 JSON 文件。

为什么需要它：nfo 里没有 <doubanid>，豆瓣网页版搜索又有反爬限流
（error_info: 搜索访问太频繁），因此这里用豆瓣移动版搜索接口 + 逐条校验标题年份，
只在 NAS 上跑一次并落盘，插件只读缓存、不实时请求豆瓣。

用法：
    python3 fetch_douban_ids.py <媒体库目录> [输出文件]

示例：
    python3 fetch_douban_ids.py /media/Videos/电影
    python3 fetch_douban_ids.py /media/Videos/电影 /media/Videos/电影/.douban_ids.json

输出（默认写入 <媒体库目录>/.douban_ids.json）：
    {
      "碟中谍 (1996)": {
        "douban_id": "1292484",
        "title": "碟中谍",
        "year": "1996"
      }
    }

脚本可重复运行：已缓存的条目会跳过，中断后可直接续跑。
注意：频繁请求可能触发豆瓣限流，脚本已内置 1.2 秒间隔，请勿并发运行。
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def http_get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Referer": "https://m.douban.com/"},
            )
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            if i == tries - 1:
                print("      ! 请求失败: %s" % e)
                return ""
            time.sleep(2 + i * 2)
    return ""


def normalize(s):
    """去掉标点、空白、全角半角差异，用于标题比较"""
    if not s:
        return ""
    s = urllib.parse.unquote(s)
    s = re.sub(r"[\s\-—–_·:：,，.。!！?？'\"“”‘’()（）\[\]【】/\\]+", "", s)
    return s.lower()


def search_ids(title, limit=8):
    """豆瓣移动版搜索，返回 [(id, 标题原文, 年份or空)]

    移动版结果结构（实测）：
        <li><a href="/movie/subject/1292484/">
          <img .../>
          <div class="subject-info">
            <span class="subject-title">碟中谍</span>
            <p class="subject-abstract">... 1996 ...</p>
    因此标题取 subject-title，年份在同一 <li> 块内再找四位年份。
    """
    q = urllib.parse.quote(title)
    html = http_get("https://m.douban.com/search/?query=%s" % q)
    if not html:
        return []
    out = []
    seen = set()
    # 按 <li> 块切分，每块内找 subject 链接 + subject-title + 年份
    for li in re.findall(r"<li>(.*?)</li>", html, re.S):
        m_id = re.search(r'/movie/subject/(\d+)/', li)
        if not m_id:
            continue
        sid = m_id.group(1)
        if sid in seen:
            continue
        m_t = re.search(r'class="subject-title"[^>]*>(.*?)<', li, re.S)
        title_txt = m_t.group(1).strip() if m_t else ""
        yr = ""
        ym = re.search(r"(19\d{2}|20\d{2})", re.sub(r"<[^>]+>", " ", li))
        if ym:
            yr = ym.group(1)
        seen.add(sid)
        out.append((sid, title_txt, yr))
        if len(out) >= limit:
            break
    return out


def pick(cands, want_title, want_year):
    """在候选中挑最匹配的一条：先按年份，再按标题相似度"""
    if not cands:
        return None, ""
    nt = normalize(want_title)
    wy = str(want_year or "")

    scored = []
    for sid, t, y in cands:
        nt_c = normalize(t)
        score = 0
        if wy and y == wy:
            score += 100          # 年份完全一致，权重最高
        elif wy and y:
            score += max(0, 30 - abs(int(y) - int(wy))) * 2
        if nt and nt_c:
            if nt_c == nt:
                score += 60       # 标题完全一致
            elif nt in nt_c or nt_c in nt:
                score += 35       # 一方包含另一方
            else:
                common = len(set(nt) & set(nt_c))
                score += int(common / max(len(nt), len(nt_c)) * 30)
        scored.append((score, sid, t, y))

    scored.sort(reverse=True)
    best = scored[0]
    # 阈值：太不像就不给，避免挂错链接
    if best[0] < 35:
        return None, ""
    return best[1], best[3]


def main():
    ap = argparse.ArgumentParser(
        description="抓取豆瓣 subject id 并缓存，供「我的媒体库」插件生成豆瓣链接",
    )
    ap.add_argument("library", help="媒体库目录，例如 /media/Videos/电影")
    ap.add_argument(
        "-o", "--output",
        help="输出 JSON 路径（默认 <媒体库目录>/.douban_ids.json）",
    )
    ap.add_argument(
        "--delay", type=float, default=1.2,
        help="每次请求间隔秒数（默认 1.2，调小易触发豆瓣限流）",
    )
    args = ap.parse_args()

    lib = args.library
    out = args.output or os.path.join(lib, ".douban_ids.json")

    if not os.path.isdir(lib):
        print("媒体库目录不存在: %s" % lib)
        sys.exit(1)

    cache = {}
    if os.path.exists(out):
        try:
            cache = json.load(open(out, encoding="utf-8"))
        except Exception:
            cache = {}

    dirs = sorted(d for d in os.listdir(lib)
                  if os.path.isdir(os.path.join(lib, d)) and not d.startswith("."))
    todo = []
    for d in dirs:
        p = os.path.join(lib, d)
        nfos = [f for f in os.listdir(p) if f.lower().endswith(".nfo")]
        if not nfos:
            continue
        todo.append(d)

    print("扫描到 %d 个影片目录，已缓存 %d 条" % (len(todo), len(cache)))
    ok = 0
    fail = []
    for i, d in enumerate(todo, 1):
        if d in cache and cache[d].get("douban_id"):
            continue
        # 从目录名解析：中文名 (年份)
        m = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", d)
        if m:
            title, year = m.group(1).strip(), m.group(2)
        else:
            title, year = d, ""

        cands = search_ids(title)
        sid, got_year = pick(cands, title, year)
        if sid:
            cache[d] = {"douban_id": sid, "title": title, "year": year, "match_year": got_year}
            ok += 1
            print("[%2d/%2d] OK   %-40s -> %s (%s)" % (i, len(todo), d[:40], sid, got_year))
        else:
            fail.append(d)
            print("[%2d/%2d] FAIL %-40s (候选 %d)" % (i, len(todo), d[:40], len(cands)))
        # 每条都落盘，中断可续
        with open(out, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        time.sleep(args.delay)   # 放慢，别把豆瓣打到限流

    print("\n完成：成功 %d，失败 %d，已写入 %s" % (ok, len(fail), out))
    if fail:
        print("失败列表（多为罗马数字/译名差异，可手工核对后补入 JSON）：")
        for f in fail:
            print("  -", f)


if __name__ == "__main__":
    main()