# Lightweight MFA candidates for Headplane

Date: 2026-11-13. Research only; no authentication software was installed and no production login configuration changed.

## Operator requirements

Keep account/password login and add a phone authenticator's TOTP code. Support the existing IP HTTPS endpoint and normal logout. Avoid the proposed Keycloak plus PostgreSQL service pair. Retain Chinese/English dashboard switching, owner permissions, device identities, private backups, and Git history.

## Recommendation for selection: Casdoor with SQLite

Official release checked: `v4.27.1`, published 2026-11-10; source commit `2213c440aa2ce100f4d47efc1c0be3d7d47417fe`.

- Official installation documentation supports SQLite 3 as an application database. It is a local data file used by the authentication service, without a separate PostgreSQL/MySQL process or container.
- Official MFA documentation describes password plus six-digit TOTP, QR enrollment, and one-time recovery codes. An organization's MFA item can be Required, which requires setup before sign-in completes. MFA remember-device behavior must be disabled for the intended policy.
- Chinese and English are supported by the application. This avoids maintaining an extra login-page translation fork.
- Standard OIDC discovery includes PKCE S256 and an end-session endpoint. Headplane can use its native OIDC connector rather than a custom password/TOTP implementation.
- The stable source includes `conf.GetBasePath()` and `routers/base_path.go`, including path-prefix routing and frontend asset URL handling. This permits an intended `/auth/` reverse-proxy layout without consuming Headscale's root/control paths or moving the dashboard from `/admin/`.
- IP HTTPS is the intended integration target. URL/configuration/source review is not a completed interoperability test: a candidate must verify actual issuer/JWKS discovery, IP-origin cookies, callback URLs, QR enrollment, forced TOTP, recovery codes, and RP-initiated logout before production cutover. Do not claim a working deployment based on this research.

The operational advantage over the previous proposal is one additional service with SQLite, rather than an identity service plus a database server. No runtime-memory figure is claimed; measure the selected candidate and set a resource limit during staging.

## Alternative: VoidAuth with SQLite

Official release checked: `v1.19.1`, published 2026-11-11; source commit `41ecbb0493e74a70d9fa53502dfc4e0d9bd709bb`.

- Official tagged documentation includes a one-container `DB_ADAPTER=sqlite` deployment and an `APP_URL` with a subpath.
- `server/util/config.ts` accepts a valid URL, derives the base path, explicitly detects IPv4/IPv6 addresses, and omits the cookie Domain for IP hosts. It does not require a DNS domain for the reviewed configuration.
- `MFA_REQUIRED` and per-client MFA policy require a second factor. TOTP setup verifies a code before activating the secret; failures are counted per account. The source includes Chinese translations and an OIDC session-end flow.
- Published security advisories inspected during selection list fixes at 1.15.1, 1.15.2, 1.16.0, 1.17.0, and 1.18.0; the reviewed 1.19.1 release is newer. This is version selection, not a complete security audit.
- One-time recovery codes were not verified in this candidate, so do not promise that feature. Casdoor is recommended here because the original intended enrollment flow also included recovery codes.

## Other candidates excluded

Tinyauth 5.2.0 explicitly rejects IP application URLs in its `SafeParseAppURL` implementation. Pocket ID uses passkeys rather than the requested password plus TOTP. Authentik requires PostgreSQL. No patched fork of an authentication provider is proposed merely to bypass its domain validation.

## Integration requirements that still apply

The earlier investigation found that Headplane 0.8.2's `disable_api_key_login` is not enforced by the server-side login action. Any OIDC/MFA migration must add that guard to both language builds and verify document and data/action requests cannot bypass MFA. Explicit Secure/HttpOnly/SameSite cookie settings and logout/session invalidation also need regression coverage.

Reuse the current password privately, close public sign-up and unused password-only grants, require owner MFA enrollment, preserve the Headplane owner's database identity/Headscale user link, and keep Headscale devices and control/DERP/STUN routes untouched. Stage with a disposable test account and copied dashboard database. Back up the new SQLite file consistently together with provider configuration and secrets outside Git. Keep a configuration/owner-mapping rollback point. The final selected provider's exact issuer, subject, endpoints, administrative restrictions, and rollout procedure belong in its approved implementation design.

## Primary sources

- https://casdoor.ai/docs/basic/server-installation/
- https://casdoor.ai/docs/basic/configuration/
- https://casdoor.ai/docs/user/multi-factor-authentication/
- https://casdoor.ai/docs/organization/mfa-items/
- https://casdoor.ai/docs/how-to-connect/oidc-client/
- https://github.com/casdoor/casdoor/blob/v4.27.1/routers/base_path.go
- https://github.com/casdoor/casdoor/blob/v4.27.1/conf/conf.go
- https://github.com/voidauth/voidauth/blob/v1.19.1/docs/Getting-Started.md
- https://github.com/voidauth/voidauth/blob/v1.19.1/docs/Configuration.md
- https://github.com/voidauth/voidauth/blob/v1.19.1/server/util/config.ts
- https://github.com/voidauth/voidauth/security/advisories
