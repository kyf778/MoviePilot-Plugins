"""
我的媒体库插件（Vue 联邦版）。

MoviePilot 官方前端没有任何"本地片库浏览"页面，本插件补上这一块：
直接扫描配置的媒体库目录，读取 nfo 元数据与本地海报，
通过 Vue 联邦组件在主界面左侧导航栏渲染片库海报墙。

数据来源完全本地（目录 + nfo + poster.jpg），
不依赖媒体服务器，因此 Emby/飞牛影视/Plex 是否接入都不影响。
"""
from __future__ import annotations

import json
import mimetypes
import re
import ssl
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from app.plugins import _PluginBase

# 视频扩展名
MEDIA_EXTS = (".mkv", ".mp4", ".avi", ".mov", ".ts", ".m2ts", ".wmv", ".flv", ".rmvb", ".iso")

# 豆瓣缓存文件名
DOUBAN_CACHE_FILE = ".douban_ids.json"

# 移动版 UA：豆瓣对桌面版搜索限流更狠，移动版接口更宽松
DOUBAN_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

_DOUBAN_CTX = ssl.create_default_context()
_DOUBAN_CTX.check_hostname = False
_DOUBAN_CTX.verify_mode = ssl.CERT_NONE

# 两次豆瓣请求之间的最小间隔（秒）。豆瓣反爬阈值很低，实测 1.2 秒安全。
DOUBAN_DELAY = 1.2
# 一轮补齐结束后，隔多久再看有没有新片入库（秒）
DOUBAN_IDLE = 300
# 触发反爬后的冷却时间（秒）
DOUBAN_COOLDOWN = 1800


