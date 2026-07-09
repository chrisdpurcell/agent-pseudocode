# Markdown fixture

```apseudo
process deploy_candidate(candidate, max_attempts=3):
    attempt = 1

    while attempt <= max_attempts:
        result = deploy_once(candidate)
        if result.ok:
            return Accepted(reason="deployed")
        else:
            attempt += 1
            continue

    return Blocked(reason="deployment failed")
```
