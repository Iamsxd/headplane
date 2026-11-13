# Headplane Casdoor / SQLite MFA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace cached Basic dashboard login with password + mandatory TOTP and working federated logout.

**Architecture:** A pinned official Casdoor service uses SQLite behind the existing IP HTTPS proxy at `/auth/`. Headplane uses native OIDC, preserves the owner row and bilingual backend, and rejects disabled API-key login server-side. Stage with a disposable account and copied database before guarded cutover.

**Tech Stack:** Headplane 0.8.2, Node 24.22.1, pnpm 10.4.0, Casdoor v4.27.1, SQLite, Nginx, systemd, Docker, Python 3.

**Spec:** [Approved design](../specs/2026-11-13-headplane-casdoor-mfa-design.md), approved by operator on 2026-11-13.

## Global Constraints

- Keep `https://140.143.127.180/admin/`, existing password, owner identity/permissions, Headscale link and Chinese/English switching.
- One extra provider service, SQLite; no external database server or provider fork.
- Require TOTP enrollment, verification and one-time recovery; no remembered-MFA bypass or password-only grant.
- Initial Casdoor memory limit 512 MiB; measure candidate before accepting.
- Explicit Secure/HttpOnly/SameSite=Lax application cookies, eight-hour maximum session, native provider logout.
- Provider loopback only; exact callback `/admin/oidc/callback` and logout return `/admin/login?s=logout`.
- No production seeds or recovery codes in chat, artifacts, Git or build contexts; operator enrolls their own phone.
- Fresh backup/rollback, no Headscale database rollback, no interruption of network services, secret scan before push.

## Review Focus

- Malformed or `.data` API-key POST must fail before parsing/validation/session creation when disabled (Task 1).
- IP subpath assets, issuer and cookie origin must work without relaxed token validation (Task 2).
- An unenrolled account, alternate grant or reused recovery code must not bypass MFA (Task 3).
- Logout must revoke copied application cookies and provider SSO after refresh (Task 4).
- Owner collision/mismatched link and active SQLite WAL must abort migration or produce consistent backup (Task 5).

---

### Task 1: Enforce the application authentication boundary

**Files:** Modify `app/routes/auth/login/action.ts`, `app/server/web/auth.ts`, `tools/build-language.py`, `CHANGELOG.md`; extend `tests/unit/auth/login-action.test.ts` and `tests/unit/auth/auth-service.test.ts`.

**Interfaces:** Existing `loginAction(args)` consults `appConfigContext` before accessing the form or Headscale. `createAuthService` sets HttpOnly and SameSite=Lax centrally for creation and destruction. Both language builds apply shared changes.

- [ ] Add disabled-login tests asserting no form parsing, Headscale calls or session creation, including malformed requests; retain enabled successful login coverage. Add session creation/destruction cookie assertions.
- [ ] Run focused unit tests on the pinned remote build environment; save expected failing output.
- [ ] Implement minimal guard and cookie defaults, with explicit English build patches and shared test propagation. Add user-facing changelog entry.
- [ ] Run focused tests, typecheck and lint; commit `fix(auth): enforce OIDC-only login and secure session cookies`.

### Task 2: Stage an initialized private provider

**Files:** Create `deployment/tencent/ops/casdoor_setup.py`, `deployment/tencent/templates/casdoor.service`, `deployment/tencent/templates/casdoor-nginx.conf`, `docs/deployment/casdoor-mfa.md`; parameterize stage path in `tools/build-language.py`.

**Interfaces:** `casdoor_setup.py inspect|prepare|verify` reads protected local credentials and writes private initialized config/data; prints only nonsecret status. Runtime manifests expose version/digest, never credentials. Configuration selects SQLite and `/auth` with the exact HTTPS origin.

- [ ] Inspect pinned upstream initialization, image metadata, SQLite support, base-path, OIDC token format and logout behavior. Pull official version image and record digest/source evidence.
- [ ] Privately initialize a dedicated org/application, ordinary owner and separate local-only maintenance identity with no demo/first-visitor access. Start hardened loopback-only service with 512 MiB limit.
- [ ] Expose only candidate login/account protocol routes through Nginx without changing `/admin/` yet. Verify metadata/assets/cookie scope, strong signing keys, exact issuer and redirects, no unused listeners, and bounded memory/logs.
- [ ] Document exact endpoints and maintenance restrictions. If official runtime cannot satisfy the design, stop cutover and report evidence; do not weaken checks.

### Task 3: Verify mandatory MFA and recovery in an isolated candidate

**Files:** Create `deployment/tencent/ops/verify_casdoor_mfa.py`; adapt existing candidate tooling without overwriting previous staging/rollback directories.

