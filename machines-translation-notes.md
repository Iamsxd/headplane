# Machine route translation notes

- Translated 13 route, component, and dialog files under `app/routes/machines/` into Simplified Chinese. The filter hook has no display copy and was left unchanged.
- Preserved all action IDs, filter values, form/query keys, route paths, property names, command snippets, example keys, device names, tags, addresses, product names, and protocol acronyms.
- Preserved interpolation expression order, control flow, and component structure. Singular/plural tag warning branches now use natural Chinese phrases.
- Dynamic error text returned by the Headscale API is passed through unchanged by `extractApiErrorMessage`; it may still be English. The local fallback is translated.
- Shared tag badges, status indicators, generic dialog buttons, host-info fallback text, and relative time formatting are outside this subtask's file ownership and need central localization.
- `toggle_expiry` originally returned the same “Machine expired” message as `expire`. Both occurrences were translated literally; the pre-existing message mismatch was not changed as part of localization.
- `AGENTS.md` requests a user-facing `CHANGELOG.md` entry under `# Next`; this needs to be added centrally because the changelog is outside this subtask's ownership.
- Build/typecheck and deployment are delegated to the root task as instructed; no packages or tests were added.
