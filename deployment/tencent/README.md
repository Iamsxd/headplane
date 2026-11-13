# Tencent deployment records

These scripts and templates were recovered from the existing deployment on 2026-11-13. They are tracked here for review and future maintenance; copying them into Git did not deploy a change.

`ops/` preserves the installer, key rotation, backup, public dashboard checks, and Headscale/DERP checks. `templates/` contains configuration with secret **paths**, never secret values. Current authentication is still Nginx Basic authentication with trusted proxy headers; the proposed OIDC/TOTP migration is a separate change.

The scripts retain their original server paths and historical staging directories. Do not rerun historical installers or cutover scripts against production. Future releases need their own staging directory and rollback point. Public verifiers read the operator's private login file without printing its contents; they must be adapted when the authentication scheme changes.

The working copies previously used outside this repository remain in the server workspace. For future changes, edit these tracked copies and deploy reviewed revisions, rather than allowing separate copies to diverge.

Never commit `/etc/headplane`, `/etc/headscale`, passwords, API keys, cookie secrets, private keys, database files, environment files, or backup archives. Private server backups remain the recovery mechanism for configuration and data; Git records source and deployment logic.
