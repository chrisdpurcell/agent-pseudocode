---
schema_version: '1.1'
id: 'runbook-vvyp1a-enforcement-guide'
title: 'Enforcement Guide'
description: 'Reference for repository enforcement layers that protect Pythonic Agent Pseudocode files.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'mix'
tags:
  - 'runbook'
  - 'enforcement'
  - 'agent-workflow'
aliases:
  - 'pre-commit hooks'
  - 'CI gate'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Enforcement Guide

## Enforcement architecture

```text
Pythonic pseudocode standard
        ↓
apseudo-lint and apseudo-format
        ↓
├─ pre-commit hooks
├─ GitHub Actions CI
├─ Claude Code hooks
├─ Codex hooks
├─ VS Code/Kate LSP diagnostics
└─ MCP tools for agents
```

The CLI validator and formatter are the source of truth. Other integrations call or wrap them.

## Local commands

```bash
scripts/apseudo-format --check --changed
scripts/apseudo-lint --changed
scripts/apseudo-review .
```

## pre-commit

Configured files:

```text
.pre-commit-config.yaml
.pre-commit-hooks.yaml
```

Install:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

## CI

Configured workflow:

```text
.github/workflows/apseudo-lint.yml
```

Set **Validate pseudocode standard** as a required check in branch protection.

## Agent hooks

See `docs/apseudo-docs/features/HOOKS.md` for Claude/Codex hook details.

## MCP

See `docs/apseudo-docs/features/MCP.md` for agent-facing MCP tools.

## Failure handling

When validation fails, the correct response is one of:

1. Fix the pseudocode.
2. Explain the APSEUDO-\* diagnostic and why the source is blocked.
3. Propose a standard change with rationale.

Do not bypass hooks, pre-commit, or CI.
