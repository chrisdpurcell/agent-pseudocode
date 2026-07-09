---
bug_id: '003'
date: '2026-07-09'
title: 'pre-migration ChatGPT transcript trips real APSEUDO lint errors on illustrative fences'
services: [lint]
status: fixed
---

## Cause

`docs/reference/pre-migration/apseudo-chatgpt-conversation.md` (relocated from `docs/reference/pre-migration/` — path unchanged by the 2026-07-09 `docs/specs/` → `docs/reference/` relocation, only its siblings moved) is a verbatim historical ChatGPT conversation log. It contains several `agent-pseudocode`/`apseudo` fenced code blocks that were illustrative snippets in that conversation, not authored, structurally-complete pseudocode. `apseudo-lint`/`apseudo-review` scans every `apseudo`-fenced block in every tracked Markdown file, so these illustrative fences trip real diagnostics:

- `APSEUDO-RETURN-001` (ERROR): process has no terminal return outcome — lines 816, 825, 2585
- `APSEUDO-BRANCH-002` / `APSEUDO-RETURN-003` (WARNING): placeholder body / missing terminal statement — same fence locations
- `APSEUDO-BRANCH-001` (WARNING): if/elif chain has no explicit else — line 1870

This is one of two reasons `uv run apseudo-review .` currently exits 1 on `main` — see bug 002 for the other (unrelated) reason. Confirmed pre-existing via the same temporary-worktree A/B test as bug 002, during the 2026-07-09 standards-adoption session's Task 6 and final review.

## Fix

Fixed 2026-07-09 by adding `docs/reference/pre-migration` to the `apseudo_lint.exclude` list in both `.apseudo-lint.toml` and `pyproject.toml`. This keeps the verbatim historical transcript in the durable reference corpus while preventing its quoted illustrative fences from being treated as live authored pseudocode examples.

## Lesson

A repo's own linter scanning "every markdown file with the right fence language" will happily lint fences inside a verbatim historical transcript as if they were live examples. When relocating or auditing docs that quote external conversations verbatim, check whether they carry the project's own fence language and, if so, whether they need an explicit lint-scope exclusion — don't assume "it's just docs" means it's exempt.
