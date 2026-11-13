# Headplane password and TOTP with Casdoor / SQLite

Status: detailed design approved by the operator on 2026-11-13; implementation authorized. Authentication deployment remains pending until candidate acceptance and cutover are verified.

## 中文实施摘要

- 使用 Casdoor＋SQLite，新增一个认证服务；SQLite 是本地数据库文件，无需独立数据库服务器。
- 后台继续使用 `https://140.143.127.180/admin/`，保留当前账号密码、管理员权限和中英文切换。
- 首次登录先扫码绑定手机验证器并保存一次性恢复码；此后登录需要密码及动态码，恢复码可以应急使用一次。
- 退出登录同时结束 Headplane 和认证服务的当前浏览器会话，修复退出后立即自动登录的问题。
- 先用隔离的后台数据库副本和临时测试账号验证 IP HTTPS、强制二步验证、恢复码、退出及双语界面，再备份和切换。切换时后台会短暂重启，现有后台会话失效。
- 实施选择：认证服务使用现有 HTTPS 下的 `/auth/` 路径；初始内存上限 512 MiB，实测后决定是否接受。现有 Headscale、中继、博客和设备身份须通过切换前后核验。
- 手机绑定由操作者在实际 HTTPS 页面完成，二维码密钥和恢复码不进入聊天或 Git。实施改动分项提交到已有 fork。

Builder check: a fresh independent reviewer found no important unanswered planning questions on 2026-11-13. Runtime compatibility remains a candidate acceptance requirement, not a verified deployment claim.

## Intent, choices, and limits

The operator selected **Casdoor plus SQLite** after requesting a lighter alternative to Keycloak plus PostgreSQL. Keep the current password-based administrator account and add a phone authenticator's six-digit TOTP code. First login must require enrollment and verification; provide one-time recovery codes. Logout must end the current Headplane and provider browser session and stay logged out. Keep the current IP HTTPS dashboard and bilingual UI.

Use one extra authentication service with an embedded SQLite database file. Do not add PostgreSQL, MySQL, Redis, a separate forward-auth gateway, or a maintained authentication-provider fork. No memory-use claim has been measured; start with a 512 MiB provider limit and measure candidate startup and steady state before accepting it.

This change covers dashboard login, not device registration or network login. Preserve Headscale user/device identities, addresses, ACLs, Noise/DERP keys, control routes, STUN, blog HTTPS, monitoring and maintenance timers. No upstream PR is requested. The operator binds their own authenticator; production QR seeds and recovery codes must not be printed, committed, or shared in chat.

## Approaches considered

- **Selected: Casdoor / SQLite via native Headplane OIDC.** Official 4.27.1 source and documentation support TOTP, mandatory enrollment, one-time recovery codes, Chinese UI, subpath routing, SQLite and RP-initiated logout. It adds one service and a file to back up.
- VoidAuth / SQLite also supports IP application URLs, subpaths, MFA, Chinese and OIDC. Recovery codes were not verified; Casdoor better matches the intended recovery flow.
- Keycloak / PostgreSQL was not approved and its proposal is withdrawn because of the extra database service. Tinyauth's reviewed release rejects IP URLs. No custom password/TOTP implementation is proposed in Headplane.

## Current state and required app fixes

Headplane 0.8.2 is deployed as a pinned bilingual Docker image, one initialized backend, loopback 3000, 512 MiB limit, non-root and read-only filesystem. Nginx Basic authentication injects `Remote-User: admin`; this trusted proxy identity reauthenticates immediately after logout. One Headplane owner has subject `proxy:admin` and is linked to Headscale user ID 1.

Two shared application changes are required and must apply to both language builds:

1. Enforce `oidc.disable_api_key_login` in the server-side login action **before** accepting a submitted key, validating it against Headscale, or creating any session. In current 0.8.2 the loader hides/redirects the UI, but direct action POST is still accepted. Add tests for enabled/disabled login and both document/data action contracts.
2. Explicitly configure `_hp_auth` cookies with HttpOnly and SameSite=Lax in addition to Secure and the `/admin` path. Verify creation and expiration headers. Do not assume current behavior: current context options omit HttpOnly.

