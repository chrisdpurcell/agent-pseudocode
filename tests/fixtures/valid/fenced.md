# Valid fenced block

```apseudo
process smoke_test(max_rounds=1):
    round = 1
    while round <= max_rounds:
        if tests_pass():
            return Accepted(reason="tests passed")
        else:
            return Blocked(reason="tests failed")
    return Blocked(reason="round cap reached")
```
