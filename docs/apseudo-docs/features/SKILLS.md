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
