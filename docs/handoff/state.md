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
- `markdown-tooling` adopted with lint+format CI **deliberately deferred**:
  `.markdownlint.json` / `.prettierrc.json` / `.markdownlint-cli2.jsonc` are
  seeded, but `.github/workflows/lint-markdown.yml` was deleted after the
  adopt CLI wrote it (this repo has never been linted) and `format.yml`'s
  `prettier` input is set `false`. A local `npx markdownlint-cli2 "**/*.md"
  "#node_modules"` run found **489 errors across 33 of 83 Markdown files** —
  do not attempt to fix these inline; a dedicated full-repo cleanup task
  (Task 9) must run `npx prettier@3.8.3 --write .` and
  `npx markdownlint-cli2 --fix "**/*.md"`, review the diff, then re-add
  `lint-markdown.yml` and flip `format.yml`'s `prettier` to `true`.