class MyLibrary(_PluginBase):
    """在 MoviePilot 内浏览本地媒体库的插件。"""

    plugin_name = "我的媒体库"
    plugin_desc = "在 MoviePilot 左侧导航栏浏览本地媒体库：读取 nfo 元数据与本地图片，展示片库海报墙。"
    plugin_icon = "https://raw.githubusercontent.com/kyf778/MoviePilot-Plugins/main/icons/mylibrary.png"
    plugin_version = "3.4.0"
    plugin_author = "kyf778"
    author_url = "https://github.com/kyf778"
    plugin_config_prefix = "mylibrary_"
    plugin_order = 60
    plugin_label = "媒体展示"
    auth_level = 1

    _enabled: bool = False
    _library_path: str = ""
    _poster_size: str = "medium"
    _douban_auto: bool = True
    _douban_thread: Optional[threading.Thread] = None
    _douban_stop: Optional[threading.Event] = None
    _douban_lock: threading.Lock = threading.Lock()

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """根据插件配置初始化运行状态。"""
        # 配置可能被反复保存，先把上一轮的后台线程收掉，避免线程越堆越多
        self._stop_douban_worker()

        self._enabled = False
        self._library_path = ""
        self._poster_size = "medium"
        self._douban_auto = True
        if not config:
            return
        self._enabled = bool(config.get("enabled", False))
        self._library_path = (config.get("library_path") or "").strip()
        self._poster_size = config.get("poster_size") or "medium"
        # 老配置里没有这个键，按"开启"处理（本特性的意义就在于免手动）
        self._douban_auto = bool(config.get("douban_auto", True))

        if self._enabled and self._library_path and self._douban_auto:
            self._start_douban_worker()

    def get_state(self) -> bool:
        """获取插件启用状态。"""
        return self._enabled

    @staticmethod
    def get_render_mode() -> Tuple[str, str]:
        """声明插件使用 Vue 联邦组件渲染（侧栏入口的前置条件）。"""
        return "vue", "dist/assets"

    def get_sidebar_nav(self) -> List[Dict[str, Any]]:
        """声明插件在主界面左侧导航栏中的全页入口。"""
        if not self.get_state():
            return []
        return [
            {
                "nav_key": "main",
                "title": "我的媒体库",
                "icon": "mdi-movie-open",
                "section": "organize",
                "permission": "manage",
                "order": 44,
            }
        ]

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """返回插件远程命令列表。"""
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        """返回插件 API 列表（Vue 组件通过 api prop 调用）。"""
        return [
            {
                "path": "/library",
                "endpoint": self.api_library,
                "methods": ["GET"],
                "summary": "获取媒体库扫描结果",
                "auth": "bear",
            },
            {
                "path": "/poster",
                "endpoint": self.api_poster,
                "methods": ["GET"],
                "summary": "获取本地海报图片",
                "allow_anonymous": True,
            },
        ]

    def get_form(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Vue 模式下返回默认配置模型（设置页由 Config 组件渲染）。"""
        return [], {
            "enabled": False,
            "library_path": "",
            "poster_size": "medium",
            "douban_auto": True,
        }

    def get_page(self) -> List[Dict[str, Any]]:
        """Vue 模式下详情页由远程 Page 组件渲染。"""
        return []

    # ------------------------------------------------------------------
    # 插件 API
    # ------------------------------------------------------------------
    def api_library(self) -> Dict[str, Any]:
        """扫描媒体库并返回海报墙数据（供 Vue AppPage 组件渲染）。"""
        items = self._scan()
        for item in items:
            if item.get("has_poster"):
                qs = quote(f"{item['dir_name']}/{item['poster_name']}")
                item["poster_url"] = f"/api/v1/plugin/MyLibrary/poster?path={qs}"
            else:
                item["poster_url"] = ""
            item["size_display"] = self._human_size(item["size_bytes"])
            item.pop("poster_name", None)

        movies = [x for x in items if x["type"] == "电影"]
        tvs = [x for x in items if x["type"] == "电视剧"]
        return {
            "success": True,
            "message": "",
            "data": {
                "items": items,
                "summary": {
                    "total": len(items),
                    "movies": len(movies),
                    "tvs": len(tvs),
                    "total_size": self._human_size(sum(x["size_bytes"] for x in items)),
                },
                "library_path": self._library_path,
            },
        }

    def api_poster(self, path: str = "") -> Any:
        """按相对路径返回本地海报图片（防目录穿越）。"""
        from fastapi.responses import Response

        root = Path(self._library_path or "")
        if not root or not path:
            return Response(status_code=404)
        try:
            target = (root / path).resolve()
            # 防目录穿越
            if not str(target).startswith(str(root.resolve())):
                return Response(status_code=403)
            if not target.is_file():
                return Response(status_code=404)
            ctype = mimetypes.guess_type(str(target))[0] or "image/jpeg"
            return Response(content=target.read_bytes(), media_type=ctype)
        except Exception:
            return Response(status_code=500)

    # ------------------------------------------------------------------
    # 媒体库扫描
    # ------------------------------------------------------------------
    def _load_douban_ids(self) -> Dict[str, str]:
        """读取豆瓣 subject id 缓存。

        nfo 里没有 <doubanid>（实测 0/50），豆瓣又有反爬，所以缓存文件
        .douban_ids.json 由两条途径产生：插件后台线程自动补齐（_douban_worker），
        或手动跑 tools/fetch_douban_ids.py。本方法只读，从不写入。
        """
        if not self._library_path:
            return {}
        cache_file = Path(self._library_path) / DOUBAN_CACHE_FILE
        if not cache_file.is_file():
            return {}
        try:
            raw = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {
            k: (v or {}).get("douban_id") or ""
            for k, v in (raw or {}).items()
            if isinstance(v, dict)
        }

    # ------------------------------------------------------------------
    # 豆瓣 ID 自动补齐（后台线程）
    #
    # 为什么要有它：nfo 里没有 <doubanid>，MoviePilot 的豆瓣接口也拿不到 id，
    # 只能走豆瓣网页搜索；而豆瓣反爬严格，必须慢速、只补缺失的、被限流就长时间
    # 冷却。因此这里用独立后台线程串行处理，默认每部间隔 1.2 秒。
    # ------------------------------------------------------------------
    def _start_douban_worker(self) -> None:
        """启动豆瓣补齐后台线程。"""
        stop = threading.Event()
        self._douban_stop = stop
        self._douban_thread = threading.Thread(
            target=self._douban_worker,
            args=(stop,),
            name="MyLibraryDouban",
            daemon=True,
        )
        self._douban_thread.start()

    def _stop_douban_worker(self, timeout: float = 3.0) -> None:
        """通知后台线程退出（线程在 Event 上等待，会被立即唤醒）。"""
        stop, thread = self._douban_stop, self._douban_thread
        self._douban_stop = None
        self._douban_thread = None
        if stop is not None:
            stop.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)

    def _douban_worker(self, stop: threading.Event) -> None:
        """后台循环：只查缓存里缺的，慢速请求，触发反爬就长时间冷却。"""
        failed: set = set()
        while not stop.is_set():
            todo = self._douban_todo(failed)
            if not todo:
                # 没有待补条目时不发任何请求，隔一段时间再看有没有新片入库
                stop.wait(DOUBAN_IDLE)
                continue

            rate_limited = False
            for dir_name, title, year in todo:
                if stop.is_set():
                    return
                cands, limited = self._douban_search(title)
                if limited:
                    rate_limited = True
                    print(f"【我的媒体库】豆瓣限流，暂停补齐 {DOUBAN_COOLDOWN // 60} 分钟")
                    break
                sid, match_year = self._douban_pick(cands, title, year)
                if sid:
                    self._douban_save(dir_name, sid, title, year, match_year)
                    print(f"【我的媒体库】豆瓣 ID 已补齐：{dir_name} -> {sid}")
                else:
                    # 本进程内不再重试，避免对同一条反复请求豆瓣
                    failed.add(dir_name)
                stop.wait(DOUBAN_DELAY)

            stop.wait(DOUBAN_COOLDOWN if rate_limited else 60)

    def _douban_todo(self, failed: Optional[set] = None) -> List[Tuple[str, str, str]]:
        """找出「有 nfo 但缓存里没有豆瓣 ID」的目录，返回 [(目录名, 片名, 年份)]。"""
        root = Path(self._library_path or "")
        if not self._library_path or not root.is_dir():
            return []
        cached = self._load_douban_ids()
        skip = failed or set()
        todo: List[Tuple[str, str, str]] = []
        for dir_path in sorted(root.iterdir()):
            name = dir_path.name
            if name.startswith(".") or name in skip or cached.get(name):
                continue
            if not dir_path.is_dir():
                continue
            try:
                has_nfo = any(f.suffix.lower() == ".nfo" for f in dir_path.iterdir() if f.is_file())
            except OSError:
                continue
            if not has_nfo:
                continue
            title, year = self._douban_parse_dirname(name)
            todo.append((name, title, year))
        return todo

    def _douban_save(self, dir_name: str, douban_id: str, title: str,
                     year: str, match_year: str = "") -> None:
        """把一条豆瓣 ID 合并写回缓存（先重读再原子替换，不覆盖外部脚本的写入）。"""
        cache_file = Path(self._library_path) / DOUBAN_CACHE_FILE
        with self._douban_lock:
            raw: Dict[str, Any] = {}
            if cache_file.is_file():
                try:
                    loaded = json.loads(cache_file.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        raw = loaded
                except Exception:
                    raw = {}
            raw[dir_name] = {
                "douban_id": douban_id,
                "title": title,
                "year": year,
                "match_year": match_year,
            }
            tmp = cache_file.with_name(cache_file.name + ".tmp")
            tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(cache_file)

    @staticmethod
    def _douban_parse_dirname(name: str) -> Tuple[str, str]:
        """从目录名解析片名与年份：'碟中谍 (1996)' -> ('碟中谍', '1996')。"""
        m = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", name or "")
        if m:
            return m.group(1).strip(), m.group(2)
        return (name or "").strip(), ""

    @staticmethod
    def _douban_normalize(text: str) -> str:
        """去掉标点、空白、全角半角差异，用于标题比较。"""
        if not text:
            return ""
        text = urllib.parse.unquote(text)
        text = re.sub(r"[\s\-—–_·:：,，.。!！?？'\"“”‘’()（）\[\]【】/\\]+", "", text)
        return text.lower()

    @staticmethod
    def _douban_is_rate_limited(html: str) -> bool:
        """识别豆瓣限流页（实测返回 error_info: 搜索访问太频繁）。"""
        if not html:
            return False
        return "访问太频繁" in html or "error_info" in html

    @staticmethod
    def _douban_parse_search(html: str, limit: int = 8) -> List[Tuple[str, str, str]]:
        """解析豆瓣移动版搜索结果，返回 [(subject_id, 标题, 年份)]。

        实测结构：
            <li><a href="/movie/subject/1292484/">
              <div class="subject-info">
                <span class="subject-title">碟中谍</span>
                <p class="subject-abstract">... 1996 ...</p>
        因此标题取 subject-title，年份在同一 <li> 块内再找四位年份。
        """
        out: List[Tuple[str, str, str]] = []
        seen = set()
        for li in re.findall(r"<li>(.*?)</li>", html or "", re.S):
            m_id = re.search(r"/movie/subject/(\d+)/", li)
            if not m_id:
                continue
            sid = m_id.group(1)
            if sid in seen:
                continue
            m_t = re.search(r'class="subject-title"[^>]*>(.*?)<', li, re.S)
            title_txt = m_t.group(1).strip() if m_t else ""
            ym = re.search(r"(19\d{2}|20\d{2})", re.sub(r"<[^>]+>", " ", li))
            seen.add(sid)
            out.append((sid, title_txt, ym.group(1) if ym else ""))
            if len(out) >= limit:
                break
        return out

    @classmethod
    def _douban_search(cls, title: str, limit: int = 8) -> Tuple[List[Tuple[str, str, str]], bool]:
        """请求豆瓣移动版搜索，返回 (候选列表, 是否被限流)。"""
        q = urllib.parse.quote(title or "")
        if not q:
            return [], False
        html = cls._douban_http_get(f"https://m.douban.com/search/?query={q}")
        if not html:
            return [], False
        if cls._douban_is_rate_limited(html):
            return [], True
        return cls._douban_parse_search(html, limit), False

    @staticmethod
    def _douban_http_get(url: str, tries: int = 2) -> str:
        """带 UA/Referer 的 GET（豆瓣对裸请求直接拒），失败返回空串。"""
        for i in range(tries):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": DOUBAN_UA, "Referer": "https://m.douban.com/"},
                )
                with urllib.request.urlopen(req, timeout=20, context=_DOUBAN_CTX) as resp:
                    return resp.read().decode("utf-8", "ignore")
            except Exception:
                if i == tries - 1:
                    return ""
                time.sleep(2 + i * 2)
        return ""

    @classmethod
    def _douban_pick(cls, cands: List[Tuple[str, str, str]],
                     want_title: str, want_year: str) -> Tuple[Optional[str], str]:
        """在候选中挑最匹配的一条：先看年份，再看标题相似度。

        阈值 35 是实测调出来的：低于它宁可留空（回退豆瓣搜索页），
        也不要给影片挂错豆瓣链接。
        """
        if not cands:
            return None, ""
        nt = cls._douban_normalize(want_title)
        wy = str(want_year or "")
        scored = []
        for sid, cand_title, cand_year in cands:
            nt_c = cls._douban_normalize(cand_title)
            score = 0
            if wy and cand_year == wy:
                score += 100                      # 年份完全一致，权重最高
            elif wy and cand_year:
                score += max(0, 30 - abs(int(cand_year) - int(wy))) * 2
            if nt and nt_c:
                if nt_c == nt:
                    score += 60                   # 标题完全一致
                elif nt in nt_c or nt_c in nt:
                    score += 35                   # 一方包含另一方
                else:
                    common = len(set(nt) & set(nt_c))
                    score += int(common / max(len(nt), len(nt_c)) * 30)
            scored.append((score, sid, cand_year))
        scored.sort(reverse=True)
        best = scored[0]
        if best[0] < 35:
            return None, ""
        return best[1], best[2]

    def _scan(self) -> List[Dict[str, Any]]:
        """扫描媒体库目录，返回条目列表。"""
        root = self._library_path
        if not root or not Path(root).exists():
            return []

        items: List[Dict[str, Any]] = []
        root_path = Path(root)
        douban_ids = self._load_douban_ids()

        for dir_path in sorted(root_path.iterdir()):
            if not dir_path.is_dir() or dir_path.name.startswith("."):
                continue
            entry = self._read_dir_item(dir_path)
            if entry:
                items.append(entry)

        # 附加豆瓣 id（按目录名匹配缓存）
        for entry in items:
            entry["douban_id"] = douban_ids.get(entry["dir_name"], "")

        # 排序：电影在前，再按年份倒序
        def sort_key(x: Dict[str, Any]) -> Tuple[int, str, int]:
            is_tv = 1 if x.get("type") == "电视剧" else 0
            try:
                year = int(x.get("year") or 0)
            except (TypeError, ValueError):
                year = 0
            return (is_tv, str(x.get("title") or ""), -year)

        items.sort(key=sort_key)
        return items

    def _read_dir_item(self, dir_path: Path) -> Optional[Dict[str, Any]]:
        """读取单个媒体目录：nfo 元数据 + poster 封面。"""
        # 找视频文件（判断是不是影视目录）
        videos = [
            p for p in dir_path.iterdir()
            if p.is_file() and p.suffix.lower() in MEDIA_EXTS
        ]

        is_tv = False
        nfo_files = list(dir_path.glob("*.nfo"))
        tvshow = dir_path / "tvshow.nfo"
        if tvshow.exists():
            nfo_files.append(tvshow)
            is_tv = True

        # 电视剧：继续看子目录里有没有剧集
        if not videos:
            sub_videos = [
                p for p in dir_path.rglob("*")
                if p.is_file() and p.suffix.lower() in MEDIA_EXTS
            ]
            if not sub_videos:
                return None
            videos = sub_videos
            if not is_tv:
                # 有 season 目录或 SxxExx 命名 -> 判为剧集
                for sv in sub_videos:
                    if sv.name.upper().startswith(("S", "E")) or "S0" in sv.name:
                        is_tv = True
                        break

        meta = self._parse_nfo(nfo_files)
        if not meta.get("title"):
            meta["title"] = dir_path.name

        poster = None
        for name in ("poster.jpg", "folder.jpg", "cover.jpg"):
            p = dir_path / name
            if p.exists():
                poster = p
                break

        # 横版背景图：优先 landscape（正常横构图）。
        # fanart/backdrop 常是"枪管/隧道"主观视角构图，当背景会出现圆形亮斑，故不用。
        landscape = None
        for name in ("landscape.jpg", "thumb.jpg"):
            p = dir_path / name
            if p.exists():
                landscape = p
                break

        # 清晰度：从视频文件名识别 2160p/1080p/720p 等
        resolution = ""
        for v in videos:
            m = re.search(r"(2160p|1080[pi]|720[pi]|4k|8k|uhd)", v.name, re.I)
            if m:
                resolution = m.group(1).upper().replace("I", "P")
                break

        # 电视剧季数统计
        seasons = set()
        if is_tv:
            for v in videos:
                ms = re.search(r"[Ss](\d{1,2})", v.name)
                if ms:
                    seasons.add(int(ms.group(1)))
            for sv in dir_path.glob("Season*"):
                ms = re.search(r"(\d+)", sv.name)
                if ms:
                    seasons.add(int(ms.group(1)))

        video_files = [
            {"name": v.name, "size_bytes": v.stat().st_size} for v in videos[:200]
        ]

        return {
            "title": meta.get("title"),
            "year": meta.get("year") or "",
            "type": "电视剧" if is_tv else "电影",
            "overview": (meta.get("overview") or "").strip(),
            "genre": meta.get("genre") or "",
            "rating": meta.get("rating") or "",
            "mpaa": meta.get("mpaa") or "",
            "studio": meta.get("studio") or "",
            "country": meta.get("country") or "",
            "tmdb_id": meta.get("tmdb_id") or "",
            "imdb_id": meta.get("imdb_id") or "",
            "duration": meta.get("duration") or "",
            "release_date": meta.get("release_date") or "",
            "edition": meta.get("edition") or "",
            "director": meta.get("director") or "",
            "directors": meta.get("directors") or [],
            "cast": meta.get("cast") or [],
            "resolution": resolution,
            "season_count": len(seasons),
            "path": str(dir_path),
            "dir_name": dir_path.name,
            "has_poster": bool(poster),
            "poster_name": poster.name if poster else "",
            "has_landscape": bool(landscape),
            "size_bytes": self._dir_size(dir_path),
            "video_count": len(videos),
            "video_files": video_files,
        }

    @staticmethod
    def _dir_size(dir_path: Path) -> int:
        """递归统计目录占用字节数。"""
        total = 0
        try:
            for p in dir_path.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
        except OSError:
            pass
        return total

    @staticmethod
    def _parse_nfo(nfo_files: List[Path]) -> Dict[str, Any]:
        """解析 nfo，返回影片完整元数据（标题/年份/简介/类型/评分/演职员等）。"""
        import xml.etree.ElementTree as ET

        meta: Dict[str, Any] = {}
        for nfo in nfo_files:
            try:
                tree = ET.parse(nfo)
                root = tree.getroot()
            except Exception:
                continue

            def text_of(*tags: str) -> str:
                for tag in tags:
                    el = root.find(tag)
                    if el is not None and el.text and el.text.strip():
                        return el.text.strip()
                return ""

            meta["title"] = text_of("title") or meta.get("title", "")
            meta["year"] = text_of("year") or meta.get("year", "")
            meta["overview"] = text_of("plot", "outline") or meta.get("overview", "")
            meta["genre"] = text_of("genre") or meta.get("genre", "")
            meta["rating"] = text_of("rating", "voteaverage") or meta.get("rating", "")
            meta["mpaa"] = text_of("mpaa", "certification") or meta.get("mpaa", "")
            meta["studio"] = text_of("studio") or meta.get("studio", "")
            meta["country"] = text_of("country") or meta.get("country", "")
            meta["tmdb_id"] = text_of("tmdbid") or meta.get("tmdb_id", "")
            meta["imdb_id"] = text_of("imdbid") or meta.get("imdb_id", "")
            meta["duration"] = text_of("runtime") or meta.get("duration", "")
            meta["release_date"] = text_of("premiered", "releasedate") or meta.get("release_date", "")
            meta["edition"] = text_of("edition") or meta.get("edition", "")

            # 导演（可能多个）
            directors = [d.text.strip() for d in root.findall("director")
                         if d.text and d.text.strip()]
            if directors:
                meta["director"] = "、".join(dict.fromkeys(directors))
                meta["directors"] = list(dict.fromkeys(directors))[:5]

            # 演职员：演员带头像与角色，导演/编剧按需收录
            cast: List[Dict[str, str]] = []
            for tag, label in (("actor", "演员"), ("director", "导演")):
                for node in root.findall(tag):
                    name_el = node.find("name")
                    name = (name_el.text or "").strip() if name_el is not None else ""
                    if not name:
                        name = (node.text or "").strip()
                    if not name:
                        continue
                    role_el = node.find("role")
                    thumb_el = node.find("thumb")
                    cast.append({
                        "name": name,
                        "role": (role_el.text or "").strip() if role_el is not None else "",
                        "thumb": (thumb_el.text or "").strip() if thumb_el is not None else "",
                        "tag": tag,
                        "tag_text": label,
                    })
            if cast:
                meta["cast"] = cast[:20]

            if meta.get("title"):
                break
        return meta

    @staticmethod
    def _human_size(num: float) -> str:
        """把字节数格式化为人类可读大小。"""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if num < 1024:
                return f"{num:.1f} {unit}".replace(".0 ", " ")
            num /= 1024
        return f"{num:.1f} PB"

    def stop_service(self) -> None:
        """停止插件后台服务并释放资源。"""
        self._stop_douban_worker()
