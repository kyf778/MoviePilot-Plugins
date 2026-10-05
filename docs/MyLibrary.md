# 我的媒体库（MyLibrary）

在 MoviePilot 左侧导航栏浏览本地媒体库的海报墙。

## 功能

- 扫描媒体库目录，读取每部影片目录内的 NFO 元数据与本地图片
- 展示海报墙，悬停卡片可看简介，点开看导演、演职员、清晰度、体积、文件清单
- 一键跳转 TheMovieDb / IMDb / 豆瓣
- 豆瓣 ID 可选缓存：见 [豆瓣 ID 缓存](#豆瓣-id-缓存)

## 使用

1. 在 MoviePilot 中安装「我的媒体库」插件
2. 进入插件配置，填写媒体库根目录，例如 `/media/Videos/电影`
3. 保存后重启 MoviePilot，侧栏会出现入口

### 目录结构

插件按「一级目录 = 一部影片」扫描：

```text
/media/Videos/电影/
├── 大战争家廓尔凯撒 (2006)/
│   ├── movie.nfo
│   └── poster.jpg
└── 007：大破天幕杀机 (2015)/
    ├── movie.nfo
    └── poster.jpg
```

- NFO 文件名不限（`movie.nfo`、`*.nfo` 均可），取第一个成功解析的
- 图片支持 `poster.jpg` / `folder.jpg` / 目录内首张图片
- 子目录会被当作独立影片扫描；**不要在影片目录里再套一层目录**

## 豆瓣 ID 缓存（可选）

NFO 里通常没有豆瓣 ID。插件支持读取媒体库根目录下的 `.douban_ids.json`
补充豆瓣链接，用配套脚本生成：

```bash
python tools/fetch_douban_ids.py /media/Videos/电影
```

参数：

| 参数 | 说明 | 默认值 |
|---|---|---|
| `library` | 媒体库目录（位置参数） | 必填 |
| `-o, --output` | 输出文件路径 | `<library>/.douban_ids.json` |
| `--delay` | 每次请求间隔秒数 | `1.2` |

脚本通过 `m.douban.com` 逐部搜索，**默认间隔 1.2 秒，请勿调低**——
豆瓣对高频访问会返回「搜索访问太频繁」。生成的 JSON 不会被提交到仓库
（已在 `.gitignore` 中）。

## 隐私

插件只读取本地文件，不向外部发送媒体库路径或文件名。
豆瓣 ID 脚本会请求豆瓣搜索接口，请自行评估使用频率。

## 常见问题

**条目数不对**
确认配置路径指向影片所在的那一层。若影片在 `电影/` 子目录下，路径要写到该子目录。

**海报不显示**
确认影片目录下有 `poster.jpg` 等图片；图片名含特殊字符也能识别，但请避免中文路径编码问题。

**豆瓣链接为空**
该影片未在缓存中找到。运行 `fetch_douban_ids.py` 生成缓存，或手动编辑 `.douban_ids.json`。

## 开发

见仓库根目录的 [CONTRIBUTING.md](../CONTRIBUTING.md)。
前端源码在 `plugins.v3/mylibrary/src/`，修改后需重新构建并提交 `dist/`。
