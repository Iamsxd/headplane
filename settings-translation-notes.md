# 用户、设置、DNS 与 ACL 汉化说明

已修改这四个路由目录中的 48 个 `.ts` / `.tsx` 文件；`acls/components/theme.ts` 没有用户文案，未修改。

- 已翻译页面、表格、按钮、弹窗、说明、工具提示、表单校验、成功消息、权限错误及角色显示名称。
- 保留 Headplane、Headscale、Tailscale、Headplane Agent、Tailnet、Magic DNS 等产品名称及 DNS、ACL、OIDC、SSH、IAM 等缩写。
- 保留角色枚举、表单字段及提交值、配置键、策略键、查询与 API 路径、IP/域名/用户名示例、命令和实际用户数据。
- `dns/dialogs/add-record.tsx` 中重复记录提示的 `includes("already exists")` 与本地校验消息耦合；两处匹配词同步改成 `includes("已存在")`，判断行为保持一致。
- `settings/restrictions/table.tsx` 的动态英文类型名称改为中文显示映射，`domain`、`group`、`user` 提交值保持原样。
- `acls/components/rules-editor.tsx` 仅在显示时将已知 SSH 操作 `accept` / `check` 映射为“允许”/“定期验证”，策略原始值与未知操作保持原样。
- `acls/acl-action.ts` 的本地语法错误前缀改为“语法错误:”，保留 ASCII 冒号，以兼容现有标题/详情拆分。

仍由目录外或外部服务提供的显示内容：`USERNAME_RULE`、`validateUsername`、`parsePolicy`、`formatTimeDelta`，以及 Agent 的 `reason` / 同步错误和 Headscale API 原始错误。前四项由父任务统一处理；后几项若要求完全中文，需要在其来源或统一错误呈现层继续处理。

按分工未执行安装、类型检查、构建、测试或部署。已用静态文案扫描检查这些目录，剩余英文句子仅出现在注释、日志、API 错误匹配条件、命令示例和外部原始值中。
