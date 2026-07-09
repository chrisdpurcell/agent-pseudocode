---
schema_version: '1.1'
id: 'runbook-t79u50-agent-pseudocode-tasks'
title: 'Agent Pseudocode Tasks'
description: 'Task catalog for agents working with Pythonic Agent Pseudocode artifacts.'
doc_type: 'runbook'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'user'
tags:
  - 'runbook'
  - 'usage'
aliases: []
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Agent Pseudocode Tasks

Generated from `.apseudo/scripts.toml`.

## `fix-ruff`

Fix Ruff failures in a bounded, verified loop.

```bash
apseudo run --codex fix-ruff --
```

Arguments:

- `target`

## `review-spec`

Review a specification document with bounded agent behavior.

```bash
apseudo run --codex review-spec --
```
