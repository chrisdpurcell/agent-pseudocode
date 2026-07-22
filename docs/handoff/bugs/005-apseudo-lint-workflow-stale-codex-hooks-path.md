---
bug_id: '005'
date: '2026-07-22'
title: 'apseudo-lint.yml validates the deleted .codex/hooks.json, failing CI since 2026-07-09'
services: [ci]
status: fixed
---

## Cause

The `Validate JSON/TOML configs` step of `.github/workflows/apseudo-lint.yml` hard-coded four config paths:

```bash
python -m json.tool .claude/settings.json >/dev/null
python -m json.tool .codex/hooks.json >/dev/null
python -m json.tool .mcp.json >/dev/null
# ...then tomllib on .codex/config.toml
```

`.codex/hooks.json` was deleted when Codex hook wiring moved into `.codex/config.toml`; the workflow was never updated. The step runs under `bash -e`, so it aborted with:

```text
FileNotFoundError: [Errno 2] No such file or directory: '.codex/hooks.json'
##[error]Process completed with exit code 1.
```

Because `-e` stops at the first failure, every later step (ruff, basedpyright, `pip-audit`) was silently skipped for the whole period.

The `Agent Pseudocode Validation` workflow has therefore been red on **every** commit since at least `e6cf3d5` (2026-07-09), including `21ade51`, `26446ad`, and the V4→V5 migration commit `5147139`. It was found only because the migration session inspected CI conclusions after pushing.

Confirmed pre-existing, not caused by the V5 migration: the migration commit touched neither `.codex/hooks.json` nor this workflow, and the two preceding commits fail identically.

## Fix

Applied 2026-07-22: removed the `.codex/hooks.json` line. `.codex/config.toml` is the current Codex hook authority and the same step already validates it with `tomllib`.

The remaining hard-coded paths were verified to exist and parse, and every step the `-e` abort had been masking was run locally and passes: `pip-audit`, `ruff`, `basedpyright`, the CLI smoke commands, and `apseudo-mermaid`.

The explicit path list was kept rather than globbed to all tracked JSON, because `.vscode/*.json` is JSONC and `python -m json.tool` rejects comments.

## Lesson

Third instance of the same class as bugs 001 and 002: a file move updated the obvious consumers but left a literal path behind in a non-obvious one. CI workflows are a path consumer too — grep the whole repository for the old literal path when relocating a file, `.github/` included.

Second, distinct lesson: a `run:` block under `bash -e` converts one stale path into a silent skip of every later gate. A green-to-red transition that nobody watches is indistinguishable from no CI at all — check the run conclusion after pushing, not just local checks.
