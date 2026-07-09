**Last updated:** 2026-07-09

## In flight

Nothing. Standards adoption (agent-handoff-v3 + adr, markdown-tooling,
cli-documentation, project-spec, python-tooling, python-coding) merged to
`main` 2026-07-09 (`4ac4d37`). See `STATUS.md` for current state, `TODO.md`
for open follow-ups, `docs/handoff/bugs/` for 4 open bug records found
during adoption (not introduced by it).

## Recently landed

- Standards adoption plan (`docs/superpowers/plans/2026-07-08-adopt-standards.md`)
  fully executed and merged. See `docs/adr/adr-0001-*.md` and `adr-0002-*.md`
  for the two recorded deviations.
- 4 pre-existing bugs found during adoption, recorded (not fixed) in
  `docs/handoff/bugs/001` through `004` — see TODO.md's Agent Tracked Tasks
  for the summary and links.

## Watch out for

- 3 CI gates are deliberately deferred (config adopted, enforcement not
  wired): markdown lint/format, `project-spec` validate, coverage floor.
  Details and re-enable steps are in `TODO.md`'s Agent Tracked Tasks, not
  duplicated here.
- See `docs/handoff/conventions.md` C-004/C-005 for the frontmatter-scope
  and `uv sync` gotchas.
