# Headplane account login and TOTP design

Status: proposed, awaiting design approval. No authentication changes have been deployed.

## Intent and decisions

The operator approved replacing browser Basic authentication with account/password web login and selected a phone authenticator's six-digit TOTP code as the second factor. The existing IP dashboard and Chinese/English switching must keep working. Logout must clear the current application session and the identity-provider session, then stay on a logged-out page.

The implementation choice below is the builder's recommendation, not an infrastructure choice already made by the operator.

## Current deployment

Headplane 0.8.2 has API-key and OIDC authentication, with no built-in TOTP enrollment. Nginx currently requires Basic authentication on `/admin/`, then injects `Remote-User: admin`. Headplane resolves this trusted proxy identity ahead of application cookies. The logout endpoint expires the application cookie, but the browser resends Basic credentials and the login loader immediately redirects to machines. Reproduced through trusted public HTTPS: logout 302 to login, login 302 to machines, authenticated machines 200, no credentials 401.

One Headplane owner exists: subject `proxy:admin`, linked to Headscale user ID 1. The owner database ID, role, capabilities, and link must be preserved. There were no application sessions at inspection. Headscale and its device identities remain outside the migration.

The server has approximately 3.7 GiB RAM, 0.7 GiB in use at inspection, and 54 GiB available disk. Dashboard Node is limited to 512 MiB and listens only on loopback. IP HTTPS already has a trusted certificate and renewal.

## Approaches

1. **Recommended: native Headplane OIDC with a local Keycloak service.** Keycloak supplies password login, enforced TOTP enrollment/verification, recovery codes, account security, rate limiting, and standard logout. Its hostname implementation accepts a full HTTPS URL and can use the current IP and a dedicated `/auth` prefix. Use an official pinned release with PostgreSQL, rather than extending cryptographic/login code ourselves. It adds a service and database plus their maintenance and backup cost.
2. Domain-oriented forward-auth services such as Tinyauth/Authelia are smaller, but do not meet the current IP requirement as shipped. Tinyauth 5.2.0 explicitly rejects IPs in `SafeParseAppURL`; modifying its URL/cookie rules and logout integration would create another maintained fork. Not selected.
3. Add local password/TOTP authentication directly to the Headplane fork. It could preserve one application process, but requires maintaining credential storage, enrollment, recovery, attempts, session handling, and security fixes. Avoid this extra security implementation.

The selected user-facing approach remains the existing account/password plus phone dynamic code. Keycloak is the recommended implementation for review.

## Services and boundaries

- Keep dashboard URL `https://140.143.127.180/admin/`.
- Add Keycloak under `https://140.143.127.180/auth/`, using a dedicated `headplane` realm. Current official release discovered during planning is 26.8.2; pin its official image by digest after checking compatibility. Use a supported pinned PostgreSQL image and private database credentials.
- Nginx exposes only the dedicated realm endpoints and required static resources under `/auth/`; do not expose master-realm login, administration API/console, health, metrics, or database ports publicly. Administrative operations use SSH/local access.
- Bind the Keycloak HTTP port to loopback and keep PostgreSQL on a private container network. No new public firewall port is required. Set the external HTTPS URL explicitly, trust only the reverse proxy, and overwrite forwarding headers in Nginx.
- Use separate non-root service/container identities, capability and process restrictions, log limits, and memory limits. Initial targets: Keycloak 1 GiB container / 512 MiB maximum heap, PostgreSQL 256 MiB with conservative connections. Check real memory/startup behavior and adjust within the server's headroom before cutover.
- Preserve the bilingual architecture and its single backend context. A required application change is to enforce `disable_api_key_login` in the server login action: current 0.8.2 only hides/redirects the UI and still accepts direct API-key POST. Apply this guard to both language builds with regression coverage; otherwise the proposed MFA can be bypassed.

## Identity, session, and login policy

