# Agent Pseudocode Use-Case Guide

Date: 2026-07-09 Applies to: Agent Pseudocode Toolkit `0.6.1`

This folder explains how to use Agent Pseudocode as a practical agent-instruction system. The focus is not only the language syntax, but how the files, runner, hooks, language server, MCP server, skills, and editor integrations work together.

## Start here

| Need | Document |
| --- | --- |
| Understand the mental model | [`MENTAL-MODEL.md`](MENTAL-MODEL.md) |
| Decide whether to use prose, Markdown fences, `.apseudo`, or executable scripts | [`CHOOSING-A-SURFACE.md`](CHOOSING-A-SURFACE.md) |
| Understand how pseudocode is fed to Claude Code or Codex CLI | [`AGENT-FEEDING-PATHS.md`](AGENT-FEEDING-PATHS.md) |
| See task-oriented examples | [`COMMON-WORKFLOWS.md`](COMMON-WORKFLOWS.md) |
| Use executable/shebang runner scripts | [`RUNNER-WORKFLOWS.md`](RUNNER-WORKFLOWS.md) |
| Adopt this in a real repo | [`REPOSITORY-OPERATING-MODEL.md`](REPOSITORY-OPERATING-MODEL.md) |
| Copy common patterns | [`EXAMPLE-CATALOG.md`](EXAMPLE-CATALOG.md) |

## Short version

Agent Pseudocode is best used as a **bounded process contract** for an AI agent.

Use it when normal prose is too easy for an agent to misread:

- repeated review/revision loops;
- explicit stop conditions;
- `if / elif / else` branch logic;
- retry caps;
- release gates;
- handoff-size limits;
- verification requirements;
- upstream bug tracking;
- template or standards synchronization;
- any workflow where “keep trying until it works” would be dangerous.

The `.apseudo` file itself is not executed like Python. It is validated, formatted, and then either:

1. read by an agent as repository context;
2. embedded in Markdown as a normative fenced block;
3. launched through `apseudo-run`, which turns it into a strict headless Claude/Codex prompt;
4. exposed through MCP and skills so agents can validate, explain, and repair it.

## Where this fits with the rest of the docs

This folder is usage-oriented. It complements the normative and reference docs:

| Topic | Reference |
| --- | --- |
| Language rules | [`docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md`](../../../reference/PYTHONIC_PSEUDOCODE_STANDARD.md) |
| Executable script semantics | [`docs/reference/EXECUTABLE-PSEUDOCODE-SPEC.md`](../../../reference/EXECUTABLE-PSEUDOCODE-SPEC.md) |
| CLI reference | [`../usage.md`](../usage.md) |
| Runner command reference | [`../RUNNER-USAGE.md`](../RUNNER-USAGE.md) |
| Enforcement | [`docs/apseudo-docs/enforcement/ENFORCEMENT.md`](../../enforcement/ENFORCEMENT.md) |
| Hooks | [`docs/apseudo-docs/features/HOOKS.md`](../../features/HOOKS.md) |
| MCP | [`docs/apseudo-docs/features/MCP.md`](../../features/MCP.md) |
| Skills | [`docs/apseudo-docs/features/SKILLS.md`](../../features/SKILLS.md) |
| VS Code | [`../VSCODE.md`](../VSCODE.md) |
| Kate | [`../KATE.md`](../KATE.md) |
