# Chris Implementation Guide: Agent Pseudocode Syntax Toolkit

**Date:** 2026-07-08  
**Audience:** You, plus coding agents implementing editor support.  
**Status:** Internal working guide.

## Goal

Create practical tooling for your Pythonic agent-pseudocode convention without turning the convention into a full programming language.

## Current deliverables

1. `.apseudo`, `.agentpseudo`, and `.pseudocode` standalone files highlight in VS Code.
2. Markdown fenced code blocks highlight in VS Code when the fence language is recognized.
3. `.apseudo` standalone files highlight in Kate.
4. VS Code grammars are maintained in YAML and compiled to JSON.
5. `apseudo-lint` validates structural rules.
6. `apseudo-format` conservatively formats source and Markdown fences.
7. `apseudo-lsp` provides diagnostics, autocomplete, hover, and formatting.
8. VS Code starts `apseudo-lsp` through `vscode-languageclient`.
9. Kate can start `apseudo-lsp` through the LSP Client plugin.
10. Pre-commit, CI, Claude Code hooks, and Codex hooks reuse the same validator/formatter.

## Recommended workflow

### 1. Put this repo under version control

```bash
cd agent-pseudocode-syntax
git init
git add .
git commit -m "Initial agent pseudocode toolkit"
```

### 2. Run the Python smoke test

```bash
uv sync --extra dev
scripts/run-enforcement-smoke-test.sh
```

### 3. Test VS Code in extension-development mode

```bash
cd products/vscode-extension
npm install
npm run check
code .
```

Press `F5`. In the Extension Development Host, open:

```text
docs/examples/review-loop.apseudo
docs/examples/markdown-fence-demo.md
```

Check:

- syntax highlighting;
- completion popup on `ret`, `Acc`, `# @`, and `while`;
- hover on `MUST`, `while`, `Accepted`, and `@bounded`;
- diagnostics for intentionally invalid pseudocode;
- document formatting.

### 4. Package VS Code

```bash
cd products/vscode-extension
npm run package
code --install-extension agent-pseudocode-0.6.1.vsix --force
```

For VS Codium, replace `code` with `codium`.

### 5. Install Kate highlighter and LSP config

```bash
./scripts/install-kate-user.sh
```

Restart Kate. Open `products/kate-integration/examples/review-loop.apseudo`. If auto-detection does not pick it up, choose:

```text
Tools → Highlighting → Scripts → Agent Pseudocode
```

Enable the LSP Client plugin and paste `products/kate-integration/lsp-client-settings.json` into User Server Settings. Use an absolute path to `scripts/apseudo-lsp` if Kate cannot find `apseudo-lsp`.

## What still needs human review

### VS Code runtime behavior

The files validate statically, but the final check is a real Extension Development Host session. Confirm that the language server starts and the output channel has no startup errors.

### Kate LSP behavior

Kate LSP configuration depends on the local Kate version and environment `PATH`. Confirm that the Output panel shows the Agent Pseudocode server starting for `.apseudo` files.

### Markdown LSP behavior in Kate

Markdown LSP mapping is opt-in. Use `products/kate-integration/lsp-client-settings.markdown-opt-in.json` only when you want the pseudocode server attached to Markdown mode.

## What not to overbuild yet

Do not add Tree-sitter, semantic tokens, rename, code actions, or a full parser until the convention stabilizes. The current linter/formatter/LSP architecture is intentionally line-oriented and conservative.
