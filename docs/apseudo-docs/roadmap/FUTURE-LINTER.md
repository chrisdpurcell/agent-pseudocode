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

See `docs/enforcement/ENFORCEMENT.md` for the rule set, install steps, pre-commit integration, GitHub Actions workflow, and Claude/Codex hook behavior.