Preserve API-key login when the disabling setting is false, upstream behavior for other installations, the one-backend bilingual architecture, and existing tests. Apply integration patches explicitly to the English build in `tools/build-language.py`. Add a user-facing changelog Fixes entry. No OIDC state-cookie redesign is included; test mismatched state and expired/reused authorization codes rather than claiming server-expiring, single-use state.

## Provider, URLs, and access boundaries

- Pin official Casdoor `v4.27.1` (reviewed source `2213c440aa2ce100f4d47efc1c0be3d7d47417fe`) by image digest after verifying its SQLite-enabled runtime. Prefer an official non-demo image configured with SQLite; do not expose an all-in-one image's sample credentials/data. If the published image cannot satisfy the reviewed source/SQLite/subpath behavior, report it rather than silently building an unreviewed provider fork.
- Intended external provider base: `https://140.143.127.180/auth`, using existing Nginx TLS and certificate renewal. Use provider `basePath` support so assets/API/redirects stay under `/auth/`; leave dashboard at `https://140.143.127.180/admin/`. Bind provider HTTP only to loopback; do not add a public port or security-group rule.
- Configure the external origin explicitly and trust only the local proxy. Nginx overwrites forwarding headers and strips untrusted identity headers. Restrict provider administrative console and nonessential management APIs while permitting the login/account/MFA endpoints needed for owner enrollment and recovery. A legitimate account must not gain provider administrative permissions.
- Keep configuration read-only and secrets in service-readable protected files, runtime state in a separate private SQLite data directory, and logs bounded. Use a non-root identity, capabilities dropped, no-new-privileges, read-only container filesystem with only required writable paths, pids and memory limits, and no Docker socket. Disable unused provider LDAP/RADIUS/listener functionality; validate actual listening sockets.
- One dedicated organization/application for Headplane; use a standards-compatible JWT format and stable user-ID `sub`, signing certificate, confidential client secret, PKCE S256, and exact registered redirect URIs: `/admin/oidc/callback` and `/admin/login?s=logout`. No wildcard redirects. Discover the exact issuer/metadata/endpoints from the configured candidate and verify issuer, audience, nonce, signature, and callback. Never relax validation to make an issuer mismatch work.

## Account, MFA, and logout policy

- Provision ordinary provider user `admin` in the dedicated organization, reusing the existing dashboard password privately. The Headplane owner role comes from the guarded migration, not from granting this user Casdoor administrator access.
- Protect a separate provider maintenance identity with a random private credential, available only through the documented SSH/local maintenance path. Initialize it before exposing any provider route; never leave first-visitor bootstrap or sample accounts accessible. The builder may select the exact initialization mechanism after reading the pinned release's import/API behavior.
- Disable public sign-up, invitations/open user creation, social/guest/passwordless alternatives and unused OAuth grant types for this application. Require TOTP in the organization, disable remembered-MFA bypass, and verify an unenrolled user cannot get an authorization code until enrollment completes. An already enrolled user must supply a valid dynamic code or one-time recovery code at a fresh login.
- Display QR enrollment and recovery codes only on authenticated HTTPS pages. Require a real valid TOTP to activate enrollment. Test one-time recovery use and refusal on reuse. Document loss-of-phone recovery and SSH-assisted reset when all recovery material is lost; no permanent password-only fallback.
- Chinese login with English selectable, matching the user's language preference where practical. Preserve existing dashboard language cookies and switching.
- Configure Headplane native OIDC, `disable_api_key_login: true`, `use_end_session: true`, exact post-logout return, and disable trusted proxy authentication. Remove Nginx Basic auth and stop injecting the proxy principal. Delete legacy app sessions during cutover. Old Basic credentials and spoofed headers alone must no longer grant entry.
- Use an eight-hour maximum application session and align provider lifetime where supported; disable remember-me persistence. Native dashboard sessions are not claimed to support global immediate revocation when a provider session is ended elsewhere.
- Logout through Headplane must delete its current server-side session and expire its cookie, then invoke Casdoor's OIDC end-session endpoint with the ID token and registered return URI. Verify it also ends provider SSO and that the logged-out page remains after refresh. Logging in again must require fresh password/second-factor interaction. Other independent browser sessions are not claimed to be globally logged out.

