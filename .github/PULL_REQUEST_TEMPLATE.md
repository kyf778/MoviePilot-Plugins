name: 提交 PR
description: 提交插件改动
title: "[PR] "
labels: ["pr"]
body:
  - type: markdown
    attributes:
      value: |
        提交前请确认已阅读 [贡献指南](../blob/main/CONTRIBUTING.md)。

  - type: input
    id: plugin
    attributes:
      label: 涉及插件
      description: 改动了哪个插件，填目录名
      placeholder: "mylibrary"
    validations:
      required: true

  - type: dropdown
    id: change-type
    attributes:
      label: 改动类型
      options:
        - 修复缺陷
        - 新增功能
        - 适配版本 / 元数据
        - 构建配置或依赖
        - 文档
        - 其他
    validations:
      required: true

  - type: textarea
    id: change
    attributes:
      label: 改动说明
      description: 说明改了什么，以及为什么这样改
    validations:
      required: true

  - type: textarea
    id: checklist
    attributes:
      label: 自检
      description: 确认后才提交，未勾选的 PR 会被关闭
      value: |
        - [ ] 已运行 `python .github/scripts/preflight.py` 且全部通过
        - [ ] 版本号已在 `__init__.py`、`package.v3.json`、`history` 三处同步
        - [ ] 前端改动已重新构建并提交 `dist/` 产物
        - [ ] 未提交任何凭据、内网地址或个人路径
      render: markdown