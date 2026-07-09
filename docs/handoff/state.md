**Last updated:** 2026-07-08

## In flight

Adopting agent-handoff-v3 and six project-standards standards per `TODO.md`
(User Managed section), via a single implementation plan at
`docs/superpowers/plans/2026-07-08-adopt-standards.md`. Executing task-by-task.

## Recently landed

- `docs/adr/` created, scoped `markdown-frontmatter` adopted as prerequisite.

## Watch out for

- `.project-standards.yml`'s `markdown.frontmatter.include` is deliberately
  scoped to `docs/adr/**` only — do not widen it to the whole repo without a
  separate decision; this repo has ~150 pre-existing Markdown files with no
  frontmatter.
- `python-tooling` adoption bumps `requires-python` to `>=3.14` and swaps
  `pyright` → `basedpyright`, `hatchling` → `uv_build`.
