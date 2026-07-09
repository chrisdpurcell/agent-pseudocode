# Testing Guide

**Date:** 2026-07-08

## Static checks included

From `products/vscode-extension/`:

```bash
npm run check
```

This compiles `.tmLanguage.yaml` to `.tmLanguage.json`, parses generated JSON, and confirms files referenced from `package.json` exist.

Check Kate XML well-formedness from the repo root:

```bash
python - <<'PY_KATE_XML'
import xml.etree.ElementTree as ET
ET.parse('products/kate-integration/agent-pseudocode.xml')
print('Kate XML is well-formed')
PY_KATE_XML
```

## Manual VS Code test

1. Open `products/vscode-extension/` in VS Code.
2. Press `F5`.
3. Open `docs/apseudo-docs/examples/review-loop.apseudo`.
4. Confirm language mode is **Agent Pseudocode**.
5. Run **Developer: Inspect Editor Tokens and Scopes**.

Representative expected scope fragments:

| Token | Scope fragment |
|---|---|
| `process` | `keyword.declaration.function.agent-pseudocode` |
| `while` | `keyword.control.agent-pseudocode` |
| `MUST NOT` | `keyword.other.normative.agent-pseudocode` |
| `Accepted` | `support.class.outcome.agent-pseudocode` |
| `review_document` | `entity.name.function.call.agent-pseudocode` |

## Manual Kate test

1. Install XML with `./scripts/install-kate-user.sh`.
2. Restart Kate.
3. Open `products/kate-integration/examples/review-loop.apseudo`.
4. Select **Tools → Highlighting → Scripts → Agent Pseudocode** if needed.
