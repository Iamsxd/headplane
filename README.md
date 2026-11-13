# Headplane 中英文切换

入口：https://140.143.127.180/admin/，基于官方 Headplane 0.8.2，2026-11-13 上线。
右上角选择“简体中文 / English”，默认中文。切换会刷新当前页并保留路径、过滤条件和片段。
浏览器通过 Secure、HttpOnly、SameSite=Lax、Path=/admin 的 hp_language Cookie 记忆选择一年；不同浏览器互不影响。其他已打开标签页刷新后使用新选择。

## 源码和维护

Fork：https://github.com/Iamsxd/headplane ，定制分支 `lovecanl-0.8.2`，上游 https://github.com/tale/headplane 。
官方 `v0.8.2` 基线提交为 `05e3ee33f6d3b347013654c69186791347be8bd9`；保留上游历史以便比较和升级。
之前的中文和双语版本于 2026-11-13 从保留源码补建为两条独立提交，没有伪造更早的提交日期，详见 [恢复来源与版本记录](docs/fork-history.md)。
构建工具在 `tools/`，部署/轮换/备份/验证脚本和非敏感配置模板在 [deployment/tencent/](deployment/tencent/README.md)。
密码、API 密钥、私钥、Cookie 密钥、数据库和备份不进入 Git。

app/ 是中文视图及共用集成代码。官方英文对照可通过 `git show v0.8.2:app/文件路径` 查看；本机保留的 .upstream/app/ 仅作参考，不纳入版本管理。英文构建从服务器保存的完整官方 0.8.2 源码准备，只增加构建脚本列明的共用集成补丁。
common.zh-CN.json 和 tools/apply-common.cjs 仅为初始翻译辅助，最终源另有人工修订。

中英文覆盖导航、设备、用户、访问控制、DNS、设置、登录、公共组件、弹窗和常用提示。
产品名称、API/配置/表单键、权限枚举、命令、策略示例、设备名称、地址和用户数据保持原样。外部服务及第三方库原始诊断信息可能仍是英文。
保留上游 MIT 许可证，见 LICENSE。

这是本地双语构建。升级上游时，需迁移中文及共用集成补丁，重新执行构建、候选验证和发布流程。原仅中文发布的历史说明保存在 README.zh-only-20261113.md。

## 架构

两套 SSR/客户端视图共用一个后端 context、数据库连接、认证服务、Headscale 客户端和后台任务。
中文 server/app.ts 初始化一次；英文 server/language-view.ts 只导出请求处理器工厂，接收同一个 context，不加载配置、不打开数据库、不启动服务或端口。
每个请求按 Cookie 白名单选择视图，缺失/损坏/不支持的值回到中文。
静态文件合并并检查同名内容一致，切换后旧文档的资源仍能加载。完整刷新保持模块级文案、SSR 和水合语言一致。

语言 POST 显式校验 Origin，仅接受 zh-CN/en。回跳限制在后台内，对 URL 归一化后的最终路径再次拒绝双斜线；React Router 负责补回 basename。
共享功能状态保留上游英文原因，中文在展示处翻译，避免英文页面混入中文原因。

## 构建与发布

- 完整官方源码：服务器 /root/headplane-setup-20261113/source/tale-headplane-6f0764e，版本 0.8.2。
- 暂存及日志：/root/headplane-language-20261113/，其中 zh/、en/ 为可重建源。
- Node24.22.1 / pnpm10.4.0：/opt/headplane-build/bin。
- 精确冻结依赖：/opt/headplane-zh-source/node_modules。准备源码时核对 pnpm-lock.yaml 与冻结安装一致，未更新依赖。
- 官方 WASM/wasm_exec.js 复用，未重编译 Go 探针。
- 覆盖归档：本机 artifacts/tencent-headscale/headplane-language-overlay.tgz。

服务器 overlay/ 需要 app/、tests/、CHANGELOG.md、Dockerfile.language；运行 tools/build-language.py，每次清空并重建限定的两个源目录，依次执行 typecheck、lint、完整 unit suite、build，合并资源并检查碰撞。
使用 Dockerfile.language，历史 Dockerfile 仅用于最初的单中文发布。镜像构建上下文不得包含配置密钥、登录文件或数据库备份。
本次工具使用固定暂存目录，未来发布应另建目录和回滚点。

固定继承官方运行时：

```text
ghcr.io/tale/headplane@sha256:b053a0a6699d0a67be3f0d9bae8e7dbe35ed67ae8448412adcbad7ea49866faa
```

部署标签 headplane-local:0.8.2-bilingual-20261113；systemd 固定镜像 ID：

```text
sha256:9ce135fc8b7c06f2c8a930d106639cd00adf44efe8bcf1ac81fdcab339774397
```

服务继续使用 loopback3000、非 root、只读根文件系统、cap-drop、内存/进程限制，无 Docker socket。
密钥轮换通过 systemd 重启，继续读取 runtime.env 中的固定双语镜像。

## 验证和回退

公开版本来源与验证摘要见 [docs/fork-history.md](docs/fork-history.md)；完整运维证据保留在操作者工作区的 artifacts/tencent-headscale/headplane-language-release-20261113.md。
tools/verify-language.py 验证隔离候选；加 --public 则读取本机私有登录文件验证正式 HTTPS，不输出凭据。
包括 Cookie、正常/危险回跳、跨站 POST、八个页面、静态资源、非写入表单校验、并发隔离。浏览器另验证实际切换、记忆、当前详情页及手机布局。

退回上一个仅中文版本，在服务器以 root 执行：

```sh
cp /root/headplane-language-20261113/before-language.env /etc/headplane/runtime.env
systemctl restart headplane
curl --fail http://127.0.0.1:3000/admin/healthz
```

无数据库迁移，无需回滚设备或账号数据。原官方和此前中文镜像均保留。
tools/deploy-language.py 会拒绝覆盖本次回滚点，不应重复用于后续发布。
