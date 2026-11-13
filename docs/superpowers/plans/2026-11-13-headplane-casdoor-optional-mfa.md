# Casdoor Optional MFA Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace cached Basic login with official Casdoor account login and user-selected TOTP.

**Architecture:** Official pinned Casdoor v4.27.1 with SQLite at `/auth/`, loopback only behind existing IP HTTPS. Native Headplane OIDC preserves the existing owner and bilingual UI. Prepare and verify a temporary user/candidate, then back up and cut over with scoped rollback.

**Tech Stack:** Node 24.22.1, pnpm 10.4.0, Headplane 0.8.2, official Casdoor v4.27.1 image config `sha256:3af7268ddfcfac032bfff4fc67acaea284278269c6caf5bc761609ac25a6596b`, SQLite, Python 3, Docker, systemd, Nginx.

**Spec:** [Operator override and retained architecture](../specs/2026-11-13-headplane-casdoor-mfa-design.md).

## Global Constraints

- User explicitly authorizes replacement, optional MFA, official unmodified provider, no maintained provider fork.
- Keep `https://140.143.127.180/admin/`, existing password/owner ID/role/caps/Headscale link and bilingual switching.
- Native OIDC only for dashboard login; API-key and spoofed proxy identities remain disabled. Unenrolled users may use password alone. Enrolled users require a factor.
- Keep provider management private; ordinary dashboard administrator is not a Casdoor administrator. Disable public signup and unrelated grants/methods.
- No actual seeds/recovery codes/passwords/runtime DBs in Git, logs or chat; production enrollment belongs to the operator.
- Preserve network identities/control/DERP/STUN, blog configuration and maintenance timers; fresh consistent backups and guarded rollback; no device DB rollback.

## Review Focus

- OIDC outage must not offer a disabled API-key form (Task 1).
- Subpath frontend assets, IP cookies and exact issuer/claims must work with normal TLS validation (Tasks 2–3).
- Optional MFA must allow ordinary login, but an enrolled account cannot bypass its code and recovery cannot be reused (Task 3).
- Logout must revoke the local copied cookie and provider SSO, and stay logged out after refresh (Task 3).
- Owner migration/link mismatch, provider WAL backup and failed cutover must leave recoverable state without changing devices (Task 4).

### Task 1: Complete native login readiness

**Files:** `app/routes/auth/login/page.tsx`, `tools/build-language.py`, `tests/unit/auth/login-page.test.ts`, `CHANGELOG.md`.
**Interfaces:** Login loader returns `isApiKeyLoginEnabled: boolean`; page renders the API-key form only if true. Existing shared backend/dual-view architecture and app guard/cookie fixes remain.

- [ ] Add a failing loader/SSR or rendered response test for a disabled key login when provider discovery fails; retain enabled behavior.
- [ ] Implement the explicit flag and conditional form in both views; run focused tests then full typecheck/lint/unit/build in a fresh stage, assemble image.
- [ ] Commit app readiness changes with tests and changelog.

### Task 2: Provision initialized official Casdoor

**Files:** `deployment/tencent/ops/casdoor-setup.py`, templates `casdoor.service`, `casdoor-proxy.conf`, deployment guide.
**Interfaces:** Root-only setup `prepare|configure|expose|inspect` writes protected `/etc/casdoor` config/credentials and `/var/lib/casdoor` SQLite/session data, never emits secrets. Official runtime starts through systemd with 512 MiB limit and loopback published port. Organization uses TOTP rule `Optional` and zero remembered-factor hours. Stable owner subject is saved privately for migration.

- [ ] Initialize random maintenance credentials and SQLite privately; provision ordinary owner with current password, dedicated OIDC application, strong generated signing cert, exact redirects, authorization-code/PKCE only.
- [ ] Disable demo/signup/bootstrap and restrict maintenance identity to local trusted proxy IP. Add `/auth/` Nginx routes while leaving existing `/admin/` protection intact.
- [ ] Verify trusted public HTTPS discovery/JWKS/asset paths and account UI, secure scoped cookies, private management APIs and no extra public listener.

### Task 3: Verify official optional MFA and federated logout

**Files:** `deployment/tencent/ops/verify-casdoor.py`, candidate setup; no provider source modifications.
**Interfaces:** Disposable test account + isolated Headplane database at loopback candidate port; temporary HTTPS candidate routing reuses `/admin/oidc/callback` with an exact test-only route/header, without exposing copied sessions or changing live owner auth. Redacted receipts gate cutover.

- [ ] Test password-only OIDC success for unenrolled test user, exact stable subject/owner preservation, both languages and no API-key bypass.
- [ ] Through official endpoints/UI enable TOTP with a real generated test code; verify wrong/missing code rejection, valid code login, recovery accepted once and rejected on reuse, and optional disable flow.
- [ ] Verify real callback issuer/signature/audience/nonce, mismatched state and reused code rejection, logout revocation/current provider session and stable logged-out page. Remove test seeds/accounts/sessions before delivery.

### Task 4: Back up and cut over

**Files:** `deployment/tencent/ops/deploy-casdoor.py`, existing `tencent-headscale-backup.py`, nonsecret production config/proxy templates.
**Interfaces:** Deployment records private rollback state, asserts expected single owner `proxy:admin` and Headscale link `1`, changes only its subject in a transaction, deletes old app sessions, replaces Basic/proxy auth with verified native OIDC and immutable image. Rollback restores only dashboard config/owner mapping; no Headscale DB restore.

- [ ] Add consistent provider SQLite backup plus protected config/signing/client secrets/service/image manifests to daily backup; test integrity and isolated restore.
- [ ] Snapshot devices/keys/config/services and create a fresh pre-cutover backup, guarded owner migration, `nginx -t`, switch and verify actual production owner callback/permissions.
- [ ] Confirm HTTPS login/logout, owner unchanged, optional MFA page, language switching, control/DERP/STUN, timers/monitoring and protected backups. Roll back scoped dashboard changes if acceptance fails.

### Task 5: Review and deliver

- [ ] Fresh read-only whole-branch review; fix material findings and verify each fix.
- [ ] Secret/diff checks, meaningful commits and push; record deployed immutable IDs and recovery instructions. Report actual live URL, same credentials, where to enable optional TOTP, and any remaining limitation.

## Execution

Continue inline on the existing `feat/casdoor-mfa` branch. User's explicit latest instruction supersedes the old mandatory-MFA gate. Preserve earlier failed mandatory-enrollment evidence as history, not as the acceptance policy for this optional-MFA deployment. Do not ask the user to enroll a phone or share a code to complete the replacement.
