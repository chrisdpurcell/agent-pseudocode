---
schema_version: '1.1'
id: 'reference-xicitp-agent-skills'
title: 'Agent Skills'
description: 'Reference for the agent skills that package Pythonic Agent Pseudocode guidance.'
doc_type: 'reference'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'tooling-maintainers'
consumer: 'mix'
tags:
  - 'reference'
  - 'agent-workflow'
aliases:
  - 'APSEUDO skill'
  - 'agent-pseudocode skill'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Agent Skills

This repository includes skills for both Claude Code and Codex.

## Claude Code

Path:

```text
.claude/skills/agent-pseudocode/SKILL.md
```

Claude Code discovers project skills from `.claude/skills/`. Invoke it directly with `/agent-pseudocode` or rely on automatic use when the task matches the description.

## Codex

Path:

```text
.agents/skills/agent-pseudocode/SKILL.md
```

Codex discovers repository skills from `.agents/skills` between the current working directory and the repository root. Invoke it directly from `/skills` or with `$agent-pseudocode` where supported.

## Skill behavior

The skill tells the agent to:

- Use the standard document for convention changes.
- Start new workflows from templates where practical.
- Validate with `apseudo-format` and `apseudo-lint`.
- Use `apseudo-explain` for diagnostics.
- Avoid enforcement bypasses.

## Shared reference

Both skills include:

```text
references/quick-reference.md
```

That file contains a compact workflow template, approved outcomes, and diagnostic triage reminders.
