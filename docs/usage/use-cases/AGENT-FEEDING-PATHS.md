# How Pseudocode Is Fed to Agents

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## Overview

Agent Pseudocode reaches Claude Code or Codex CLI through several channels. The right channel depends on whether the pseudocode is a reusable repo artifact, a one-off prompt, or an executable runner script.

```text
Pseudocode source
    ↓
repo context, prompt, runner, hooks, skills, or MCP
    ↓
Claude Code / Codex CLI
    ↓
agent action
    ↓
validation, run record, CI, or final outcome
```

## Path 1: Direct prompt

Use this for one-off work.

Prompt example:

````markdown
Follow this process exactly:

```apseudo
process repair_markdown_links(paths, max_rounds=3):
    round = 1

    while round <= max_rounds:
        result = run_command("uv run markdown-link-check {paths}")

        if result.passed:
            return Accepted(reason="links valid")

        elif result.failures:
            fix_link_failures(result.failures)
            round += 1
            continue

        else:
            return Blocked(reason="link checker returned ambiguous output")

    return Blocked(reason="round cap reached")
```
````

The agent receives the pseudocode because it is included directly in the task prompt.

Best for:

- quick one-time instructions;
- testing a new process before committing it;
- small branch-heavy instructions.

Weakness:

- no persistent repo artifact;
- no automatic CI coverage unless saved into the repo.

## Path 2: Repository files

Use this for durable standards and reusable workflows.

Example layout:

```text
repo/
├── AGENTS.md
├── CLAUDE.md
├── standards/
│   └── processes/
│       ├── review-loop.apseudo
│       ├── release-gate.apseudo
│       └── upstream-bug-report.apseudo
```

Prompt example:

```text
Implement the upstream bug workflow. Follow standards/processes/upstream-bug-report.apseudo as the control-flow source of truth.
```

The agent receives the pseudocode by reading the referenced file from the repository.

Best for:

- reusable workflow definitions;
- standards that should be versioned;
- agent processes that need review and CI.

## Path 3: `AGENTS.md` and `CLAUDE.md`

These files tell agents what `.apseudo` means in the repo.

Example wording:

```markdown
Files ending in `.apseudo` and Markdown fenced blocks labeled `apseudo` or `agent-pseudocode` are normative process instructions. Treat them as the control-flow source of truth when referenced by a task.
```

The agent receives the rule through its normal project-instruction discovery.

Best for:

- making the convention repository-wide;
- avoiding repeated explanations in prompts;
- ensuring Claude and Codex receive the same policy.

## Path 4: Executable runner scripts

Use this when the pseudocode should behave like a command-line task launcher.

Command:

```bash
uv run apseudo-run --codex --apply docs/examples/runner/fix-ruff.apseudo -- target=src
```

Runner flow:

```text
apseudo-run
    ↓ parse script/frontmatter
    ↓ validate body
    ↓ resolve args/provider/mode/workspace
    ↓ render strict prompt
    ↓ launch codex exec or claude -p
    ↓ capture structured outcome and run records
```

The agent receives the pseudocode through a generated prompt. Use `--render-prompt` to see the exact prompt before running:

```bash
uv run apseudo-run --codex --render-prompt docs/examples/runner/fix-ruff.apseudo -- target=src
```

Best for:

- repeatable command-line workflows;
- CI-like or unattended agent tasks;
- tasks that need run records, logs, post-checks, and output files.

## Path 5: Script registry

Use this when you want named tasks instead of paths.

Registry:

```toml
[scripts.fix-ruff]
path = "docs/examples/runner/fix-ruff.apseudo"
description = "Fix Ruff failures in a bounded, verified loop."
default_agent = "codex"
default_mode = "apply"
```

Command:

```bash
uv run apseudo run fix-ruff -- target=src
```

The unified CLI resolves the registry name to a script path and then uses the same runner path.

Best for:

- recurring tasks;
- reducing command length;
- making agent tasks discoverable.

## Path 6: Hooks

Hooks do not normally feed the pseudocode to the agent. They enforce that the pseudocode remains valid while the agent works.

Example:

```text
Claude/Codex edits docs/usage/use-cases/COMMON-WORKFLOWS.md
    ↓
Post-edit hook runs
    ↓
apseudo-lint detects a bad fenced apseudo block
    ↓
agent must fix or surface blocker
```

Hooks are enforcement, not task definition.

Best for:

- blocking invalid pseudocode edits;
- preventing bypass commands;
- ensuring final completion only happens after validation.

## Path 7: MCP server

The MCP server exposes helper tools to agents.

Typical agent uses:

```text
validate_file(path="standards/processes/release-gate.apseudo")
explain_rule(rule_id="APSEUDO-WHILE-001")
generate_template(template="review-loop")
review_project(path=".")
render_mermaid(path="standards/processes/review-loop.apseudo")
```

The agent receives the standard through tool calls and returned explanations.

Best for:

- agent self-service;
- rule explanations;
- template generation;
- project-wide review.

MCP is not a hard enforcement layer by itself. Use hooks and CI for that.

## Path 8: Skills

The repo ships skill documents for Claude and Codex-style agent use.

Locations:

```text
.claude/skills/agent-pseudocode/SKILL.md
.agents/skills/agent-pseudocode/SKILL.md
```

Skills give agents compact operational instructions for using the tools correctly.

Best for:

- reducing repeated prompt text;
- making the convention available to subagents;
- teaching agents the intended workflow.

## Path 9: Editor/LSP feedback before agent use

The language server and editor extensions help you author valid pseudocode before an agent sees it.

They provide:

- highlighting;
- diagnostics;
- completion;
- hover;
- formatting;
- symbols;
- code actions.

This path feeds the human author, not the agent directly. It improves the artifact that the agent later consumes.

## Recommended default path

For a repo you care about, use this stack:

```text
1. Write reusable workflows as .apseudo files.
2. Reference them from Markdown standards.
3. Tell agents about them in AGENTS.md and CLAUDE.md.
4. Enable hooks so agents cannot silently break them.
5. Enable pre-commit and CI for repository enforcement.
6. Use apseudo-run only for workflows you actually want to launch from the shell.
7. Use MCP/skills to make the standard easier for agents to follow.
```
