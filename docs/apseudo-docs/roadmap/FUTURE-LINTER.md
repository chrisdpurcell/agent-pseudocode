---
schema_version: '1.1'
id: 'note-et386x-linter-status-apseudo-lint'
title: 'Linter Status: `apseudo-lint`'
description: 'Roadmap note for future apseudo-lint validation behavior.'
doc_type: 'note'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'agent-pseudocode-maintainers'
consumer: 'mix'
tags:
  - 'rules'
  - 'validator'
aliases:
  - 'apseudo-lint'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Linter Status: `apseudo-lint`

**Date:** 2026-07-08  
**Status:** Implemented prototype.

The future linter plan has been replaced by a working CLI package under `src/apseudo_lint`.

Use:

```bash
uv run apseudo-lint .
uv run apseudo-lint . --format json
uv run apseudo-lint . --strict
```

See `docs/apseudo-docs/enforcement/ENFORCEMENT.md` for the rule set, install steps, pre-commit integration, GitHub Actions workflow, and Claude/Codex hook behavior.
