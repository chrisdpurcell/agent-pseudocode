# Kate Integration

## Files

- `products/kate-integration/agent-pseudocode.xml` — KSyntaxHighlighting XML definition.
- `products/kate-integration/lsp-client-settings.json` — standalone `.apseudo` LSP configuration.
- `products/kate-integration/lsp-client-settings.markdown-opt-in.json` — optional Markdown LSP configuration.

## Install highlighting

```bash
./scripts/install-kate-user.sh
```

This copies `products/kate-integration/agent-pseudocode.xml` to the user syntax-highlighting directory.

## Enable LSP

1. Enable Kate's LSP Client plugin.
2. Open LSP Client settings.
3. Paste `products/kate-integration/lsp-client-settings.json` into User Server Settings.
4. Replace `apseudo-lsp` with an absolute path to `scripts/apseudo-lsp` if Kate cannot find the command.

## Supported LSP features

Kate's LSP Client can surface server-provided diagnostics, completion, hover, formatting, code actions, document symbols, folding, definition, and references depending on Kate version and plugin settings.

## Markdown

Use Markdown LSP opt-in only if you want diagnostics inside Markdown `apseudo` fences. Syntax highlighting for fenced blocks is handled primarily by the editor's Markdown support and the VS Code injection grammar; Kate's XML definition is focused on standalone pseudocode files.