**Interfaces:** Verifier uses a disposable provider account/seed, removes it on completion, and emits a redacted JSON acceptance receipt. Candidate Headplane uses a copied database and loopback test port. Seed/code values stay in memory/private temporary storage.

- [ ] Configure Required TOTP, disable remembered MFA/signup/social/unused grants, exact confidential OIDC client with PKCE S256, and provider ordinary-user permissions.
- [ ] Verify password-only login cannot issue an authorization code until verified enrollment; wrong password/code and rate limit, recovery-code acceptance once and rejection on reuse, no password grant bypass, and no public management/bootstrap endpoints.
- [ ] Build both language views from Task 1 in a fresh stage. Run typecheck, lint, full unit tests and builds; assemble immutable image and verify asset collisions.
- [ ] Exercise real IP HTTPS OIDC callback with isolated owner and copied database; verify issuer/audience/signature/nonce, mismatched state and expired/reused authorization code denial, both languages and correct owner role/link.
- [ ] Commit deployment templates/tooling and candidate evidence references; never commit runtime state.

### Task 4: Prove end-to-end logout and bypass denial

**Files:** Extend `deployment/tencent/ops/verify_casdoor_mfa.py`; app logout/provider changes only if required by observed failing interoperability.

**Interfaces:** Existing `OidcService.buildEndSessionUrl(idToken)` targets the discovered provider end-session endpoint and exact registered return URI. Logout revokes server session and expires cookie.

- [ ] Test document and `.data` logout, copied-cookie rejection, provider session invalidation, stable `/admin/login?s=logout` after refresh and fresh password/TOTP on next login.
- [ ] Test direct API-key document/`.data` POST, old Basic credentials and spoofed identity headers cannot grant candidate access.
- [ ] If an app compatibility fix is needed, first capture its failing test, minimally fix both language builds, rerun affected checks and rebuild candidate. Commit separately with accurate evidence.

### Task 5: Back up and perform guarded production cutover

**Files:** Create `deployment/tencent/ops/deploy_casdoor_mfa.py`; extend `deployment/tencent/ops/headscale-backup.py` (or repository equivalent matching the installed backup script) with consistent provider SQLite backup; create deployment/rollback documentation.

**Interfaces:** `deploy_casdoor_mfa.py snapshot|cutover|rollback|verify` uses root-private rollback directory and expected owner `proxy:admin`, known owner row ID and Headscale ID 1. Migration changes subject only, rejects duplicate subject/owner/link mismatch, revokes legacy sessions, and records private receipt. No Headscale database restore.

- [ ] Verify consistent SQLite backup including WAL state through SQLite backup API, integrity, private modes and isolated restore. Add provider config, credentials, signing material, image IDs and manifest to daily backup.
- [ ] Snapshot live device identities/keys, service/config/timer status and current Nginx/Headplane settings. Confirm owner password can reach enrollment page without enrolling the operator on their behalf.
- [ ] Briefly stop Headplane, back up owner state, migrate exact stable subject in a guarded transaction, remove Basic/proxy auth, enable native OIDC-only config and verified image, validate Nginx then start.
- [ ] Verify unauthenticated access, no MFA bypass, callback/owner mapping, languages, Headscale control/DERP/STUN, blog, monitoring, renewal/rotation/backup timers. Roll back only dashboard config/owner mapping on failed acceptance.

### Task 6: Deliver and preserve the release

**Files:** `docs/deployment/casdoor-mfa.md`, release receipt/report in `docs/`, approved design status and this checklist.

**Interfaces:** Final receipt names tested Git revision, provider/app immutable images, tests run, backup/rollback path and operator enrollment pending/completed status without secrets.

- [ ] Remove temporary test user, seed material and candidate sessions; retain only private required rollback data.
- [ ] Verify fresh daily backup/isolated provider restore and actual public login/enrollment availability. Record resource usage and operational recovery procedure.
- [ ] Run diff checks and secret scan, commit meaningful deployment/docs changes, push to the existing fork and verify remote revision equality.
- [ ] Give operator the unchanged dashboard link and phone enrollment/recovery steps. Do not claim their production phone is enrolled before they do it.

## Execution and self-review

Operator approved deployment of the concrete design. Execute inline in the existing suitable checkout with a focused feature branch, without another permission round. Review coverage includes all design sections: authentication changes (1), provider and policy (2–3), logout (4), migration/backup/rollback/services (5), operator enrollment and Git evidence (6). Runtime inspection may settle provider-specific details within these constraints; new material incompatibilities must be reported rather than hidden.
