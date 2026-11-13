# Headplane Simplified Chinese display

**Goal:** Deliver Chinese navigation, administrative pages, dialogs, validation and status messages on the current Headplane0.8.2 installation.

**Approach:** Translate UI source from the official0.8.2 release and rebuild the React Router application against its frozen dependency lock. Derive a local image from the already pinned official runtime, replacing only built application assets. No browser translation services or DOM text rewriting. Keep all form/query/config keys, role values, commands, user-entered names, IPs and policy/code examples unchanged. Default document language becomes zh-CN. Preserve account credentials and persistent data. Retain the original image and private rollback configuration.

**Work:** Common components/layout/auth/SSH copy owned by root; independent machine and settings/users/DNS/ACL translations delegated per dispatching-parallel-agents skill. Repository AGENTS.md requires typecheck, lint and a # Next changelog entry; add localized-release documentation centrally.

- [x] Translate source UI and time/status labels, inspect changes for program token preservation.
- [x] Typecheck, lint and build with Node24.22.1/pnpm10.4.0/frozen lock; inherit official runtime and unused WASM support.
- [x] Start isolated candidate on a loopback port with copied dashboard data; verify Chinese pages, actions' submitted values, assets and authentication.
- [x] Back up data/config, switch image with readiness/rollback, inspect actual browser UI and dialogs.
- [x] Recheck existing device identities, control/DERP/STUN, key rotation compatibility and backup; record image ID/rollback and translation maintenance instructions.

Ruling: explicit request specifies Chinese display on the existing app, so proceed with Simplified Chinese defaults and preserve existing behavior without another design approval. No generic mirror tests for copy-only changes; use structural source review, required compiler/lint checks and actual UI/functional verification.

Completed 2026-11-13. Release evidence: `artifacts/tencent-headscale/headplane-zh-release-20261113.md`. Maintenance and rollback: `services/headplane-zh/README.md`. External diagnostics may remain English.
