# Kate Files

- `agent-pseudocode.xml`: KSyntaxHighlighting definition for standalone pseudocode files.
- `lsp-client-settings.json`: LSP Client settings for standalone pseudocode files.
- `lsp-client-settings.markdown-opt-in.json`: optional Markdown LSP settings.

Install the XML file with:

```bash
../scripts/install-kate-user.sh
```

Then configure Kate's LSP Client plugin. If `apseudo-lsp` is not on `PATH`, use the absolute path to `scripts/apseudo-lsp`.
