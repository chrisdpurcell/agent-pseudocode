---
bug_id: '003'
date: '2026-07-09'
title: 'pre-migration ChatGPT transcript trips real APSEUDO lint errors on illustrative fences'
services: [lint]
status: open
---

## Cause

`docs/reference/pre-migration/apseudo-chatgpt-conversation.md` (relocated
from `docs/reference/pre-migration/` — path unchanged by the 2026-07-09
`docs/specs/` → `docs/reference/` relocation, only its siblings moved) is a
verbatim historical ChatGPT conversation log. It contains several
`agent-pseudocode`/`apseudo` fenced code blocks that were illustrative
snippets in that conversation, not authored, structurally-complete
pseudocode. `apseudo-lint`/`apseudo-review` scans every `apseudo`-fenced
block in every tracked Markdown file, so these illustrative fences trip real
diagnostics:

- `APSEUDO-RETURN-001` (ERROR): process has no terminal return outcome — lines 816, 825, 2585
- `APSEUDO-BRANCH-002` / `APSEUDO-RETURN-003` (WARNING): placeholder body / missing terminal statement — same fence locations
- `APSEUDO-BRANCH-001` (WARNING): if/elif chain has no explicit else — line 1870

This is one of two reasons `uv run apseudo-review .` currently exits 1 on
`main` — see bug 002 for the other (unrelated) reason. Confirmed pre-existing
via the same temporary-worktree A/B test as bug 002, during the 2026-07-09
standards-adoption session's Task 6 and final review.

## Fix

Not yet applied. Rewriting the transcript's fenced snippets to satisfy the
linter would misrepresent the historical conversation they're quoting — the
correct fix is almost certainly a linter-level exclusion (e.g. an
`ignore_codes` entry scoped to this one file in `pyproject.toml`'s
`[tool.apseudo_lint]`, or excluding
`docs/reference/pre-migration/**` from the Markdown-fence scan entirely,
since it's explicitly historical/reference material, not authored examples)
rather than editing the file's content.

## Lesson

A repo's own linter scanning "every markdown file with the right fence
language" will happily lint fences inside a verbatim historical transcript
as if they were live examples. When relocating or auditing docs that quote
external conversations verbatim, check whether they carry the project's own
fence language and, if so, whether they need an explicit lint-scope
exclusion — don't assume "it's just docs" means it's exempt.
