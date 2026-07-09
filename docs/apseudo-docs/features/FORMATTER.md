# Agent Pseudocode Formatter

Use `apseudo-format` to normalize standalone `.apseudo` files and recognized pseudocode fences in Markdown.

```bash
uv run apseudo-format .
uv run apseudo-format --check .
uv run apseudo-format --diff --check docs examples
```

The formatter normalizes whitespace, indentation width, simple Python-like spacing, inline comment spacing, and normative keyword casing inside comments. It is intentionally conservative and does not rewrite control flow.

See `docs/features/FORMATTER-LSP-AUTOCOMPLETE.md` for full details.
