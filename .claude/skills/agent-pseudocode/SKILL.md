---
name: agent-pseudocode
description: Use when creating, editing, reviewing, explaining, formatting, or validating Pythonic Agent Pseudocode, APSEUDO-* rules, bounded loops, agent workflow standards, or Markdown apseudo fences.
allowed-tools: Bash(./scripts/apseudo-* *) Bash(scripts/apseudo-* *) Read Grep Glob Edit Write MultiEdit
---

# Agent Pseudocode Skill

Use this skill for any task involving Pythonic Agent Pseudocode, `.apseudo` files, `.agentpseudo` files, `.pseudocode` files, or Markdown fenced blocks tagged `apseudo`, `agent-pseudocode`, `agent_pseudocode`, `pythonic-pseudocode`, or `pseudocode-pythonic`.

## Required workflow

1. Read `docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md` when the task changes the convention itself.
2. For new workflow blocks, start from `scripts/apseudo-template --list` and `scripts/apseudo-template <name>` unless a custom structure is clearly required.
3. Use bounded `while` loops, explicit `else` fallbacks, and approved terminal outcomes.
4. Run `scripts/apseudo-format --check --changed` and `scripts/apseudo-lint --changed` before completion.
5. When a diagnostic appears, run `scripts/apseudo-explain <APSEUDO-CODE>` instead of guessing.
6. Do not use `--no-verify`, disable hooks, edit enforcement config, or suppress a rule unless the user explicitly asks to change the standard and the final response calls out the change.

## Hard constraints

- Do not declare pseudocode work complete while `apseudo-lint` has blocking diagnostics.
- Do not silently replace deterministic validation with narrative review.
- Do not treat Mermaid output as source of truth; pseudocode remains the source of truth.
- Prefer `process name(...):` declarations for full workflows.
- Prefer guard clauses over deep nesting.

## Useful commands

```bash
scripts/apseudo-template --list
scripts/apseudo-format --check --changed
scripts/apseudo-lint --changed
scripts/apseudo-explain APSEUDO-WHILE-001
scripts/apseudo-mermaid path/to/file.apseudo
scripts/apseudo-review .
```

## References

Load `references/quick-reference.md` for a compact rule map and copy/paste examples.
