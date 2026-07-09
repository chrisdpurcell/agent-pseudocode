# Formatter, Language Server, and Autocomplete Guide

**Date:** 2026-07-08  
**Status:** Working prototype / internal convention

This guide covers the additional enforcement and editor-assistance layer for the Pythonic Agent Pseudocode standard:

- `apseudo-format`: conservative formatter for `.apseudo` files and recognized Markdown fenced blocks.
- `apseudo-lsp`: dependency-free Language Server Protocol server for diagnostics, completion, hover, and formatting.
- VS Code integration using `vscode-languageclient`.
- Kate integration using the built-in LSP Client plugin.

The language itself remains an internal convention. The integration pattern follows the Language Server Protocol and editor extension conventions.

## 1. Install the Python tooling

From the repository root:

```bash
uv sync --extra dev
uv run apseudo-lint --version
uv run apseudo-format --check .
uv run apseudo-lsp --version
```

The package exposes three command-line entry points:

```text
apseudo-lint      Validate structure and instruction-following rules.
apseudo-format    Format standalone pseudocode and fenced Markdown blocks.
apseudo-lsp       Serve diagnostics, completion, hover, and formatting over stdio.
```

Wrapper scripts are also included:

```text
scripts/apseudo-lint
scripts/apseudo-format
scripts/apseudo-lsp
```

The wrappers are useful for repo-local hooks and editor configuration because they run through `uv` from the repository root.

## 2. Formatter behavior

The formatter is intentionally conservative. It does not try to execute pseudocode or fully rewrite logic. It normalizes:

- tabs to spaces;
- indentation width to configured multiples when `--round-indentation` is enabled;
- trailing whitespace;
- excessive blank lines inside pseudocode;
- simple Python-like header spacing;
- simple operator and comma spacing outside string literals;
- inline comment spacing;
- normative keyword casing inside comments.

Example input:

```text
process  demo( item ) :
	if   item=="ready" : # must check status
		return   Accepted(reason="done")
```

Formatted output:

```apseudo
process demo(item):
    if item == "ready":  # MUST check status
        return Accepted(reason="done")
```

### Format files in place

```bash
uv run apseudo-format docs examples
```

### Check formatting without writing

```bash
uv run apseudo-format --check .
```

### Show diffs

```bash
uv run apseudo-format --diff --check .
```

### Format stdin

```bash
cat docs/apseudo-docs/examples/review-loop.apseudo | uv run apseudo-format --stdin-filename review-loop.apseudo
```

## 3. Markdown formatting

Markdown files are not globally reformatted. Only fenced code blocks whose language matches the configured pseudocode fence aliases are formatted.

Recognized aliases are configured in `.apseudo-lint.toml`:

```toml
markdown_fence_languages = [
  "apseudo",
  "agent-pseudocode",
  "agent_pseudocode",
  "agentpseudo",
  "pythonic-pseudocode",
  "python-pseudocode",
  "pseudocode-python",
]
```

Example:

````markdown
```apseudo
process  demo() :
    return   Accepted(reason="done")
```
````

The formatter changes only the fenced pseudocode body.

## 4. Language server behavior

`apseudo-lsp` implements a small stdio JSON-RPC language server with no runtime dependency beyond the Python package itself.

Implemented LSP features:

| Feature | Method | Behavior |
|---|---|---|
| Diagnostics | `textDocument/publishDiagnostics` | Runs the same linter used by `apseudo-lint`. |
| Completion | `textDocument/completion` | Keywords, outcomes, annotations, and snippets. |
| Hover | `textDocument/hover` | Short docs for normative terms, outcomes, and annotations. |
| Formatting | `textDocument/formatting` | Calls the same formatter used by `apseudo-format`. |

The server intentionally does not implement rename, references, semantic tokens, or code actions yet.

### Run directly

```bash
uv run apseudo-lsp --stdio
```

For tracing during editor debugging:

```bash
uv run apseudo-lsp --stdio --trace
```

## 5. VS Code setup

The VS Code extension now includes:

- TextMate syntax highlighting;
- Markdown injection grammar;
- snippets for `.apseudo` files;
- Markdown fenced-block snippets;
- a language-client launcher for `apseudo-lsp`;
- document formatting through the language server;
- diagnostics through the language server;
- completion and hover through the language server.

### Development install

```bash
cd products/vscode-extension
npm install
npm run check
```

Open the `products/vscode-extension/` folder in VS Code and press `F5` to launch an Extension Development Host.

### Package and install

```bash
cd products/vscode-extension
npm run package
code --install-extension agent-pseudocode-0.6.1.vsix --force
```

For VS Codium:

```bash
codium --install-extension agent-pseudocode-0.6.1.vsix --force
```

### Language server command resolution

By default, the extension tries these options:

1. A configured command from `agentPseudocode.server.command`.
2. A repo-local `scripts/apseudo-lsp` wrapper.
3. `uv run apseudo-lsp` in a workspace containing `pyproject.toml`.
4. `apseudo-lsp` on `PATH`.

The most reliable local development setup is to open the repository root as the workspace and keep `uv` available on `PATH`.

### VS Code settings

