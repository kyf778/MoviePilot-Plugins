# MoviePilot-Plugins

个人 MoviePilot V3 插件市场仓库。

MoviePilot 通过 `PLUGIN_MARKET` 配置读取 GitHub 仓库的 `main` 分支索引，多个地址用逗号分隔。

## 插件列表

| 插件 | 说明 |
| --- | --- |
| [MyLibrary 我的媒体库](plugins.v3/mylibrary) | 在左侧导航栏浏览本地媒体库：NFO 元数据 + 本地图片海报墙，悬停看简介，点开看导演/演职员/清晰度/文件清单，可直达 TheMovieDb / IMDb / 豆瓣 |

## 订阅方法

在 MoviePilot 中依次进入：

**系统设置 → 插件市场 → 插件仓库**，填入本仓库地址：

```text
https://raw.githubusercontent.com/kyf778/MoviePilot-Plugins/main
```

保存后刷新插件市场，即可看到并安装「我的媒体库」。

> 也可以直接改配置项 `PLUGIN_MARKET`（系统设置 → 插件 → 插件仓库），多个地址用逗号分隔，例如：
> `https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/main,https://raw.githubusercontent.com/kyf778/MoviePilot-Plugins/main`

## 使用说明

安装后在插件设置中填写：

- **启用**：开启插件
- **媒体库目录**：例如 `/vol1/1000/Videos`（每个影片一个子目录，目录内含 NFO 与图片）
- **海报尺寸**：`medium` / `small` / `large`

插件会在左侧「媒体整理」分组下出现「我的媒体库」入口。

### 支持的目录结构

```text
Videos/
├── 碟中谍 (1996)/
│   ├── 碟中谍 (1996).nfo        # 必需：元数据
│   ├── poster.jpg              # 竖版海报（必需）
│   ├── landscape.jpg           # 横版背景（可选，缺失时回退 poster）
│   └── 碟中谍 (1996).mkv        # 视频文件
└── 007：大破量子危机 (2008)/
    └── ...
```

图片文件名兼容常见 Jellyfin / Emby / TinyMediaManager 命名，识别优先级：

| 用途 | 候选文件名（按优先级） |
| --- | --- |
| 竖版海报 | `poster.jpg` → `folder.jpg` → `cover.jpg` |
| 横版背景 | `landscape.jpg` → `thumb.jpg` |

> **注意**：本插件刻意不使用 `fanart.jpg` / `backdrop.jpg` 作为详情页背景。这两个文件在很多影片里是"枪管/隧道"式主观视角构图，作为背景会出现中央圆形亮斑，观感很差。

### 豆瓣链接（可选）

NFO 中通常没有 `<doubanid>`，豆瓣又有反爬限制，因此仓库提供一次性抓取脚本：

```bash
python3 tools/fetch_douban_ids.py /vol1/1000/Videos
```

脚本会生成 `<媒体库目录>/.douban_ids.json`，插件读取该缓存并在详情页生成豆瓣条目直链。

- 可重复运行，已缓存的条目会跳过，中断后直接续跑
- 默认 1.2 秒请求间隔，请勿并发运行（易触发豆瓣限流）
- 无缓存时，详情页的豆瓣链接会回退为豆瓣搜索页

## 目录结构

```text
MoviePilot-Plugins/
├── plugins.v3/              # V3 插件（目录名须为插件主类名的小写形式）
│   └── mylibrary/
│       ├── __init__.py      # 插件后端
│       ├── vite.config.js   # 联邦构建配置（官方 CSS 门禁依赖它识别插件）
│       └── dist/            # Vue 联邦构建产物
├── icons/                   # 插件图标
├── tools/                   # 辅助脚本
├── tests/v3/mylibrary/      # V3 插件测试
├── .github/scripts/         # 发布前检查脚本
├── package.v3.json          # V3 插件市场索引（本插件实际生效的索引）
└── package.json             # 旧代索引占位，见下方说明
```

### 关于两个索引文件的版本号

官方版本门禁要求 **V3 版本 = 旧代版本主号 + 1**（大版本跃迁）。本插件是 V3 专用实现，
因此：

| 文件 | 版本 | 作用 |
|---|---|---|
| `package.v3.json` | `3.3.0` | V3 宿主实际读取的索引 |
| `package.json` | `2.0.0` + `"v3": false` | 旧代占位，让旧代宿主识别后跳过 |

⚠️ **不要把 `package.json` 的版本改成 `3.3.0`**，那会触发官方门禁失败
（V3 版本必须比旧代大一号）。改动版本时两个文件要一起考虑。

## 开发

```bash
cd plugins.v3/mylibrary
pnpm install
pnpm build          # 产物输出到 dist/assets
```

提交前跑一次统一检查（版本一致性 + 联邦 CSS 隔离 + 隐私扫描 + 单元测试）：

```bash
python .github/scripts/preflight.py
```

> 该脚本等价于官方门禁的本地版本。官方 CI 还会额外运行
> `check_federation_css.py` 与 `check_plugin_versions.py` 两个脚本，
> 判定逻辑以官方为准。

提交前请确保：

- `plugin_version`、`package.v3.json` 中的 `version` 与最新 `history` 三者一致
- 当前版本历史置顶，其余按语义版本降序
- 插件目录名为插件主类名的小写形式（`MyLibrary` → `mylibrary`）
- **不得发布 `__federation_shared_vuetify/styles-*.css`**——联邦组件与主程序共用
  同一个 `document`，Vuetify 全局样式会污染宿主界面。`vite.config.js` 里的
  postcss 过滤器负责丢弃来自 `node_modules/vuetify` 的样式，改构建配置时不要删掉它

## 免责声明

本仓库插件为个人自用工具，不隶属于 MoviePilot 官方。使用前请自行确认代码安全性。

MoviePilot 官方仓库：[jxxghp/MoviePilot-Plugins](https://github.com/jxxghp/MoviePilot-Plugins)