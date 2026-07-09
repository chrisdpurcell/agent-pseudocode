# Choosing the Right Surface

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## Decision summary

Use the lightest surface that gives enough control.

| Situation | Use | Why |
| --- | --- | --- |
| One-off instruction in a chat or agent prompt | Prompt-local fenced `apseudo` block | Fast and explicit; no repo artifact needed. |
| A standard needs one normative workflow | Markdown fenced `apseudo` block in the standard | Keeps the workflow beside the explanation. |
| A workflow is reused across docs or repos | Standalone `.apseudo` file | Stable reference target; easy to lint, diff, and reuse. |
| A workflow should be launched from the shell | Executable `.apseudo` runner script | Validates, renders, and sends the task to Claude/Codex. |
| A repo has several recurring agent tasks | `.apseudo/scripts.toml` registry plus `apseudo run <name>` | Gives task names and default provider/mode. |
| An agent needs callable support tools | MCP server | Lets agents validate, explain, template, and review pseudocode. |
| You are authoring or editing files | VS Code or Kate integration plus LSP | Syntax highlighting, diagnostics, completion, hover, formatting. |
| You need hard enforcement | pre-commit, CI, and agent hooks | Prevents drift and blocks invalid edits. |

## Use prose when the main issue is context

Use normal Markdown when the instruction is about intent, rationale, scope, background, or tradeoffs.

Good prose-only cases:

- project background;
- design rationale;
- architecture overview;
- human decision records;
- explanatory tutorials;
- style preferences with no branching.

Do not force these into pseudocode.

## Use fenced `apseudo` blocks inside Markdown when the process belongs to the document

Use fenced blocks when a standard needs a small embedded control-flow section.

Example:

````markdown
## Amendment loop

The amendment loop is bounded to prevent indefinite Claude/Codex disagreement.

```apseudo
process amend_plan(plan, reviewer, max_rounds=5):
    round = 1
    blockers = []

    while round <= max_rounds:
        review = reviewer.review(plan)

        if review.status == "approved":
            return Accepted(reason="plan approved")

        elif review.blockers:
            blockers = review.blockers
            plan = revise_using_blockers(plan, blockers)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous review result")

    return Blocked(reason="round cap reached", unresolved_blockers=blockers)
```
````

This is ideal when the workflow is specific to the surrounding document.

## Use standalone `.apseudo` when the workflow has a name

Create a standalone file when the process is reused or referenced by multiple documents.

Good examples:

```text
standards/processes/spec-review-loop.apseudo
standards/processes/release-gate.apseudo
standards/processes/upstream-bug-report.apseudo
standards/processes/handoff-size-control.apseudo
```

Then reference it from Markdown:

```markdown
The normative process is `standards/processes/release-gate.apseudo`.
Do not duplicate the release-gate logic in prose.
```

This keeps the workflow diff-friendly and makes it easier for hooks/CI to validate.

## Use executable `.apseudo` when the workflow should run from the command line

Use executable scripts when you want shell-like ergonomics:

```bash
uv run apseudo-run --codex --apply docs/examples/runner/fix-ruff.apseudo -- target=src
```

or:

```bash
chmod +x docs/examples/runner/fix-ruff.apseudo
docs/examples/runner/fix-ruff.apseudo --codex --apply -- target=src
```

Use this for bounded, repeatable, agentic tasks:

- fix Ruff or Pyright failures;
- review a spec;
- repair docs links;
- generate release notes;
- update a template repo from standards;
- triage issue evidence;
- perform a bounded refactor with post-checks.

Do not use executable `.apseudo` for destructive deterministic operations. If a task can be safely and fully specified as Python or Bash, write Python or Bash.

## Use a registry when there are multiple scripts

The registry lives at:

```text
.apseudo/scripts.toml
```

Example:

```toml
[scripts.fix-ruff]
path = "docs/examples/runner/fix-ruff.apseudo"
description = "Fix Ruff failures in a bounded, verified loop."
default_agent = "codex"
default_mode = "apply"

[scripts.review-spec]
path = "docs/examples/runner/review-spec.apseudo"
description = "Review a specification document with bounded agent behavior."
default_agent = "claude"
default_mode = "review"
```

Then run:

```bash
uv run apseudo run fix-ruff --codex --apply -- target=src
uv run apseudo run review-spec --claude --review -- spec_path=docs/spec.md
```

The registry is useful when you want a small set of known agent tasks that behave like `make` targets or `just` recipes.

## Use MCP when the agent needs tools, not just instructions

The MCP server is useful when the agent should be able to ask the system questions:

- validate this file;
- explain this rule ID;
- generate a starter template;
- render Mermaid from a process;
- review the project for pseudocode completeness.

MCP improves agent self-service. It is not a replacement for hooks, pre-commit, or CI.

## Use hooks when you need enforcement during agent work

Hooks are for automatic checks during Claude/Codex operation.

Common hook behavior:

```text
Agent edits Markdown or .apseudo
    ↓
Hook detects changed pseudocode-relevant files
    ↓
Hook runs apseudo-format --check and apseudo-lint
    ↓
Hook blocks or reports invalid changes
```

Hooks reduce reliance on the agent remembering to validate.

## Use CI when the repository must not accept invalid pseudocode

CI is the final guardrail. A local agent can misbehave, but the repository should not accept broken standards.

The intended order is:

```text
editor feedback → agent hook → pre-commit → CI required check
```

Each layer catches the same class of problem at a different time.
