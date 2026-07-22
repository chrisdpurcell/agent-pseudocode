---
bug_id: '006'
date: '2026-07-22'
title: 'apseudo-explain --json and apseudo-template --json crash on slots dataclasses'
services: [cli]
status: fixed
---

## Cause

`Rule` and `Template` are both declared `@dataclass(frozen=True, slots=True)`. `slots=True` gives instances no `__dict__`, but three CLI call sites serialized them through it:

```python
# explain_cli.py
print(json.dumps([rule.__dict__ for rule in rules], indent=2, sort_keys=True))

# template_cli.py, both the listing and single-template branches
print(json.dumps([template.__dict__ for template in templates], indent=2, sort_keys=True))
print(json.dumps(template.__dict__, indent=2, sort_keys=True))
```

Every invocation raised:

```text
AttributeError: 'Rule' object has no attribute '__dict__'. Did you mean: '__dir__'?
```

So `apseudo-explain --json`, `apseudo-template --json`, `apseudo-template --list --json`, and `apseudo-template <name> --json` were all completely broken — not edge cases, the only behavior those flags have.

The correct pattern already existed in the same codebase: `mcp.py:197` serializes the identical `Rule` objects with `dataclasses.asdict`. The MCP `list_rules` tool therefore worked while the CLI flag it mirrors did not.

Found while gathering the rule catalog to author `docs/specs/apseudo-validation-toolchain.md`; the documentation task exercised a flag no test covered.

## Fix

Applied 2026-07-22: replaced all three `__dict__` reads with `dataclasses.asdict`, matching `mcp.py`.

Added `tests/test_cli_json_output.py` — seven tests covering both listing paths, the single-item paths, and the exit-2 unknown-name paths for each command. There was no prior coverage of either `--json` flag, which is why a total failure survived.

## Lesson

`slots=True` silently removes `__dict__`. Any `obj.__dict__` on a dataclass is a latent crash the moment someone adds slots — and adding slots is a routine performance/immutability change that looks unrelated. Use `dataclasses.asdict` (or `fields()`) for dataclass serialization, always.

Second lesson: a flag with no test can be 100% broken and still ship. `--json` output paths are exactly the kind of surface a human never exercises interactively but an integration depends on. When one module gets a serialization pattern right and another does not, the gap is usually missing tests rather than intentional divergence — grep for the pattern repo-wide when fixing one instance.
