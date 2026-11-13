# Optional Casdoor MFA deployment result

The operator authorized official Casdoor with optional user enrollment and deployment of the existing modified Headplane. The original mandatory-enrollment acceptance gate was superseded explicitly. Production was switched on 2026-11-13; the real owner remains unenrolled so they can bind their own authenticator.

The runtime and recovery instructions are in [the deployment guide](../../../deployment/tencent/CASDOOR.md). Dashboard URL and existing password remain unchanged. The real browser verified original-account login, the Chinese account page's **多因素认证 → 设置** entry, and native logout ending on the logged-out page.

## Evidence

- Both languages passed typecheck, lint, 300 unit tests and build using pinned Node 24.22.1 / pnpm 10.4.0.
- All 13 official-provider optional-MFA checks passed: password-only login while unenrolled, code enrollment, missing/wrong factor rejection after enrollment, valid TOTP, recovery once only and optional disable.
- All 11 private candidate OIDC checks passed with normal certificate validation, real signed callback, wrong state/reused code rejection, bilingual authenticated pages, copied-cookie revocation, provider logout and identical owner role/caps/link.
- All 14 production checks passed, including original owner preservation, device/key/config identity hashes, services, STUN and maintenance timers. Komari is active.
- Consistent backups of the three SQLite databases passed integrity checks, and a temporary restored official Casdoor instance loaded the expected client and owner independently.
- An external workstation verified blocked provider management/signup/bootstrap endpoints, masked public application credentials and normal HTTPS discovery/JWKS. The maintenance identity was denied for an external forwarded client IP.
- Redacted detailed receipts remain under `/root/headplane-optional-20261113/`. Private runtime/recovery material is excluded from Git.

## Final review

An independent read-only reviewer found no critical issues and one important recovery issue: rollback restored old role/caps/link values even though deployment changed only the subject. This was corrected with regression tests. The migration now rechecks the complete owner tuple inside its write transaction; rollback restores only the expected migrated subject, preserves later permission/link edits, is idempotent for the old subject and refuses unrelated later subject changes. The regression first failed on the old behavior; all five recovery tests and six existing Python tooling tests then passed. The corrected recovery script was installed without repeating the cutover.

## Decisions and deferred work

- Ready OIDC revalidation may change a rejected API-key POST into the exact OIDC-start redirect. Acceptance permits that redirect without a session cookie or access to protected pages, as well as a 403. The action's unit tests still require rejection. This decision would be wrong if either response could establish an alternate authenticated session; the live session and protected-page checks exclude that observed behavior.
- Minor, deferred: the first-install script depends on the default configuration already extracted into the earlier staging directory. It is not a self-contained installer for a clean host. This does not affect the initialized production service or its tested backups/recovery.

The known official-provider behavior around unverified first-time MFA enablement remains accepted by the operator. No provider source changes or fork were introduced.
