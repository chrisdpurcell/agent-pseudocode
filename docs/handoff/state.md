**Last updated:** 2026-07-09

## In flight

Adopting agent-handoff-v3 and six project-standards standards per `TODO.md`
(User Managed section), via a single implementation plan at
`docs/superpowers/plans/2026-07-08-adopt-standards.md`. Executing task-by-task.
`python-tooling` (Task 7) now done; `project-spec` and `python-coding` remain.

## Recently landed

- `docs/adr/` created, scoped `markdown-frontmatter` adopted as prerequisite.
- `python-tooling` adopted (Task 7, ADR-0002): `requires-python = ">=3.14"`,
  `hatchling` → `uv_build` (with `[tool.uv.build-backend] module-name =
  "apseudo_lint"` override for the project-name/module-name mismatch),
  `pyright` → `basedpyright`, `[dependency-groups].dev` replaces the `dev`
  extra, coverage + pip-audit added. All 12 `[project.scripts]` entry points
  verified working (`uv build` + smoke-run each). `apseudo-lint.yml` updated
  in place per ADR-0002 rather than adding a separate `check.yml`.

## Watch out for

- `.project-standards.yml`'s `markdown.frontmatter.include` is deliberately
  scoped to `docs/adr/**` only — do not widen it to the whole repo without a
  separate decision; this repo has ~150 pre-existing Markdown files with no
  frontmatter.
- **`apseudo-lint.yml`'s new `Run coverage` step will fail CI**: actual
  coverage is 60% against the `python-tooling` standard's `fail_under = 85`
  floor (`[tool.coverage.report]` in `pyproject.toml`). Do not silence this
  by lowering `fail_under` or removing the CI step — see TODO.md's "Task 10"
  entry for the module-by-module breakdown; closing the gap requires writing
  real tests, not a config change.
- `uv sync --extra dev` no longer works (that extra was replaced by
  `[dependency-groups].dev`) — use bare `uv sync` (the `dev` group syncs by
  default) or `uv sync --all-groups`.
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
