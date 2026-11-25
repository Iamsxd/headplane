# Tencent deployment records

These scripts and templates were recovered from the existing deployment on 2026-11-13. They are tracked here for review and future maintenance; copying them into Git did not deploy a change.

`ops/` preserves the installer, key rotation, backup, public dashboard checks, and Headscale/DERP checks. `templates/` contains configuration with secret **paths**, never secret values. Authentication has since migrated to native OIDC with official Casdoor and optional TOTP; see [the current authentication deployment](CASDOOR.md). Public Tailscale DERP regions have been removed; see [private relay selection and adding a backup](DERP.md).

The host now accepts SSH keys only and installs Debian security updates automatically, with automatic reboot disabled. See the [host maintenance record and recovery guidance](MAINTENANCE.md).

Headscale, Headplane and Casdoor now use `hs.lovecanl.cn`. The original IP still accepts existing Tailscale clients. See the [domain cutover and rollback record](DOMAIN.md).

The scripts retain their original server paths and historical staging directories. Do not rerun historical installers or cutover scripts against production. Future releases need their own staging directory and rollback point. Public verifiers read the operator's private login file without printing its contents; they must be adapted when the authentication scheme changes.

The working copies previously used outside this repository remain in the server workspace. For future changes, edit these tracked copies and deploy reviewed revisions, rather than allowing separate copies to diverge.

Never commit `/etc/headplane`, `/etc/headscale`, passwords, API keys, cookie secrets, private keys, database files, environment files, or backup archives. Private server backups remain the recovery mechanism for configuration and data; Git records source and deployment logic.
