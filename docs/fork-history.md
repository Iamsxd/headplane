# Fork history and recovered releases

Repository: https://github.com/Iamsxd/headplane

Upstream: https://github.com/tale/headplane

Development branch: `lovecanl-0.8.2`. The fork's `main` branch initially mirrors upstream; custom changes live on the development branch.

## Provenance

The previous Chinese and bilingual deployments were built from source archives. They had release notes, test logs, image IDs, and rollback backups, but no local Git history and no fork. On 2026-11-13 the operator requested Git management. The recovered commits are dated when recovery took place, not backdated to imply a history that did not exist.

Official annotated tag `v0.8.2` has tag object `6f0764ef0c8cda997f94baa8e01b59ce6847d346`, pointing to commit `05e3ee33f6d3b347013654c69186791347be8bd9`. The former archive directory's `6f0764e` suffix came from the tag object. The retained English `app/` reference matches the official commit after line-ending normalization.

1. `74867d4` — recovered Simplified Chinese source snapshot. `app/`, `tests/`, and `CHANGELOG.md` came from the retained `/opt/headplane-zh-source` build tree. The preserved build's `build/server/index.js` SHA256 equals the earlier Chinese image build context: `c549da1e4f3c807af0c83b54fec1b674f70d5506bf39a657b2f67cc6bd4ab50b`.
2. `831b626` — recovered bilingual source, shared backend initialization, language routing/cookies, safe return paths, responsive header, and regression tests.
3. Subsequent maintenance commit — tracked build/deployment/verification scripts, source provenance, documentation, and exclusions for runtime credentials and data.

## Deployed artifacts and evidence

Chinese image: `sha256:0cbb92e64044823687842054354bca13922ecc997a413188baaf14382dcd1981`.

Bilingual image currently in production: `sha256:9ce135fc8b7c06f2c8a930d106639cd00adf44efe8bcf1ac81fdcab339774397`.

Pinned official runtime base: `ghcr.io/tale/headplane@sha256:b053a0a6699d0a67be3f0d9bae8e7dbe35ed67ae8448412adcbad7ea49866faa`.

The existing bilingual verification records report typecheck, lint, unit suites (23 files / 294 tests per language), production builds, public HTTPS checks, browser switching, and mobile layout checks. Git recovery is source management only; it does not claim those builds were originally made from these new commit IDs. The new tracked application source is checked against the pre-Git source snapshot, and the live deployed build tree is compared separately before pushing.

Private recovery archives and full operator release evidence remain outside this public repository. The build scripts retain their documented historical paths. See the repository README for the current build procedure and `deployment/tencent/README.md` for deployment caveats.

## Future work

Create focused commits for each change. Record verification with the revision and resulting image ID for each future deployment. Keep the upstream remote to review and merge future official updates. Authentication/MFA work must use its own branch or focused commits and must not be described as deployed until verified.
