---
bug_id: '001'
date: '2026-07-09'
title: 'MCP resource map references docs/*.md paths that never existed'
services: [mcp]
status: open
---

## Cause

`src/apseudo_lint/mcp.py`'s `_read_resource`'s `resource_map` (around line 251)
hard-codes four resource URIs against paths directly under `docs/` that have
never existed in this repo's history:

```python
resource_map = {
    "apseudo://standard": self.root / "docs" / "PYTHONIC_PSEUDOCODE_STANDARD.md",
    "apseudo://rules": self.root / "docs" / "reference" / "RULES.md",  # fixed 2026-07-09
    "apseudo://agent-instructions": self.root / "docs" / "AGENT-INSTRUCTIONS-WORDING.md",
    "apseudo://feature-gap-analysis": self.root / "docs" / "FEATURE-GAP-ANALYSIS.md",
    "apseudo://traceability-review": self.root / "docs" / "PROJECT-TRACEABILITY-REVIEW.md",
}
```

The real files live under subdirectories:

- `apseudo://standard` → real file is `docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md`
- `apseudo://agent-instructions` → real file is `docs/apseudo-docs/usage/AGENT-INSTRUCTIONS-WORDING.md`
- `apseudo://feature-gap-analysis` → real file is `docs/reviews/FEATURE-GAP-ANALYSIS.md`
- `apseudo://traceability-review` → real file is `docs/reviews/PROJECT-TRACEABILITY-REVIEW.md`

`apseudo://rules` had the identical bug (pointed at `docs/RULES.md`) and was
fixed on 2026-07-09 as part of the `docs/specs/` → `docs/reference/`
relocation (see `docs/adr/adr-0001-relocate-language-reference-docs.md`) —
the other four entries were out of scope for that task and left as-is.

Found during a 2026-07-09 standards-adoption session's final whole-branch
review; confirmed via direct inspection, not by exercising the MCP server at
runtime.

## Fix

Not yet applied. `_read_resource` currently degrades gracefully — a missing
path returns a "not found" string rather than raising, so this is silent
data loss (four resources always report as absent), not a crash. Fix by
repointing each entry to its real path, matching the pattern used for
`apseudo://rules`.

## Lesson

When relocating or reorganizing `docs/`, grep for the literal path strings
across the whole repo (`grep -rn "docs/PYTHONIC_PSEUDOCODE_STANDARD.md"` etc.),
not just the files a specific task's brief names — `mcp.py`'s resource map
is a second, easy-to-miss consumer of these paths beyond the doc links and
`review.py` checks that are more commonly remembered.
