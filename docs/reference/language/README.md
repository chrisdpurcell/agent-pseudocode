# Language Spec Directory

This directory is the shared source of truth for the editor adapters.

- `TOKEN-SPEC.md` defines what the language recognizes.
- `SCOPE-MAP.md` maps tokens to VS Code and Kate style concepts.
- `examples/` contains canonical sample files used to test highlighters.

When adding a new keyword or outcome name, update this directory first, then update the VS Code grammar and Kate XML.
