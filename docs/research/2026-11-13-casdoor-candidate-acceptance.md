# Casdoor candidate rejected before production cutover

Date: 2026-11-13 (Asia/Shanghai). Deployment is **incomplete**. The approved design requires a valid authenticator code before enrollment activation. Actual official runtime testing did not satisfy that requirement. No public authentication routes, Nginx configuration, systemd services, production owner mapping or live image were changed.

## Official candidate and isolation

- Version: Casdoor v4.27.1; reviewed source commit `2213c440aa2ce100f4d47efc1c0be3d7d47417fe`.
- Official Docker Hub index: `sha256:a0499a9e1bc0c089af79f19b16b866432bc9519a495e286ac7c558181c302b2a`.
- Linux amd64 manifest: `sha256:7e8ab89f046b24960a2a6ccab338935d787f21c55690114478dd3cae604631cf`.
- Loaded image config: `sha256:3af7268ddfcfac032bfff4fc67acaea284278269c6caf5bc761609ac25a6596b`.
- The server could not reach Docker Hub; download through the local official registry API verified each manifest/blob SHA-256 and each uncompressed rootfs diff ID before transfer and `docker load`. No mirror or modified provider image was used.
- Private SQLite/WAL candidate with generated maintenance credentials and disposable ordinary accounts; non-root user 1000, read-only root, dropped capabilities, no-new-privileges, pids 128, memory 512 MiB, loopback port 18000 only. Observed idle Docker memory: approximately 34 MiB; this is not a production-load benchmark.
- Configured organization TOTP `Required`, remembered MFA zero hours, confidential authorization-code-only client with PKCE S256, SQLite, `/auth` base path and explicit IP HTTPS origin. No production owner account was provisioned.

## Observed acceptance failure

The final check produced:

```json
{
  "password_only_requires_enrollment": true,
  "invalid_setup_code_rejected": true,
  "unverified_enable_rejected": false,
  "code_issuance_blocked_after_unverified_enable": false,
  "id_token_denied_after_unverified_enable": false,
  "ordinary_test_user_is_not_admin": true
}
```

A fresh ordinary test account was prompted for required enrollment after password validation. An invalid dynamic code was rejected by the verification endpoint. However, skipping successful verification and directly calling the activation endpoint succeeded; the same pending browser session could then obtain an authorization code and exchange it with PKCE for an ID token. No valid TOTP was submitted and no recovery code was redeemed as a login factor; provider-generated recovery material was submitted to the setup endpoint. Only test accounts and in-memory test seeds were used; the script deletes its account in `finally` and prints no credentials or tokens.

This demonstrates a failure to enforce verified enrollment. It does **not** establish that an attacker can log into an already enrolled account without its second factor. The normal web UI includes a verification step; that UI step alone does not satisfy the approved server-enforced requirement.

The pinned source explains the behavior: `controllers/mfa.go` records a successful verification but `checkMfaSetupDest` exempts TOTP from the proof check; `MfaSetupEnable` calls `TotpMfa.Enable`, which stores the supplied secret and recovery material without validating a TOTP. The pending sign-in check thereafter tests that a required factor exists. Sources:

- https://github.com/casdoor/casdoor/blob/v4.27.1/controllers/mfa.go
- https://github.com/casdoor/casdoor/blob/v4.27.1/object/mfa_totp.go
- https://github.com/casdoor/casdoor/blob/v4.27.1/controllers/auth.go

The repeatable candidate scripts are in `tools/casdoor-candidate/`. Redacted remote receipt: `/root/headplane-mfa-20261113/enrollment-acceptance.json`. Public IP HTTPS/browser interoperability, recovery-code reuse, native provider logout, backup restore and production migration remain unverified. A successful private metadata/SQLite test is not evidence those gates passed.

After verification, the disposable provider container, candidate database/configuration/session state and the isolated app database copy were removed. Generated candidate credentials, signing keys and test enrollment material were not retained. The official image, built app image, source/build logs and redacted boolean receipts remain available for a later authorized implementation. Headscale, Headplane and Nginx were active after cleanup.

## Headplane hardening prepared independently

Task 1 fixes are prepared on `feat/casdoor-mfa`: server-side disabled API-key guard before form parsing, explicit HttpOnly/SameSite=Lax cookies, and logout expiration with `Max-Age=0`. Both language builds receive the same changes while retaining one backend.

- Baseline: 23 unit files / 294 tests passed.
- Regression RED: missing HttpOnly and processing disabled-login malformed forms reproduced before the implementation.
- Final Chinese and English: each 24 files / 298 unit tests passed, typecheck/lint/build passed. Lint reports the same three warnings as the existing source; zero errors. Vite native-config extension warnings remain visible in build/typecheck logs.
- Assembled candidate image: `sha256:05cac3575e1d5a9b60e2ac9bcba4cd931f73115840008cf0860515ef9d664bcd`.
- Real HTTP candidate checks passed for form and malformed document/`.data` POST rejection with 403/no session cookie, spoofed Basic/proxy principal denial, and both language logged-out pages. Candidate used a consistent dashboard DB copy and was removed afterward.

These fixes and image are **not deployed**. The live image remains `sha256:9ce135fc8b7c06f2c8a930d106639cd00adf44efe8bcf1ac81fdcab339774397`. The current Basic-auth logout behavior therefore remains pending the authentication migration.

Independent branch review confirmed the application guard/cookie changes and provider rejection evidence. Review fixes make acceptance checks survive optimized Python, inspect repeated response fields without case sensitivity, require an authentication redirect and visible translated logout text, stage a fresh loopback-only app with a fresh signing secret and cleared copied sessions, and refuse any existing build output directory instead of deleting it. Regression tests reproduce the original false success under `-O` and deletion of pre-existing language/image sentinels before the fix. Provider-outage API-key form visibility remains an explicitly deferred UI issue: the server rejects disabled login even if that form is shown.

Additional health observation: public dashboard retained trusted HTTPS/Basic protection (401), Headscale `/health` returned 200, the backup/key rotation/certificate timers remained active, and local blog HTTPS with `lovecanl.cn` SNI returned 200. A public blog TLS handshake from the workstation failed in both Python and curl; DNS still pointed to this server. This work made no blog/proxy/firewall changes, and the cause of that separate public connectivity issue was not established.

## Required decision

The approved design expressly excludes a maintained provider fork. Do not silently relax verified enrollment or patch a provider image. The concrete extension, if authorized, is a separately managed Casdoor fork that binds a successful TOTP verification to the exact user, secret and enrollment session, requires and consumes that proof at activation, and tests missing/mismatched/replayed proof before the full original acceptance process. This adds responsibility for tracking upstream provider security updates.

Otherwise keep production unchanged and evaluate another SQLite/password/TOTP/OIDC provider against IP HTTPS, mandatory verified enrollment, recovery and logout requirements before recommending it. No unverified alternative is promised as ready.
