---
schema_version: '1.1'
id: 'reference-mbn9ms-markdown-fence-demo'
title: 'Markdown Fence Demo'
description: 'Example Markdown document showing Pythonic Agent Pseudocode fenced blocks.'
doc_type: 'reference'
status: 'active'
created: '2026-07-08'
updated: '2026-07-09'
reviewed: null
owner: 'agent-pseudocode-maintainers'
consumer: 'mix'
tags:
  - 'reference'
  - 'language'
  - 'usage'
aliases: []
related: []
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Markdown Fence Demo

This file tests VS Code Markdown injection for Agent Pseudocode.

```apseudo
process review_loop(document, max_rounds=5):
    round = 1

    while round <= max_rounds:
        result = review_document(document)

        if result.approved:
            return Accepted(reason="approved")

        elif result.blockers:
            document = revise(document, result.blockers)
            round += 1
            continue

        else:
            return Blocked(reason="ambiguous review result")

    return Blocked(reason="round cap reached")
```

The same grammar should also apply to:

```agent-pseudocode
process smoke_test():
    if tests_pass():
        return Accepted(reason="tests passed")
    else:
        return Blocked(reason="tests failed")
```
