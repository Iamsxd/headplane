# 历史记录：Headplane 仅中文版本（已由双语版本替代）

部署于 `https://140.143.127.180/admin/`，基于官方 Headplane 0.8.2，2026-11-13 上线。
`app/` 是最终中文源文件；`.upstream/app/` 是未修改的上游对照。
`common.zh-CN.json` 与 `tools/apply-common.cjs` 仅辅助初始翻译，最终版本另有人工修订，不能仅凭运行该工具重建完整翻译。

## 范围

导航、设备、用户、访问控制、DNS、设置、登录页面、公共组件、弹窗、常用校验和状态提示已翻译，日期与相对时间使用中文。
产品名称、API/配置/表单键、权限枚举、命令及策略示例保持原样。设备名称、地址和用户数据不翻译。
Headscale、OIDC、浏览器及第三方库返回的原始诊断信息可能仍为英文。

这是当前版本的本地翻译，不是上游官方语言包。升级上游版本时，应重新对比并迁移翻译，再构建和验证。
保留上游 MIT 许可证，见 `LICENSE`。

## 来源与构建

官方源码：`tale/headplane`，版本 0.8.2，源码目录 `tale-headplane-6f0764e`。
官方运行时固定为：

```text
ghcr.io/tale/headplane@sha256:b053a0a6699d0a67be3f0d9bae8e7dbe35ed67ae8448412adcbad7ea49866faa
```

服务器完整构建源位于 `/opt/headplane-zh-source`，Node 24.22.1、pnpm 10.4.0 位于 `/opt/headplane-build/bin`。
依赖安装使用官方源码的冻结 `pnpm-lock.yaml`，未更新依赖版本。pnpm 压缩包按官方 npm 元数据 SHA512 校验。
WASM 与 wasm_exec.js 复用官方运行时文件；未重新编译 Go 探针。

在对应上游源码上覆盖 `app/` 和 `CHANGELOG.md` 后运行：

```sh
export PATH=/opt/headplane-build/bin:$PATH
export HEADPLANE_VERSION=0.8.2
pnpm install --frozen-lockfile --ignore-scripts
pnpm run typecheck
pnpm run lint
pnpm run build
```

以 `Dockerfile` 和 `build/` 构建派生镜像，只替换应用构建产物，继承官方 Node、启动方式和运行时支持。
不要将 `/etc/headplane`、API 密钥、Cookie 密钥、登录文件或数据备份加入镜像构建上下文。

部署镜像标签：`headplane-local:0.8.2-zh-cn-20261113`。
实际 systemd 环境固定使用不可变的镜像 ID：

```text
sha256:0cbb92e64044823687842054354bca13922ecc997a413188baaf14382dcd1981
```

原版镜像与配置保留于服务器。API 密钥轮换通过 systemd 重启 Headplane，继续使用 `/etc/headplane/runtime.env` 中的中文镜像；无需更改轮换脚本。

## 验证与恢复

完整结果见 `../../artifacts/tencent-headscale/headplane-zh-release-20261113.md`。
临时候选环境使用独立 SQLite 快照和 loopback 3001；已验证后移除候选容器及本机预览代理/SSH 隧道。
预览代理只允许 GET，不提交任何生产写入。

恢复原版时，在服务器以 root 执行：

```sh
cp /root/headplane-zh-setup-20261113/before-zh-deploy.env /etc/headplane/runtime.env
systemctl restart headplane
curl --fail http://127.0.0.1:3000/admin/healthz
```

翻译不涉及数据库结构，无需回滚设备数据。仅在数据本身损坏时才按原备份恢复流程处理数据库。
`tools/deploy.py` 为本次部署脚本，拒绝覆盖既有回滚点；未来发布需使用新的独立暂存目录。
