# Products and Editor Integrations

This folder contains distributable or editor-facing product assets. They are kept together to avoid root-level sprawl while preserving the build/test behavior of each product.

| Folder | Purpose |
| --- | --- |
| `products/vscode-extension/` | VS Code extension source: TextMate grammars, Markdown injection grammar, snippets, LSP client, and VSIX packaging scripts. |
| `products/kate-integration/` | Kate / KSyntaxHighlighting XML definition, Kate LSP client examples, and Kate-specific examples. |

Generated distribution artifacts such as `.vsix` packages are intentionally produced inside the relevant product folder during packaging and are not required for source development.
