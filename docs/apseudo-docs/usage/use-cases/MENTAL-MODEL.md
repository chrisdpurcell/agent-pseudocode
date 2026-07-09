---
schema_version: '1.1'
id: 'concept-9ab8lr-mental-model-what-agent-pseudocode-is-for'
title: 'Mental Model: What Agent Pseudocode Is For'
description: 'Conceptual model for understanding what Pythonic Agent Pseudocode is for.'
doc_type: 'concept'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'language-maintainers'
consumer: 'user'
tags:
  - 'concept'
  - 'usage'
  - 'agent-workflow'
aliases:
  - 'APSEUDO mental model'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Mental Model: What Agent Pseudocode Is For

Date: 2026-07-09  
Applies to: Agent Pseudocode Toolkit `0.6.1`

## Core idea

Agent Pseudocode is a **control-flow source of truth** for AI-agent behavior.

It is not Python. It is not Bash. It is not Mermaid. It is a Python-shaped process language that says:

> When this condition happens, take this action; when this guard fails, stop; when this loop reaches its cap, surface blockers instead of guessing.

The best use is not replacing all documentation. The best use is replacing vague procedural prose with a bounded, checkable process.

## What problem it solves

Longform instructions often hide the important rules inside paragraphs:

> Review the document and make improvements. If the reviewer has blockers, fix them and try again. Do not keep going forever. If things still fail, explain what happened.

That sounds clear to a human, but it leaves too much room for an agent to improvise.

Agent Pseudocode makes the same workflow explicit:

```apseudo
process amend_document(document, reviewer, max_rounds=5):
    round = 1
    blockers = []

    while round <= max_rounds:
        review = reviewer.review(document)

        if review.status == "approved":
            commit_final_document(document)
            return Accepted(reason="approved")

        elif review.status == "rejected" and review.blockers:
            blockers = review.blockers
            document = revise_using_blockers(document, blockers)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous review result")

    return Blocked(reason="round cap reached", unresolved_blockers=blockers)
```

The pseudocode makes these requirements visible:

- the loop is bounded;
- the success outcome is explicit;
- rejected reviews carry blockers forward;
- ambiguous review output is not silently accepted;
- the round cap has a terminal outcome.

## What it is not

Agent Pseudocode is not a substitute for deterministic scripts.

Use Bash or Python for operations that should not require model judgment:

- copying files;
- rotating logs;
- backing up data;
- deleting generated output;
- running a known command sequence;
- production deployment;
- secret handling.

Use Agent Pseudocode when the task needs agent judgment but still needs hard boundaries.

## The three layers

Think of the system as three layers.

| Layer | Purpose | Examples |
| --- | --- | --- |
| Language | Define the process | `process`, `if`, `while`, `return Accepted(...)` |
| Tooling | Keep the process valid | `apseudo-lint`, `apseudo-format`, LSP diagnostics |
| Runtime | Feed the process to agents | `apseudo-run`, hooks, MCP, skills, repo instructions |

The language tells the agent what to do. The tooling keeps the instruction artifact healthy. The runtime decides how the agent receives and executes the instruction.

## How the agent treats pseudocode

When an agent sees an `.apseudo` file or a fenced `apseudo` block, the expected behavior is:

1. Treat the pseudocode as the process source of truth.
2. Treat prose as context unless prose conflicts with the pseudocode.
3. Preserve explicit loop bounds, guards, fallback branches, and terminal outcomes.
4. Stop and report conflicts instead of silently choosing one instruction.
5. Validate edited pseudocode before declaring the task complete.

This is why the repository ships `AGENTS.md`, `CLAUDE.md`, skills, hooks, and MCP support. They all reinforce the same contract.

## The most important design rule

Do not use pseudocode to describe everything.

Use this split:

| Need                             | Best format                       |
| -------------------------------- | --------------------------------- |
| Explain why the process exists   | Markdown prose                    |
| Define exact branches and loops  | Agent Pseudocode                  |
| Define non-negotiable invariants | RFC-style `MUST` / `SHOULD` rules |
| Define large condition matrices  | Markdown decision tables          |
| Show user commands               | Bash examples                     |
| Execute deterministic operations | Python or Bash                    |

Agent Pseudocode is strongest when it is the **control-flow kernel** inside a broader standard.

## How it becomes actionable

A pseudocode block becomes actionable through one of these paths:

| Path | How it works |
| --- | --- |
| Repository context | The agent reads `.apseudo` files and follows them when referenced. |
| Markdown fences | A standard embeds a fenced `apseudo` block as normative process logic. |
| Runner scripts | `apseudo-run` validates the file, renders a strict prompt, and launches Claude/Codex. |
| Hooks | Claude/Codex lifecycle hooks run validation after edits and before completion. |
| MCP | Agents call validation, explanation, template, and review tools. |
| LSP/editor | You get diagnostics, completion, hover, and formatting while authoring. |
| CI/pre-commit | Bad pseudocode cannot be merged unnoticed. |

The same language artifact can participate in several paths at once. For example, a `.apseudo` file can be read as repo context, validated by hooks, shown in VS Code with diagnostics, and launched as a shebang script.
