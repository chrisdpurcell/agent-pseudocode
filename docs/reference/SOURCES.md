# Sources

**Date:** 2026-07-08

This project is mostly an internal convention, but the editor integration choices are based on official documentation and published editor protocols.

## VS Code

- Visual Studio Code Extension API, **Syntax Highlight Guide**. Used for TextMate grammar behavior, injection grammar mechanics, embedded languages, scope inspection, and the note that VS Code loads JSON grammars while YAML grammars must be converted. <https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide>

- Visual Studio Code Extension API, **Contribution Points**. Used for `contributes.languages`, `contributes.grammars`, snippets, commands, configuration, and the static contribution model. <https://code.visualstudio.com/api/references/contribution-points>

- Visual Studio Code Extension API, **Language Server Extension Guide**. Used for the language-client / language-server architecture in the VS Code extension. <https://code.visualstudio.com/api/language-extensions/language-server-extension-guide>

- Visual Studio Code Extension API, **Programmatic Language Features**. Used for the mapping of editor features such as diagnostics, completion, hover, and formatting to LSP capabilities. <https://code.visualstudio.com/api/language-extensions/programmatic-language-features>

- Visual Studio Code Extension API, **Extension Anatomy**. Used for the role of `package.json` as the extension manifest. <https://code.visualstudio.com/api/get-started/extension-anatomy>

- Visual Studio Code Extension API, **Extension Manifest**. Used for combining language definitions, grammars, snippets, activation events, dependencies, and commands in one extension manifest. <https://code.visualstudio.com/api/references/extension-manifest>

## Language Server Protocol

- Microsoft, **Language Server Protocol Specification 3.17**. Used for stdio JSON-RPC message structure, server capabilities, diagnostics, completion, hover, and formatting request/response shapes. <https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/>

## Kate / KDE

- KDE Documentation, **Working with Syntax Highlighting**. Used for XML syntax definition structure, required `language` attributes, contexts, keyword lists, `itemData`, default styles, comments, folding, and install paths. <https://docs.kde.org/stable_kf6/en/kate/katepart/highlight.html>

- KDE Documentation, **LSP Client Plugin**. Used for Kate LSP features such as completion, hover, diagnostics, and document formatting. <https://docs.kde.org/trunk_kf6/en/kate/kate/kate-application-plugin-lspclient.html>

- Kate Editor blog, **LSP Client Status**. Used for the `highlightingModeRegex` server mapping model in Kate LSP Client settings. <https://kate-editor.org/post/2020/2020-01-01-kate-lsp-client-status/>

## Python packaging and tooling

- Python standard library, `json`, `argparse`, `dataclasses`, `pathlib`, `tomllib`, and `urllib.parse` documentation are relevant to implementation mechanics. The language server intentionally avoids third-party Python runtime dependencies.

## Internal convention

The language name, token taxonomy, outcome constructors, annotation names, fence aliases, formatting choices, rule names, and linter behavior are internal conventions for the Pythonic Agent Pseudocode standard. They are not external standards.

## Additional tooling sources used for version 0.4.0

- Claude Code Hooks Reference — lifecycle events, configuration nesting, hook locations, matcher behavior, and stdin JSON context: <https://code.claude.com/docs/en/hooks>
- Claude Code Skills — `SKILL.md` structure, frontmatter, project skill discovery, and live updates: <https://code.claude.com/docs/en/skills>
- Codex Hooks — repository hook locations, supported lifecycle events, common stdin fields, and hook output behavior: <https://developers.openai.com/codex/hooks>
- Codex MCP — STDIO MCP configuration through `[mcp_servers.<name>]`, server instructions, and CLI/IDE support: <https://developers.openai.com/codex/mcp>
- Codex Skills — `.agents/skills` repository locations, required `SKILL.md` fields, optional `agents/openai.yaml`, and invocation model: <https://developers.openai.com/codex/skills>
- Model Context Protocol transports — stdio newline-delimited JSON-RPC and stdout/stderr rules: <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports>
- Language Server Protocol 3.17 — diagnostics, completion, code actions, hover, symbols, and synchronized document-state model: <https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/>
- VS Code Language Server Extension Guide — editor/client pattern for language server integration: <https://code.visualstudio.com/api/language-extensions/language-server-extension-guide>
