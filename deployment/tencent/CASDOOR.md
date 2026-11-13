# Casdoor account login and optional TOTP

Deployed on 2026-11-13, following the operator's explicit change from required enrollment to optional MFA. Casdoor is the official unmodified v4.27.1 image with SQLite; there is no provider fork.

- Dashboard: `https://140.143.127.180/admin/`
- Account settings: `https://140.143.127.180/auth/account`
- The existing administrator username and password remain valid. Its Headplane owner row, role, capabilities and Headscale user link are preserved. The Casdoor user is an ordinary user, distinct from private provider maintenance administration.
- In account settings, select **多因素认证 → app → 设置**, scan with a TOTP authenticator, verify its code and save the one-time recovery code. Enrollment is optional. Once enabled, a fresh password login requires a factor. The operator enrolls their own phone; production TOTP was not pre-enabled.
- Headplane uses native OIDC with PKCE and provider logout. Basic authentication and trusted proxy identities have been removed. Direct API-key login is disabled in both language views, including during provider outages.

## Pinned runtime

| Component | Immutable image ID |
| --- | --- |
| Headplane bilingual 0.8.2, local auth fixes | `sha256:8548bee3872a70b3cab2c8bfc30262bd5ebeeb0bd5bcd9cf357c85188e56c25f` |
| Official Casdoor v4.27.1 amd64 | `sha256:3af7268ddfcfac032bfff4fc67acaea284278269c6caf5bc761609ac25a6596b` |

Headplane is bound to `127.0.0.1:3000`; Casdoor's container port is published only on `127.0.0.1:18000`. Both containers run without root and with read-only root filesystems, dropped capabilities and memory limits. Nginx uses the existing trusted IP certificate and renewal timers. Headscale, DERP/STUN, SSH, blog configuration and Komari are unchanged.

Provider configuration is under `/etc/casdoor`; SQLite and private file sessions are under `/var/lib/casdoor`. Passwords, client/signing secrets, MFA material, runtime databases and backups are never repository inputs. The maintenance identity/application/organization allow only loopback client IPs, and the public proxy overwrites forwarding headers. Nginx exposes protocol and self-service APIs while blocking provider management, public signup and password bootstrap. Authentication requests are excluded from Nginx access logs.

## Scripts and recovery

`ops/casdoor-setup.py` is a first-install initializer and refuses existing provider directories. Install `casdoor.service` first, then initialize privately before exposing `casdoor-proxy.conf`. It reads the existing protected dashboard login file and writes root-private maintenance/client credentials. It never outputs them.

`ops/verify-casdoor.py` creates and removes a disposable account, testing password-only login, successful TOTP enrollment, missing/wrong factor rejection, correct TOTP login, recovery acceptance/single use and optional removal. It does not test the superseded mandatory-enrollment policy or enroll the real owner.

`ops/verify-headplane-oidc.py` uses a consistent copy of the dashboard database with no copied live sessions, a new signing secret and a temporary TLS listener on loopback only. It checks real provider exchange/signatures through Headplane, wrong state, reused codes, role/link preservation, both languages, API-key denial and local/provider logout. It removes its temporary container/config/database afterward. The OIDC state-cookie implementation remains upstream; no server-side single-use/expiry claim is made about that cookie.

`ops/deploy-casdoor.py` requires passing acceptance receipts, asserts the exact old owner and checks for subject collisions. It backs up before switching, verifies a restored provider in an isolated temporary container, migrates only the dashboard owner subject, invalidates dashboard sessions, replaces its image/config/proxy and checks real production login/logout. On failed acceptance it automatically restores dashboard configuration and owner mapping. It never restores the Headscale database.

The deployment's private rollback state and redacted receipts are in `/root/headplane-optional-20261113/`. To undo this specific cutover while that state is still applicable:

```sh
python3 /root/headplane-optional-20261113/deploy-casdoor.py rollback
```

The daily `/usr/local/sbin/headscale-backup.py` now backs up all three SQLite databases using SQLite's consistent backup API, including committed WAL content. It also saves provider configuration, client/maintenance credentials, pinned image environment, service and proxy files alongside existing identity keys and dashboard secrets. Backups are root-private under `/var/backups/headscale/`. They are sensitive recovery material. Pre/post-cutover snapshots passed integrity checks; an isolated restored Casdoor successfully loaded the original client and owner. No production phone or seed is needed for these checks.

For a future domain change, update the provider `origin`/`originFrontend`, Headplane issuer/base URL, the exact callback/logout redirect registrations and Nginx/TLS together. Preserve the provider database and stable user subject so the owner mapping does not change.

## Verification receipt

- Both language views: Node 24.22.1 / pnpm 10.4.0, typecheck, lint, 300 unit tests each and build passed. Existing upstream lint/Vite warnings remain.
- Official optional-MFA tests, real TLS OIDC callback, mismatched state/reused code rejection, copied-cookie revocation, provider logout and refresh passed.
- Original owner ID/role/capabilities/Headscale link and all three device identities, Headscale keys/configuration were unchanged.
- Provider/database restored independently; production services, STUN, renewal/key rotation/backup timers and Komari remained active.
- Normal browser login with the original credentials and the Chinese account MFA settings entry were verified.

Historical required-enrollment rejection receipts remain in earlier commits. They are not the acceptance policy for this optional-MFA deployment.
