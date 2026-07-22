---
bug_id: '002'
date: '2026-07-09'
title: 'apseudo-review completeness checks hard-code stale docs/usage and docs/roadmap paths'
services: [review]
status: open
---

## Cause

`src/apseudo_lint/review.py`'s completeness-check table (`_check_file` calls around lines 110, 113, 114) still hard-codes paths from before an earlier, unrelated documentation reorg moved these files under `docs/apseudo-docs/`:

```python
_check_file(actual_root, "Agent wording", "docs/usage/AGENT-INSTRUCTIONS-WORDING.md"),
_check_file(actual_root, "Runner usage", "docs/usage/RUNNER-USAGE.md"),
_check_file(actual_root, "Future versions", "docs/roadmap/FUTURE-VERSIONS.md"),
```

Real locations:

- `docs/usage/AGENT-INSTRUCTIONS-WORDING.md` → `docs/apseudo-docs/usage/AGENT-INSTRUCTIONS-WORDING.md`
- `docs/usage/RUNNER-USAGE.md` → `docs/apseudo-docs/usage/RUNNER-USAGE.md`
- `docs/roadmap/FUTURE-VERSIONS.md` → no file found anywhere in the repo under any `roadmap` directory as of 2026-07-09 — either it was never created, or it was deleted/renamed without updating this check. Needs investigation, not just a path fix.

Confirmed pre-existing (not introduced by the 2026-07-09 standards-adoption work): reproduced identically via a temporary `git worktree` at the pre-adoption commit during that session's final review, byte-for-byte same 3 `MISSING` rows.

This is one of two reasons `uv run apseudo-review .` currently exits 1 on `main` — see bug 003 for the other (unrelated) reason.

## Fix

Not yet applied.

1. Update the two `docs/usage/...` paths to their real `docs/apseudo-docs/usage/...` locations.
2. Investigate whether `docs/roadmap/FUTURE-VERSIONS.md` should exist (check git history / the "Future versions" area's intended content) before deciding whether to create it or remove the check.

## Lesson

`review.py`'s own completeness-check paths are a third, non-obvious consumer of doc paths (alongside plain Markdown links and `mcp.py`'s resource map — see bug 001) that a documentation reorg must also update. None of the tasks in the 2026-07-09 standards-adoption plan touched this file's `docs/usage/` or `docs/roadmap/` entries because they predate that session's `docs/specs/` relocation and were out of its declared scope — but the pattern (grep for literal old paths repo-wide, not just the paths a task's brief names) is the same lesson as bug 001.