Example `.vscode/settings.json`:

```json
{
  "agentPseudocode.server.command": "",
  "agentPseudocode.server.args": [],
  "agentPseudocode.server.cwd": "",
  "agentPseudocode.server.trace": false,
  "agentPseudocode.server.enableMarkdown": true,
  "editor.formatOnSave": false,
  "[agent-pseudocode]": {
    "editor.defaultFormatter": "l3digital.agent-pseudocode",
    "editor.formatOnSave": true
  }
}
```

When `server.command` is empty, the extension auto-detects the server as described above.

### Markdown in VS Code

The language server attaches to Markdown by default so diagnostics and formatting can apply to fenced `apseudo` blocks. Formatting a Markdown document formats only recognized pseudocode fences.

To disable Markdown LSP attachment, set:

```json
{
  "agentPseudocode.server.enableMarkdown": false
}
```

## 6. Kate setup

Kate has two separate layers:

1. KSyntaxHighlighting XML: colors `.apseudo` files.
2. LSP Client plugin: starts `apseudo-lsp` for diagnostics, completion, hover, and formatting.

### Install syntax highlighting

```bash
./scripts/install-kate-user.sh
```

Restart Kate and open an `.apseudo` file. If needed, select:

```text
Tools → Highlighting → Scripts → Agent Pseudocode
```

### Enable Kate LSP Client

In Kate:

```text
Settings → Configure Kate → Plugins → LSP Client
```

Enable the plugin, apply, and restart Kate if needed.

Then open:

```text
Settings → Configure Kate → LSP Client → User Server Settings
```

Paste the contents of:

```text
products/kate-integration/lsp-client-settings.json
```

Default standalone `.apseudo` configuration:

```json
{
  "servers": {
    "agent-pseudocode": {
      "command": ["apseudo-lsp", "--stdio"],
      "url": "https://github.com/l3digital/agent-pseudocode-syntax",
      "highlightingModeRegex": "^Agent Pseudocode$",
      "rootIndicationFileNames": [
        ".apseudo-lint.toml",
        "apseudo.toml",
        "pyproject.toml",
        ".git"
      ]
    }
  }
}
```

For source-tree development, replace the command with the absolute path to the wrapper script, for example:

```json
"command": ["/home/chris/path/to/agent-pseudocode-syntax/scripts/apseudo-lsp"]
```

### Kate Markdown caveat

Kate can start an LSP server by highlighting mode. The default config targets only the `Agent Pseudocode` highlighting mode for standalone `.apseudo` files. If you want Kate to run the server on Markdown too, use:

```text
products/kate-integration/lsp-client-settings.markdown-opt-in.json
```

That maps both `Agent Pseudocode` and `Markdown` modes to the server. This is intentionally opt-in because it attaches the pseudocode server to every Markdown file in projects where the LSP config is active.

## 7. Autocomplete content

The language server completion list includes:

| Category | Examples |
|---|---|
| Control flow | `process`, `if`, `elif`, `else`, `while`, `for`, `return` |
| Outcomes | `Accepted(...)`, `Blocked(...)`, `NeedsUserDecision(...)`, `NeedsInput(...)` |
| Annotations | `# @bounded`, `# @external_stop_condition`, `# @exhaustive` |
| Snippets | process skeleton, bounded while loop, explicit branch chain, review loop |

VS Code also includes static snippet files. The LSP completions are editor-neutral and can be used by Kate or any other LSP client.

## 8. Recommended workflow

Use the tools in this order:

```bash
uv run apseudo-format .
uv run apseudo-lint .
uv run pytest
uv run ruff check src tests integrations/agent-hooks
uv run pyright
```

For CI and hooks, prefer check mode:

```bash
uv run apseudo-format --check .
uv run apseudo-lint .
```

## 9. Troubleshooting

### VS Code: no diagnostics or completions

Check:

- the extension is installed and active;
- the file language mode is `Agent Pseudocode` for `.apseudo` files;
- `uv run apseudo-lsp --version` works from the workspace root;
- the **Agent Pseudocode Language Server** output channel for startup errors;
- `agentPseudocode.server.command` if the server is not on `PATH`.

### VS Code: formatting does nothing

Check:

- the language server started;
- the file has recognized pseudocode content;
- for Markdown, the fenced block language is one of the configured aliases.

### Kate: LSP does not start

Check:

- the LSP Client plugin is enabled;
- the file mode is `Agent Pseudocode`;
- the `highlightingModeRegex` matches `Agent Pseudocode`;
- the `command` path is absolute or resolvable on Kate's environment `PATH`;
- Kate's Output panel for LSP startup errors.

### Kate: syntax highlighting works but LSP does not

Syntax highlighting and LSP are independent. The XML file only controls highlighting. The LSP Client plugin still needs its own JSON server configuration.

## 10. Internal convention notes

The formatter's transformations are project convention, not a published external standard. The LSP feature mapping is standard, but the rule IDs, outcomes, annotations, and pseudocode syntax are internal convention.

The formatter is intentionally conservative to avoid corrupting ambiguous pseudocode. Add stricter rewrites only after the fixture corpus grows.