## Owner migration and data protection

Before cutover, obtain and verify the provider user's exact stable `sub` from the configured token model and candidate callback. Stop only Headplane briefly and take a fresh consistent private backup. In a guarded SQLite transaction, assert exactly one owner with subject `proxy:admin`, no collision with the target subject, and the expected existing Headscale link. Change only that row's subject; preserve its database ID, owner role, capabilities, and `headscale_user_id`. Delete all old application sessions and retain a private migration receipt for rollback.

Recheck owner role and Headscale link after a real OIDC callback because the callback attempts automatic linking. Do not assign all provider identities the old owner's subject, change Headscale users, or roll back its device database. Snapshot and compare device identity fields and keys before/after.

## Candidate, rollout, and verification

Use new staging/rollback directories and an isolated dashboard database copy. Install/configure the provider privately first, initialize all credentials before exposing routes, and create a disposable test user with an independent temporary TOTP seed. Test password + QR enrollment + forced TOTP + OIDC callback + bilingual dashboard + logout end to end at the real IP HTTPS origin; validate provider subpath assets and static UI requests. Do not enroll or retain the owner's production seed on their behalf. Remove the test account and all temporary seeds/sessions.

Before production cutover, confirm the actual owner can reach required enrollment using their current password. After deployment the operator performs enrollment in their browser. If deployment cannot safely present that flow, preserve the current authentication and report the concrete blocker.

Acceptance checks: wrong password/code denial and rate limits, password-only denial, enrollment required, recovery-code one-time behavior, direct API-key document/data POST rejected with no session, old Basic and spoofed headers denied, owner permissions/link unchanged, fresh-cookie security properties, copied-cookie failure after logout, provider SSO ended, logout marker stable, and both language views working. Validate anonymous protected data/actions, exact redirect allowlists, mismatched state and expired/reused authorization codes. Provider metadata may be public; protected dashboard data may not be.

Run appropriate app typecheck/lint/unit suites/builds for both language views, new regression tests, candidate and public HTTP/browser acceptance, and relevant service health checks. Verify Headscale config/control/DERP/STUN, device identities, blog HTTPS, monitoring, certificate renewal, key rotation and backups after cutover. No production user/device creation is part of testing.

## Backup, rollback, and Git

Extend the existing daily private backup with a consistent SQLite backup of the provider and protected config/encryption/signing keys/client credentials/runtime image IDs. Verify database integrity and an isolated restore; verify private modes and manifests. Never copy SQLite files with an active WAL using a naive file copy. Secret paths may appear in templates; secret values, seeds, recovery codes and data must not enter Git.

On failed readiness/acceptance, stop Headplane and restore only saved Nginx/Headplane config and the specific migrated owner-sub/session state; restore old Basic protection and verify it. Do not restore Headscale device data. A successful migration must not leave the old public authentication path as an MFA bypass. Keep earlier image and configuration rollback points intact.

Implementation uses a focused Git branch based on the recovered bilingual history. Commit required app fixes/tests, provider deployment/migration/backup/verification tooling, and release documentation as meaningful units. Check secrets before pushing. Record tested revision and immutable deployed image IDs. Do not claim deployment until actual acceptance evidence exists.

## Primary references

- [Candidate comparison and pinned-source evidence](../../research/2026-11-13-mfa-alternatives.md)
- https://casdoor.ai/docs/basic/server-installation/
- https://casdoor.ai/docs/organization/mfa-items/
- https://casdoor.ai/docs/user/multi-factor-authentication/
- https://casdoor.ai/docs/how-to-connect/oidc-client/
- https://github.com/casdoor/casdoor/blob/v4.27.1/controllers/account.go
- https://github.com/casdoor/casdoor/blob/v4.27.1/routers/base_path.go
