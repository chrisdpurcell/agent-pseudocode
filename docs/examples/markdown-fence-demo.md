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
