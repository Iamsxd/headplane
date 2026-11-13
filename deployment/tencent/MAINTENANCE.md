# SSH access and Debian security maintenance

## Production change, 2026-11-13

The operator approved closing SSH password authentication and installing pending system updates. This record covers those two maintenance items on `140.143.127.180`.

SSH remains on port `23546`. A fresh key-only connection succeeded before the change. `/etc/ssh/sshd_config.d/00-key-only.conf` now contains [the tracked key-only settings](templates/00-key-only.conf). Both password and keyboard-interactive authentication are disabled; root can authenticate with its existing authorized public key. The existing private key and its passphrase policy were not changed.

The main configuration includes drop-ins before its older `PasswordAuthentication yes` and `PermitRootLogin yes` entries. OpenSSH takes the first applicable value; the early drop-in supplies the enforced settings. Validate the effective configuration rather than inferring it from a single line in the main file:

```sh
/usr/sbin/sshd -t
/usr/sbin/sshd -T | grep -E '^(port|pubkeyauthentication|passwordauthentication|kbdinteractiveauthentication|permitrootlogin|authenticationmethods) '
```

Expected values are `23546`, `yes`, `no`, `no`, `without-password` (OpenSSH's normalized spelling of `prohibit-password`), and `publickey`, respectively. Check any applicable `Match` blocks with `sshd -T -C` when changing access rules.

A five-minute systemd rollback timer was armed before reloading SSH. A separate connection with public-key authentication then succeeded, and an unauthenticated protocol probe advertised only `publickey`. The rollback timer was cancelled after these checks. Both tests were repeated after upgrading OpenSSH.

## Package updates and automatic security updates

APT indexes were refreshed and the upgrade was simulated first. The completed upgrade changed 115 installed packages and added four kernel packages, without removals or held-back packages. `unattended-upgrades` and its two required Python dependencies were then installed. In total, 115 packages changed, seven were added and none were removed. This stayed within Debian 13; no distribution upgrade was performed.

The package commands ran in a detached systemd service so losing the SSH transport would not interrupt dpkg. They used noninteractive debconf, `--no-remove`, and dpkg's `--force-confdef` / `--force-confold` handling to preserve locally modified configuration. Both commands exited successfully. Package results and private logs are in `/var/backups/server-maintenance/20261113T095028Z/`.

The installed automatic-update configuration is tracked as:

| Server path | Reference |
| --- | --- |
| `/etc/apt/apt.conf.d/20auto-upgrades` | [Daily APT settings](templates/20auto-upgrades) |
| `/etc/apt/apt.conf.d/52security-only` | [Security-only policy](templates/52security-only) |

The policy clears the package's broader default origins and allows only `origin=Debian,codename=trixie-security,label=Debian-Security`. Automatic reboot and automatic dependency/kernel removal are disabled. The existing `apt-daily.timer` and `apt-daily-upgrade.timer` are enabled and active; their distribution-provided random delays remain in use. Automatic updates can restart affected services as part of package installation. Review the logs and arrange reboots when kernel updates require them; security-only automation does not replace periodic review of ordinary Debian updates or the separately pinned application images.

Verify policy and scheduling with:

```sh
apt-config dump
unattended-upgrade --dry-run --debug
systemctl list-timers apt-daily.timer apt-daily-upgrade.timer
apt-get -s upgrade --with-new-pkgs
dpkg --audit
```

The recorded dry run resolved exactly the security origin above and exited successfully. The final APT simulation reported zero upgrades, additions, removals or packages held back; `dpkg --audit` was empty and `apt-get check` passed.

## Backups and verification

Before changing SSH or packages:

- Consistent application snapshot: `/var/backups/headscale/20261113T095029112125Z`.
- Root-private configuration/package-state snapshot: `/var/backups/server-maintenance/20261113T095028Z`. Its archive contains SSH/APT configuration, authorized public keys, OS/package state; separate files record installed versions, selections, SSH effective settings and node identities. This is configuration recovery material, not a bootable whole-server snapshot or a package downgrade guarantee.

Nginx, Docker/containerd and their two application launchers were restarted to load updated host libraries; cron, acpid and console gettys were also restarted. Headscale did not need a restart. Verification after maintenance confirmed:

- Fresh key login works and the SSH wire protocol offers only `publickey`.
- All three tracked configuration templates match the deployed files by SHA-256.
- SSH, Headscale, Headplane, Casdoor, Nginx, Komari, Docker and containerd are active, with no failed systemd units.
- Public trusted HTTPS health, Headscale control-route rejection, DERP upgrade/server-key frame and STUN binding succeed.
- Headplane redirects anonymous requests through its existing OIDC login; Casdoor's public login and discovery endpoints respond normally. No login with the real owner's enrolled authenticator was performed for this OS maintenance check.
- All three devices remain online. Node IDs, machine/node/discovery keys, addresses, names and user mappings match the pre-maintenance record. Headscale configuration and server identity/DERP keys are unchanged.
- Application backends and metrics remain bound to loopback. Certificate renewal, application backup and API-key rotation timers remain active; both certificate renewal services last reported success.
- Post-maintenance snapshot `/var/backups/headscale/20261113T095532555613Z` has 43 verified manifest hashes and successful integrity checks for all three SQLite databases.

The blog's local HTTPS virtual host still returns HTTP 200. Public domain availability has a separate existing filing/cloud-blocking investigation and is not established by that local check.

## Reboot completed and recovery

The initial package maintenance retained the running `6.12.107+deb13-amd64` kernel and left a reboot pending for the installed `6.12.116+deb13-amd64` kernel and old DHCP/networking, D-Bus and logind library mappings. The previous kernel was retained.

The operator subsequently requested the reboot, issued at **2026-11-13 19:53 CST (11:53 UTC)**. A changed boot ID and `uname -r` confirmed that `6.12.116+deb13-amd64` is now running. Systemd reached `running`, all eight services listed above and all six maintenance timers were active, and there were no failed units or processes retaining deleted system libraries. All three SQLite databases passed read-only `PRAGMA quick_check`.

A fresh private-key SSH connection succeeded on port `23546`; an external authentication probe still advertised only `publickey`. Public HTTPS health, control-route rejection, DERP upgrade/server-key frame and STUN binding passed again. Headplane's anonymous OIDC redirects, Casdoor login and provider discovery also passed. The Windows and Mac clients were online at verification; the phone was not online at that check, and its status immediately before reboot had not been recorded. The private host verification receipt is `verification-after-reboot.json` in the maintenance snapshot directory. Automatic reboot remains disabled.

For SSH-only recovery, use an already authenticated session or Tencent's console and the private `rollback-ssh.py` in the maintenance snapshot after reviewing its scope. It restores only the pre-change drop-in state and validates/reloads SSH. It does not alter the port, authorized keys, application databases or packages. Do not enable password login merely to apply unrelated updates.

Use configuration backups selectively. Do not restore old application databases over live device/account changes to undo an OS configuration change. Package or boot failures may require Tencent console recovery or a separate whole-host snapshot; the configuration archive alone is insufficient for a complete system rollback.

For future approved reboots, reconnect using the same private key on port `23546`, check `uname -r`, service and timer state, then repeat the public protocol verifier:

```sh
python3 deployment/tencent/ops/tencent-headscale-verify.py --remote --server-name 140.143.127.180
```

Run that verifier from the repository on another machine for a public-path check. Keep credentials, private keys, runtime databases, environment files and backup archives outside Git; this repository records only nonsecret configuration templates and maintenance procedure/results.
