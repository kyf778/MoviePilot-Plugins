# 贡献指南

感谢参与。本仓库是 [MoviePilot](https://github.com/jxxghp/MoviePilot) V3 的第三方插件仓库，
开发规范以 [jxxghp/MoviePilot-Plugins](https://github.com/jxxghp/MoviePilot-Plugins) 官方插件仓为准。

## 环境准备

```bash
git clone https://github.com/kyf778/MoviePilot-Plugins.git
cd MoviePilot-Plugins
python -m pip install pytest

cd plugins.v3/mylibrary
pnpm install
```

建议把 MoviePilot 仓库 clone 到同级目录，这样测试能走真实的 `app.plugins` 导入路径：

```text
parent/
├── MoviePilot/
└── MoviePilot-Plugins/
```

没有宿主也能跑——测试会在检测不到宿主时注入最小 `_PluginBase` 桩。

## 开发流程

1. 在 `plugins.v3/<plugin_id_lower>/` 下修改插件
2. 重新构建前端：`cd plugins.v3/<id> && pnpm build`
3. 跑发布前检查：`python .github/scripts/preflight.py`
4. 全部通过后提交 PR

## 硬性规则（违反会被 CI 拒绝）

这几条来自官方门禁脚本 `.github/scripts/check_plugin_versions.py` 与
`check_federation_css.py`，本仓库 CI 直接调用官方原件：

| 规则 | 说明 |
|---|---|
| 目录名 = 主类名小写 | `MyLibrary` → `plugins.v3/mylibrary/` |
| 三处版本一致 | `plugin_version`、`package.v3.json` 的 `version`、最新 `history` |
| history 降序 | 当前版本置顶，其余按语义版本降序 |
| 语义版本 | `3.1.0` 形式，不带 `v` 前缀 |
| **大版本跃迁** | `package.v3.json` 的主版本 = `package.json` 主版本 + 1 |
| `system_version` 用 PEP440 | `">=3.0.0"`，不要写 `"v3"` |
| 联邦插件 `release: true` | 否则 Release 工作流不会打包 |
| **不得发布 Vuetify 全量样式** | 不能有 `__federation_shared_vuetify/styles-*.css` |

### 关于最后一条

联邦组件与主程序运行在同一个 `document`，远程 CSS 会被追加到主页面 `<head>`。
如果插件打包了 Vuetify / MDI 的基础样式，`.v-card`、`.rounded-*`、`html`、`body`
等全局规则会污染 MP 主界面，而且离开插件页面后仍继续生效。

`plugins.v3/mylibrary/vite.config.js` 里的 postcss 过滤器负责丢弃来自
`node_modules/vuetify` 与 `node_modules/@mdi` 的 CSS，**改构建配置时不要删掉它**。

## 版本号怎么改

改版本时要同时动三个地方，并保持一致：

```
plugins.v3/mylibrary/__init__.py   plugin_version = "3.4.0"
package.v3.json                    "version": "3.4.0"
package.v3.json                    "history": { "v3.4.0": "...", ... }  ← 置顶
```

另外 `package.json` 与 `package.v2.json` 是旧代占位索引，**保持 `2.x` 不要动**——
它们靠 `v3: false` 排除，只是为了满足上面的大版本跃迁规则。

## 测试

```bash
python tests/run.py           # 全部测试
python tests/run.py -v        # 详细输出
python tests/v3/mylibrary/test_mylibrary.py   # 单个文件
```

测试放在 `tests/v3/<plugin_id_lower>/`，不要放进插件源码目录。
测试应覆盖纯逻辑与安全边界；外部网络、真实媒体库、第三方账号一律用 mock，
**不要让单元测试依赖公网状态或用户的真实数据**。

## 提交与 PR

- 一个 PR 只做一件事
- 提交信息用中文，说明**为什么**改而不只是改了什么
- 附上 `preflight.py` 的输出，证明检查已通过
- 涉及前端改动时附上重建后的 `dist/` 产物

## 安全约束

- 不要提交任何凭据、Cookie、内网地址或个人路径（`preflight.py` 会扫描）
- 不要编写用于绕过 MoviePilot 用户认证的插件
- 不要提供色情、赌博等违法违规内容

## 许可

提交即表示同意你的贡献以 [MIT](LICENSE) 许可发布。