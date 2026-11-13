# Headplane Language Switching Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement inline; one fresh read-only review before deployment.

**Goal:** Add remembered Chinese/English selection to the existing dashboard.

**Architecture:** Compile official English and existing Chinese route views, inject the same initialized backend context into each, dispatch each request by validated language Cookie, serve a collision-checked asset union. Full document navigation on switching keeps SSR, module constants and hydration consistent.

**Tech Stack:** Existing Node24.22.1, pnpm10.4.0, React Router, TypeScript, Vite, Vitest, pinned Docker base.

**Spec:** `docs/superpowers/specs/2026-11-13-headplane-language-design.md`.

## Constraints and review focus

- Keep one DB/context/auth/key/background service instance; English build must only export a listener factory.
- Preserve action/form/config/query/role values and all existing security limits.
- Language Cookie supports only zh-CN/en, is scoped to /admin and secure, does not affect other browsers.
- Reject unsafe redirects and invalid language; preserve valid relative page/filter state.
- Shared resources remain loadable across switches and concurrent clients; no mixed SSR/hydration state.

## Tasks

- [x] Add tests for cookie fallback/persistence/attributes, language validation, local return navigation, per-request dispatch isolation and POST behavior; observe feature-missing failures.
- [x] Implement `utils/language.ts`, `utils/ui-language.ts`, language POST route and language selector in header/login. Extract `server/request-listener.ts`, add factory-only English entry and route dispatch to existing main. Keep feature reasons language-neutral in shared context and translate at Chinese presentation points.
- [x] Create deterministic bilingual staging/build tool from exact official source and translated overlay, with shared integration patches, frozen dependencies, required typecheck/lint, unit suite and builds for both variants; collision-check asset union. Add changelog and maintenance docs.
- [x] Review final code, fix material findings, test isolated candidate across both languages, exact cookie/action/asset behavior and concurrent requests; inspect real UI switching/persistence/current path/dialog.
- [x] Backup, deploy immutable image with readiness/rollback, recheck public auth/languages/Headscale/DERP/STUN/device identity and backup. Remove temporary candidate/proxy/tunnel and record release evidence.

## Ledger

Ruling: use inline execution and existing isolated non-Git service directory; no new worktree is appropriate. Routine authorized deployment to this server is part of the task.


Task complete: both builds typecheck/lint/build passed; each unit suite 294/294. Candidate and public HTTP scenarios passed, browser switching/persistence/detail path/mobile layout verified. Private backups and immutable image recorded in artifacts/tencent-headscale/headplane-language-release-20261113.md.

Ruling: React Router document redirects also prepend basename, observed /admin/admin in candidate; return a safe internal path from the helper. Reviewer found normalization can create // after stripping prefix; added regression before fixing, then full suites and candidate/public POST passed. Global framework CSRF was not sufficient for this utility, so explicitly reject absent or mismatched Origin. Existing document user-form revalidation redirect also occurs on the old image; test the actual UI fetcher .data contract instead and leave unrelated original behavior unchanged.

Ruling: Headscale CLI JSON uses snake_case; fixed deployment identity extraction and independently compared pre-deployment/current SQLite identity columns for all 3 nodes. No data rollback or changes were performed.