- Create a single realm user `admin` with the existing dashboard password, read privately from the protected credentials file. No password or client secret appears in Git, terminal output, or chat. Store private bootstrap/operator credentials with mode 0600.
- Disable self-registration, external/social providers, and password-grant/direct-access flows. Disable public user-creation routes. Other users may only be provisioned deliberately later.
- Require OTP setup on the owner's first login, verified with a code from the owner's phone before successful completion. No shared QR or production seed in chat, Git, screenshots, logs, or build context.
- Enforce a second-factor flow; an account without enrolled TOTP must complete enrollment before an authorization code is issued. Recovery codes are an alternative second factor, never password-only access. Test missing, wrong, and correct codes, enrollment, password-only denial, and attempts limits.
- Present recovery codes inside the authenticated enrollment/account flow for the operator to save privately. Explain SSH-assisted recovery if the authenticator and codes are both lost. Do not invent an always-enabled recovery login that bypasses MFA.
- Provide Chinese login where supported and keep English selectable. Existing dashboard language selection remains intact.
- Use a confidential OIDC client with exact callback `/admin/oidc/callback`, PKCE, strict issuer/JWKS validation, and an exact registered post-logout return URI `/admin/login?s=logout`. No wildcard redirect URIs.
- Enable `disable_api_key_login`, enforce it in the server action before processing any submitted key, and disable proxy authentication in Headplane. Strip incoming identity/Authorization headers in Nginx. Verify both document and React Router data/action API-key POSTs cannot create a session, and no existing legacy sessions survive cutover.
- Use an eight-hour maximum application and identity-provider session, with no persistent remember-me login. Explicitly configure the application authentication cookie as Secure/HttpOnly/SameSite=Lax and verify its Set-Cookie header. Current 0.8.2 does not explicitly enable HttpOnly, so this is a required shared application change with regression coverage, not an assumption about existing behavior.
- Enable Headplane RP-initiated OIDC logout. Logout must delete its current session row, expire its cookie, end the provider SSO session, and render the stable logged-out page. Subsequent login must require a fresh password/MFA interaction. Independent sessions on other browsers are not claimed to be globally revoked.

## Owner migration

Obtain the new user's stable, verified Keycloak `sub` before cutover. Stop only Headplane briefly; take a fresh private consistent backup; in a guarded SQLite transaction change only the existing owner's `users.sub` from `proxy:admin` to that exact UUID. Assert there is exactly one matching owner and no target-sub collision. Preserve user ID, role, capabilities, and `headscale_user_id`. Revoke all pre-migration application sessions. Start with OIDC configured and immediately verify owner permissions.

Do not use a hardcoded claim that grants every identity the old owner subject. Do not change Headscale user records, node keys, addresses, ACLs, DERP keys, or device registrations. Capture and compare identities before/after migration. Verify the owner's Headscale user link again after an actual OIDC callback, because the callback attempts automatic identity linking.

## Staging and rollout

Use new staging and rollback directories; never overwrite earlier release rollback points. Back up Nginx/Headplane configuration, credentials, and the Headplane database. Stage the identity service and an isolated Headplane candidate using a copied database. Use a temporary test account with an independent disposable TOTP seed to test the full password/MFA/OIDC/logout cycle without enrolling the owner's authenticator on their behalf. Remove test users, seeds, and sessions afterwards.

Before production cutover, verify login/enrollment works at the real IP origin and that the owner will be shown the phone-binding flow. The operator performs their own enrollment after deployment. If enrollment cannot be reached safely, retain the existing authentication and report the blocker.

After cutover, verify anonymous data/action requests require authentication, spoofed headers and old Basic credentials do not grant entry, missing MFA cannot enter, both dashboard language views load after full MFA, logout invalidates the copied application cookie and does not silently re-login, mismatched OIDC state is rejected, and expired/reused authorization codes cannot establish a session. This does not claim that the current state cookie itself is server-expiring or single-use; that broader change is outside this migration. Use the existing upstream OIDC tests where relevant and add regression coverage for the two required shared application changes.

Run Headscale config/health/control-key/DERP/STUN checks, compare device identities, and confirm blog HTTPS, monitoring, key rotation, certificate renewal, and backups remain healthy.

## Backup, rollback, and Git

Add consistent PostgreSQL backup to the daily private backup process; include protected identity-service config, realm state, credentials, and runtime image IDs. Verify a restore in an isolated database and secret-file permissions. Git contains templates and code, never databases, secrets, recovery codes, or backup archives.

If readiness, OIDC, owner mapping, MFA, or logout acceptance fails, restore the saved Nginx/Headplane config and only the touched owner-sub/session data from the migration snapshot while Headplane is stopped. Do not restore Headscale device databases. Restart Headplane, test old Basic protection, and report the failed cutover honestly. The old public authentication must not coexist as an MFA bypass after a successful migration.

Git branch for implementation: a separate focused MFA branch descended from the recovered bilingual/release-management commits. Commit config, migration, verification and any app changes separately as meaningful units. Record tested commit and deployed image IDs in the release note. No upstream PR is part of this request.

## Sources

- https://headplane.net/features/sso
- https://www.keycloak.org/server/hostname
- https://www.keycloak.org/server/reverseproxy
- https://www.keycloak.org/2025/10/recovery-codes
- Keycloak 26.8.2 `HostnameV2ProviderFactory.java` inspected during planning; Tinyauth 5.2.0 `internal/utils/app_utils.go` inspected and rejects IP addresses.
