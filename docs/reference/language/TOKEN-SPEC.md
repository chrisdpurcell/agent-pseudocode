---
schema_version: '1.1'
id: 'reference-ucipiw-agent-pseudocode-token-specification'
title: 'Agent Pseudocode Token Specification'
description: 'Reference specification for Pythonic Agent Pseudocode tokens.'
doc_type: 'reference'
status: 'active'
created: '2026-07-09'
updated: '2026-07-09'
reviewed: null
owner: 'language-maintainers'
consumer: 'mix'
tags:
  - 'reference'
  - 'language'
aliases:
  - 'token spec'
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Agent Pseudocode Token Specification

**Version:** 0.1.0  
**Date:** 2026-07-08  
**Status:** Internal convention.

This document is the source-of-truth token map for the VS Code and Kate syntax highlighters.

## File identity

| Concept | Value | Status |
| --- | --- | --- |
| Language name | Agent Pseudocode | Internal convention |
| VS Code language ID | `agent-pseudocode` | Internal convention |
| Primary file extension | `.apseudo` | Internal convention |
| Secondary file extensions | `.agentpseudo`, `.pseudocode` | Internal convention |
| Markdown fence aliases | `apseudo`, `agent-pseudocode`, `agentpseudo`, `python-pseudocode`, `py-pseudocode` | Internal convention |

## Token classes

| Token class | Examples | Purpose | Internal or sourced? |
| --- | --- | --- | --- |
| Process declaration | `process review_loop(...):`, `def helper(...):` | Defines workflow/subroutine | Internal convention based on Python shape |
| Control keyword | `if`, `elif`, `else`, `while`, `for`, `return`, `continue`, `break` | Structural flow | Borrowed from Python control-flow vocabulary |
| Logical operator | `and`, `or`, `not`, `is`, `in` | Conditions | Borrowed from Python vocabulary |
| Normative keyword | `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY`, `REQUIRED`, `OPTIONAL` | Requirement force | Based on RFC-style convention |
| Outcome constructor | `Accepted`, `Blocked`, `NeedsUserDecision` | Terminal or intermediate workflow result | Internal convention |
| Agent action | `review_document(...)`, `revise(...)`, `run_tests(...)` | Required operation performed by agent | Internal convention |
| Literal | strings, numbers, `True`, `False`, `None` | Data values | Borrowed from Python shape |
| Comment | `# comment` | Non-normative explanation | Borrowed from Python shape |
| Decorator / annotation | `@requires_user_approval` | Optional metadata | Internal convention based on Python shape |

## Minimal grammar expectation

```apseudo
process name(input_a, input_b, max_rounds=5):
    state = initialize_state(input_a, input_b)

    while state.round <= max_rounds:
        result = review(state)

        if result.status == "approved":
            return Accepted(reason="approved")

        elif result.blockers:
            state = revise(state, result.blockers)
            state.round += 1
            continue

        else:
            return Blocked(reason="ambiguous result")

    return Blocked(reason="round cap reached")
```

## Not in scope for v0.1.0

The highlighters do not validate indentation, prove loops terminate, enforce outcome enums, or detect missing terminal returns. Those checks belong in a future linter.
