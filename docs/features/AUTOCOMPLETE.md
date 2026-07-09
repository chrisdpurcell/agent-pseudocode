# Agent Pseudocode Autocomplete

Autocomplete is provided in two layers:

1. Static VS Code snippets in `products/vscode-extension/snippets/`.
2. Editor-neutral LSP completions from `apseudo-lsp`.

Completion categories:

- control-flow keywords;
- approved outcome constructors;
- annotations and lint suppressions;
- process, review-loop, bounded-while, and branch-chain snippets.

Kate receives autocomplete through the LSP Client plugin when `apseudo-lsp` is configured for the `Agent Pseudocode` highlighting mode.
