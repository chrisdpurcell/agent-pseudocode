# Documentation Index

The documentation tree is grouped by purpose so this repository can later be converted into a packaged `project-standards` standard without keeping every reference file in the repository root.

## Layout

| Folder | Purpose |
| --- | --- |
| `docs/specs/` | Normative language and executable-runner specifications, rule catalog, and language token/scope specs. |
| `docs/usage/` | User-facing command usage, install instructions, editor setup, testing instructions, agent wording, use-case guides, and operator guides. |
| `docs/features/` | Feature-specific implementation and usage references for formatter, LSP, autocomplete, MCP, hooks, and skills. |
| `docs/enforcement/` | Enforcement-specific guides for linter, pre-commit, CI, and agent-runtime checks. |
| `docs/examples/` | Example `.apseudo` files, Markdown fenced blocks, and executable runner scripts. |
| `docs/reviews/` | Project review outputs, traceability reviews, and feature-gap analyses. |
| `docs/roadmap/` | Future-version and deferred-work documents. |
| `docs/reference/` | Source register and background reference material. |

## Primary documents

| Need | Start here |
| --- | --- |
| Learn the language convention | `docs/specs/PYTHONIC_PSEUDOCODE_STANDARD.md` |
| Use the CLI tools | `docs/usage/usage.md` |
| Use executable `.apseudo` runner scripts | `docs/usage/RUNNER-USAGE.md` |
| Understand practical use cases | `docs/usage/use-cases/README.md` |
| Choose prose vs fenced blocks vs `.apseudo` vs runner scripts | `docs/usage/use-cases/CHOOSING-A-SURFACE.md` |
| Understand how agents receive pseudocode | `docs/usage/use-cases/AGENT-FEEDING-PATHS.md` |
| See common workflow examples | `docs/usage/use-cases/COMMON-WORKFLOWS.md` |
| Understand executable script semantics | `docs/specs/EXECUTABLE-PSEUDOCODE-SPEC.md` |
| Install editor support | `docs/usage/INSTALL.md` |
| Configure VS Code | `docs/usage/VSCODE.md` |
| Configure Kate | `docs/usage/KATE.md` |
| Copy agent instructions into another repo | `docs/usage/AGENT-INSTRUCTIONS-WORDING.md` |
| Review available APSEUDO rules | `docs/specs/RULES.md` |
| See future planned improvements | `docs/roadmap/FUTURE-VERSIONS.md` |
