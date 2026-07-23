---
title: 'Repository Explainer Video Implementation Plan'
slug: 'repository-explainer-video'
size: full
status: active
source: 'docs/specs/repository-explainer-video.md (SPEC-NSBJ)'
spec_ref: 'docs/specs/repository-explainer-video.md'
created: 2026-07-23
updated: 2026-07-23
owners:
  - 'Chris Purcell'
  - 'Codex, supervised by the owner'
test_framework: pytest
---

# Repository Explainer Video Implementation Plan

**For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task by task.

> **This file is definition, not state.** It is read-only during implementation except when appending discovered work or harvesting close-out facts. Live progress belongs in the generated per-phase checklists under `.project-pipeline/2026-07-23-repository-explainer-video/`.

## 1. Objective

Build and deliver a reproducible 135-second, 1920×1080, 30 fps repository explainer with truthful Pythonic Agent Pseudocode captures, OpenAI `marin` narration, burned-in captions, a narration-free speaker cut, and machine-readable verification evidence.

## 2. Background

`SPEC-NSBJ` defines a six-scene conference film that makes agent behavior visible, verifiable, and executable. The repository has the product examples and tools but no media-production source, capture ledger, TTS adapter, deterministic renderer, or media verification harness. This plan adds those production surfaces without changing or shipping them as part of the `apseudo_lint` package.

The pipeline treats repository output as evidence rather than decorative copy. Visuals may recompose genuine source and command output for conference legibility, but may not change their semantics. OpenBao owns the Speech API credential; generated intermediates and delivery media remain ignored.

## 3. Scope

### 3.1 In Scope

- A typed, validated project and evidence-manifest model.
- One source of truth for narration segments and caption timing.
- Reproducible capture of formatter, linter, rule, Mermaid, and runner evidence.
- Deterministic SVG scene composition using repository source and captured output.
- A restricted, retry-bounded OpenAI Speech adapter for `marin`.
- FFmpeg assembly of narrated and speaker exports from one timeline.
- FFprobe, EBU R128, caption, authenticity, secret, and checksum verification.
- The six approved scenes, production sources, reviewed captures, final local exports, delivery metadata, and close-out documentation.

### 3.2 Out of Scope

- Modifying Pythonic Agent Pseudocode behavior to make filming easier.
- Publishing the MP4 to GitHub or another hosting service.
- Tracking generated WAV, MP4, frame sequences, or provider responses in Git.
- Alternate aspect ratios, translated narration, or human voice recording.
- A general-purpose video editor or public media-production API.
- Repairing the repository's unrelated existing coverage-floor backlog.

### 3.3 Assumptions

- FFmpeg 8 with `librsvg`, `drawtext`, `subtitles`, `ebur128`, AAC, and an H.264 encoder remains available; capability checks fail early if the environment changes.
- Noto Sans and Noto Sans Mono remain available on the production workstation; missing fonts block rendering rather than silently substituting metrics.
- A real read-only runner result is shown only if its preserved post-checks pass; otherwise the approved preflight-only alternate scene is rendered.
- Venue-specific delivery requirements remain unknown, so the specification's codec, loudness, and title-safe contract is authoritative.

### 3.4 Constraints

- Use Python 3.14, the standard library, uv, pytest, Ruff, and BasedPyright strict.
- Keep the production package under `media/repository-explainer/`; do not add it to the distributed `apseudo_lint` wheel.
- Use real tracked source or captured command output for every claimed interaction.
- Store only the OpenBao credential reference; never print, persist, capture, or scan the credential value into evidence.
- Validate changed pseudocode with formatter check before linter.
- Use generated checklists for progress; do not put routine state in this master.

## 4. Source Requirements

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| FR-001 | Communicate that behavior can be read, understood, validated, and run. | `SPEC-NSBJ` §7.1 | must | T2, T5, T10, T12 |
| FR-002 | Preserve the approved six-scene order. | `SPEC-NSBJ` §7.1 | must | T1, T5, T10, T12 |
| FR-003 | Feature a real validated Pythonic Agent Pseudocode workflow. | `SPEC-NSBJ` §7.1 | must | T5, T10 |
| FR-004 | Trace each real interaction to a command and named Git revision. | `SPEC-NSBJ` §7.1 | must | T3, T4, T10 |
| FR-005 | Show runner success only after a real read-only run and post-checks. | `SPEC-NSBJ` §7.1 | must | T4, T10 |
| FR-006 | Produce the narrated master with OpenAI `marin`. | `SPEC-NSBJ` §7.1 | must | T6, T11, T12 |
| FR-007 | Produce a speaker cut without narration. | `SPEC-NSBJ` §7.1 | must | T7, T11, T12 |
| FR-008 | Burn in English captions and retain reusable caption source. | `SPEC-NSBJ` §7.1 | must | T2, T7, T11, T12 |
| FR-009 | Support deterministic replacement and rerendering of assets. | `SPEC-NSBJ` §7.1 | must | T1, T7, T9, T11 |
| FR-010 | Disclose AI-generated narration. | `SPEC-NSBJ` §7.1 | must | T2, T5, T10, T12 |
| NFR-001 | Deliver 1920×1080, 30 fps H.264/AAC MP4. | `SPEC-NSBJ` §7.2 | must | T1, T7, T8, T11 |
| NFR-002 | Keep narrated duration between 125 and 145 seconds. | `SPEC-NSBJ` §7.2 | must | T1, T2, T7, T8 |
| NFR-003 | Preserve the complete story without audio. | `SPEC-NSBJ` §7.2 | must | T2, T5, T10, T12 |
| NFR-004 | Meet conference text size, title-safe, and contrast limits. | `SPEC-NSBJ` §7.2 | must | T1, T5, T8, T10 |
| NFR-005 | Reproduce equivalent streams from identical approved inputs. | `SPEC-NSBJ` §7.2 | must | T1, T7, T8, T9, T11 |
| NFR-006 | Preserve source and output semantics in composites. | `SPEC-NSBJ` §7.2 | must | T3, T5, T8, T10 |
| NFR-007 | Mix near −16 LUFS with true peak no higher than −1 dBTP. | `SPEC-NSBJ` §7.2 | must | T6, T7, T8, T11 |
| NFR-008 | Keep credentials out of source, logs, and media. | `SPEC-NSBJ` §7.2 | must | T3, T4, T6, T8, T9, T12 |
| NFR-009 | Keep attributable TTS spend under USD 1 unless re-approved. | `SPEC-NSBJ` §7.2 | should | T6, T11, T12 |

## 5. Repository and Architecture Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Product CLI | Produces genuine formatter, linter, rule, Mermaid, and runner evidence. | `src/apseudo_lint/`, `scripts/apseudo-*` |
| Example source | Supplies the hero workflow, teaching defect, and runner task. | `docs/apseudo-docs/examples/`, `tests/fixtures/invalid/` |
| Video source | Owns project data, production package, SVG assets, script, and evidence. | `media/repository-explainer/` |
| Generated delivery | Holds untracked intermediates, WAV stems, candidates, reports, and finals. | `dist/video/` |
| Production tests | Prove manifest, capture, speech, render, verification, and CLI behavior. | `tests/video/` |
| Handoff | Records approved spec, active plan, credential reference, and delivery state. | `docs/handoff/` |

### 5.2 Existing Behavior

The repository has no current video source or renderer. `uv run apseudo-format`, `uv run apseudo-lint`, `uv run apseudo-explain`, `uv run apseudo-mermaid`, and `uv run apseudo-run` provide the truthful product surfaces. FFmpeg, FFprobe, Noto fonts, SVG decoding, AAC, and H.264 encoding are available on the reference workstation. The existing Python test suite is rooted at `tests/`, and strict static checking currently covers `src` and `tests`.

### 5.3 Files Expected to Change

| Path | Action | Purpose | Owning task |
| --- | --- | --- | --- |
| `pyproject.toml` | modify | Add the production package to pytest/Ruff/BasedPyright paths without packaging it. | T1 |
| `media/repository-explainer/project.json` | create | Six-scene timeline, delivery, title-safe, and audio configuration. | T1 |
| `media/repository-explainer/video_pipeline/models.py` | create | Typed immutable manifest records. | T1 |
| `media/repository-explainer/video_pipeline/manifest.py` | create | Load and validate project, narration, capture, and delivery manifests. | T1 |
| `media/repository-explainer/narration.json` | create | Narration and caption source of truth. | T2 |
| `media/repository-explainer/captions.srt` | create | Reusable generated caption delivery source. | T2 |
| `media/repository-explainer/video_pipeline/captions.py` | create | Validate segments and render SRT deterministically. | T2 |
| `media/repository-explainer/video_pipeline/capture.py` | create | Execute allowlisted commands and record evidence. | T3 |
| `media/repository-explainer/captures/manifest.json` | create | Reviewed mapping from scenes to real commands and revision. | T3, T10 |
| `media/repository-explainer/captures/evidence/` | create | Promoted text/JSON evidence safe for composition. | T3, T10 |
| `media/repository-explainer/video_pipeline/runner_capture.py` | create | Disposable-worktree runner preflight, execution, and no-diff proof. | T4 |
| `media/repository-explainer/workflow.apseudo` | create | Recurring validated workflow visual subject. | T5, T10 |
| `media/repository-explainer/theme.json` | create | Colors, type sizes, safe area, and transition constants. | T5 |
| `media/repository-explainer/video_pipeline/scenes.py` | create | Render truthful scene SVGs from source and evidence. | T5 |
| `media/repository-explainer/assets/` | create | Tracked brand and scene-source SVGs. | T5, T10 |
| `media/repository-explainer/video_pipeline/speech.py` | create | Restricted Speech request, retry, WAV, and spend manifest. | T6 |
| `media/repository-explainer/video_pipeline/render.py` | create | Build scene clips and both FFmpeg timelines. | T7 |
| `media/repository-explainer/video_pipeline/verify.py` | create | Probe, loudness, caption, authenticity, secret, and checksum gates. | T8 |
| `media/repository-explainer/video_pipeline/cli.py` | create | Stage-oriented `capture`, `narrate`, `render`, `verify`, and `all` CLI. | T9 |
| `media/repository-explainer/video_pipeline/__main__.py` | create | Module entry point. | T9 |
| `media/repository-explainer/README.md` | create | Reproduction, credential, output, and verification instructions. | T9, T12 |
| `tests/video/` | create | Unit, contract, integration, and content tests for T1–T10. | T1–T10 |
| `docs/handoff/specs-plans.md` | modify | Track approved spec and active implementation plan. | T12 |
| `docs/handoff/state.md` | modify | Track current phase and delivery close-out. | T12 |
| `docs/handoff/deployed.md` | modify | Record local delivered artifact truth without claiming hosted publication. | T12 |

### 5.4 Dependencies

| Dependency | Type | Version / constraint | Reason |
| --- | --- | --- | --- |
| Python | runtime | 3.14 from project | Typed orchestration and tests. |
| FFmpeg / FFprobe | external | Capability-probed; reference is 8.1.2 | SVG rasterization, H.264/AAC rendering, subtitles, and media inspection. |
| Noto Sans / Noto Sans Mono | external | Fontconfig-resolved exact family names | Stable conference-safe typography. |
| OpenAI Speech API | external | `gpt-4o-mini-tts`, voice `marin` | Approved narration. |
| OpenBao | external | Existing workstation service | Runtime resolution of `OPENAI_API_KEY`. |
| uv / pytest / Ruff / BasedPyright | dev | Existing locked project tools | Test-first implementation and verification. |

No Python runtime dependency is added. The Speech request uses `urllib.request`; FFmpeg and repository tools run through argument-vector subprocess calls.

## 6. Test Strategy

- **Framework:** pytest through uv. Config: `pyproject.toml`. Test root: `tests/video/`. Shared fixtures: `tests/video/conftest.py` for temporary repositories, fake executables, WAV fixtures, and minimal manifests.
- **Commands:**
  - Targeted: `uv run pytest {path}::{test}`
  - File: `uv run pytest {path}`
  - Video subset: `uv run pytest tests/video`
  - Full: `uv run pytest`
  - Lint: `uv run ruff check media/repository-explainer/video_pipeline tests/video`
  - Format: `uv run ruff format --check media/repository-explainer/video_pipeline tests/video`
  - Types: `uv run basedpyright media/repository-explainer/video_pipeline tests/video`
  - Video coverage diagnostic: `uv run coverage run --source=media/repository-explainer/video_pipeline -m pytest tests/video`
- **Acceptance:** Test Cases in Appendix B must pass. Coverage is diagnostic, not the acceptance gate, and no new coverage-floor setting is introduced.

### 6.1 RED-GREEN-REFACTOR Contract

Each behavior task follows RED, Verify RED, GREEN, Verify GREEN, REFACTOR, and Verify Task. A RED test must assert observable output and fail because the behavior is absent or wrong. Import, collection, fixture, executable-discovery, or environment failures do not satisfy Verify RED.

Each Verify Task pass runs its targeted tests, nearest regression tests, Ruff check and format check on changed Python, BasedPyright on the production package and video tests, applicable external-tool probes, and then commits:

`T{n}: {summary} ({requirement IDs}, {test-case IDs})`

### 6.2 Test Categories

| Category | Purpose | Location |
| --- | --- | --- |
| Unit | Manifest, caption, SVG, cost, and probe parsing. | `tests/video/test_*.py` |
| Contract | Speech request shape and FFmpeg/FFprobe command contracts. | `tests/video/test_speech.py`, `tests/video/test_render.py` |
| Integration | Real local CLI, FFmpeg fixture render, and disposable Git workspace. | `tests/video/test_cli.py`, `tests/video/test_runner_capture.py` |
| Regression | Secret redaction, runner diff rejection, caption overlap, and nondeterministic metadata. | `tests/video/test_verify.py`, `tests/video/test_captions.py` |
| Content | Six scenes, approved copy, source hashes, disclosure, and conference-safe theme. | `tests/video/test_content.py` |
| End-to-end | Candidate render and final verification from fixture inputs. | `tests/video/test_cli.py` |

### 6.3 TDD Exceptions

| Task | Exception reason | Objective validation |
| --- | --- | --- |
| T11 | Paid provider generation and full-resolution rendering create ignored external artifacts rather than reusable code behavior. | Pipeline dry-run, bounded live TTS, FFmpeg exit status, FFprobe, EBU R128, and checksum reports. |
| T12 | Owner viewing and delivery promotion are acceptance operations. | Final `verify` report, narrated/muted representative-frame review, file inventory, and clean Git diff. |

## 7. Execution Summary

| Task | Title | Phase | Depends on | Requirement(s) | Primary verification |
| --- | --- | --- | --- | --- | --- |
| T1 | Define and validate the project manifest | P1 | None | FR-002, FR-009, NFR-001, NFR-002, NFR-004, NFR-005 | `uv run pytest tests/video/test_manifest.py` |
| T2 | Compile narration and captions from one source | P1 | T1 | FR-001, FR-008, FR-010, NFR-002, NFR-003 | `uv run pytest tests/video/test_captions.py` |
| T3 | Capture truthful command evidence | P1 | T1 | FR-004, NFR-006, NFR-008 | `uv run pytest tests/video/test_capture.py` |
| T4 | Capture guarded runner evidence | P1 | T3 | FR-004, FR-005, NFR-008 | `uv run pytest tests/video/test_runner_capture.py` |
| T5 | Compose conference-safe SVG scenes | P2 | T2, T3, T4 | FR-001, FR-002, FR-003, FR-010, NFR-003, NFR-004, NFR-006 | `uv run pytest tests/video/test_scenes.py tests/video/test_content.py` |
| T6 | Generate bounded `marin` narration | P2 | T2 | FR-006, NFR-007, NFR-008, NFR-009 | `uv run pytest tests/video/test_speech.py` |
| T7 | Render narrated and speaker timelines | P2 | T5, T6 | FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005, NFR-007 | `uv run pytest tests/video/test_render.py` |
| T8 | Verify media, authenticity, and security | P3 | T7 | FR-010, NFR-001–NFR-008 | `uv run pytest tests/video/test_verify.py` |
| T9 | Expose the reproducible production CLI | P3 | T3, T4, T6, T7, T8 | FR-009, NFR-005, NFR-008 | `uv run pytest tests/video/test_cli.py` |
| T10 | Lock approved content and real captures | P4 | T5, T9 | FR-001–FR-005, FR-008, FR-010, NFR-003, NFR-004, NFR-006, NFR-008 | `uv run pytest tests/video/test_content.py` |
| T11 | Generate narration and both final candidates | P4 | T10 | FR-006–FR-009, NFR-001, NFR-002, NFR-005, NFR-007, NFR-009 | `uv run python -m video_pipeline all --output dist/video/candidate` |
| T12 | Accept and deliver the verified film | P4 | T11 | FR-001, FR-002, FR-006–FR-010, NFR-001–NFR-009 | `uv run python -m video_pipeline verify --output dist/video/final` |

## 8. Implementation Tasks

## Phase P1: Evidence Foundation

### T1: Define and Validate the Project Manifest

- **goal:** A typed loader accepts exactly one coherent six-scene production manifest and rejects invalid timing, paths, media settings, safe areas, or nondeterministic output configuration.
- **phase:** P1
- **depends_on:** []
<!-- prettier-ignore -->
- **requirements:** [FR-002, FR-009, NFR-001, NFR-002, NFR-004, NFR-005]
- **priority:** must

#### T1 Context

Use frozen, slotted dataclasses and explicit JSON decoding. Reject unknown fields so misspelled production settings cannot silently change a render. Represent time as integer frames, not floating-point seconds. The approved scene boundaries are frames 0, 450, 1050, 1800, 2550, 3450, and 4050 at 30 fps.

#### T1 Files

| Action | Path | Purpose |
| --- | --- | --- |
| modify | `pyproject.toml` | Add `media/repository-explainer` to local test/static-analysis paths. |
| create | `media/repository-explainer/project.json` | Approved timeline and delivery configuration. |
| create | `media/repository-explainer/video_pipeline/__init__.py` | Production package marker. |
| create | `media/repository-explainer/video_pipeline/models.py` | Immutable records and enums. |
| create | `media/repository-explainer/video_pipeline/manifest.py` | Strict loader and cross-record validation. |
| create | `tests/video/conftest.py` | Shared manifest and executable fixtures. |
| create | `tests/video/test_manifest.py` | Unit and property-like boundary coverage. |

#### T1 Acceptance Criteria

- The approved manifest loads to six ordered, gap-free scenes totaling 4050 frames and declares 1920×1080 at 30 fps. (TC-T1-001)
- Unknown keys, path escapes, missing scene IDs, overlaps, gaps, unsafe text sizes, and a duration outside 125–145 seconds are rejected with field-specific errors. (TC-T1-002)
- Source paths resolve inside the repository, while generated paths resolve only inside the selected ignored output root. (TC-T1-003)

#### T1 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T1-001 | `test_loads_approved_six_scene_manifest` | unit | Exact order, boundaries, dimensions, and fps are returned. |
| TC-T1-002 | `test_rejects_invalid_manifest_invariants` | unit | Each mutated invalid field produces its named validation error. |
| TC-T1-003 | `test_rejects_paths_outside_owned_roots` | security | Traversal and absolute output paths are rejected. |

#### T1 Sub-tasks

- **T1.1 RED** — add the three tests in `tests/video/test_manifest.py`; expected failure: the production models and strict loader do not exist.
- **T1.2 Verify RED** — run `uv run pytest tests/video/test_manifest.py -x`; confirm the missing loader, not collection or fixture setup, causes the failure.
- **T1.3 GREEN** — add the minimum models, loader, project manifest, and `pyproject.toml` path configuration needed to satisfy the tests.
- **T1.4 Verify GREEN** — run `uv run pytest tests/video/test_manifest.py` and `uv run pytest tests/test_cli_json_output.py`.
- **T1.5 REFACTOR** — centralize integer/range/path validation without a generic framework; preserve precise error messages.
- **T1.6 Verify Task** — run the T1 tests, Ruff, Ruff format, BasedPyright, and `uv run python -m video_pipeline --help`; commit with requirement and test IDs.

### T2: Compile Narration and Captions from One Source

- **goal:** One ordered JSON narration source deterministically produces valid SRT captions and enforces duration, readability, disclosure, and mute-safe copy.
- **phase:** P1
- **depends_on:** [T1]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-008, FR-010, NFR-002, NFR-003]
- **priority:** must
- **files:** `media/repository-explainer/narration.json` (create), `media/repository-explainer/captions.srt` (create), `media/repository-explainer/video_pipeline/captions.py` (create), `tests/video/test_captions.py` (create)
- **acceptance:** ordered segments stay within their scene frames, contain no overlap, keep captions to two lines and readable dwell time, preserve the six scene messages, and include the AI-narration disclosure (TC-T2-001, TC-T2-002); repeated compilation is byte-identical (TC-T2-003).
- **sub-tasks:**
  - **T2.1 RED** — add caption parsing, invariant, disclosure, and deterministic SRT tests; expected failure: no compiler or narration source exists.
  - **T2.2 Verify RED** — run `uv run pytest tests/video/test_captions.py -x`; confirm the missing compiler/source causes failure.
  - **T2.3 GREEN** — implement frame-based segment validation and SRT emission; author the six-scene narration source and generated SRT.
  - **T2.4 Verify GREEN** — run the caption tests and manifest tests; compare a second compile byte for byte.
  - **T2.5 REFACTOR** — isolate timestamp formatting and line wrapping; do not create alternate script sources.
  - **T2.6 Verify Task** — run T1–T2 tests plus static checks; commit with IDs.

### T3: Capture Truthful Command Evidence

- **goal:** An allowlisted capture stage records exact argument vectors, named Git revision, exit status, stdout/stderr hashes, and promoted safe output for repository tool interactions.
- **phase:** P1
- **depends_on:** [T1]
<!-- prettier-ignore -->
- **requirements:** [FR-004, NFR-006, NFR-008]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/capture.py` (create), `media/repository-explainer/captures/manifest.json` (create), `media/repository-explainer/captures/evidence/` (create), `tests/video/test_capture.py` (create)
- **acceptance:** captures bind output to command, cwd, revision, exit status, timestamp, and SHA-256 (TC-T3-001); shell strings, disallowed executables, dirty-source ambiguity, path escapes, and credential-like environment or output fail closed (TC-T3-002); reviewed promotion copies only named evidence and preserves bytes (TC-T3-003).
- **sub-tasks:**
  - **T3.1 RED** — add fake-executable and temporary-Git tests; expected failure: the allowlisted capture and promotion APIs do not exist.
  - **T3.2 Verify RED** — run `uv run pytest tests/video/test_capture.py -x`; confirm missing behavior rather than Git setup causes failure.
  - **T3.3 GREEN** — implement argument-vector subprocess capture, Git binding, redaction rejection, hashing, and explicit evidence promotion.
  - **T3.4 Verify GREEN** — run capture and manifest tests; run one harmless `uv run apseudo --version` fixture capture.
  - **T3.5 REFACTOR** — share owned-path and canonical-JSON helpers with the manifest layer while keeping executable policy local to capture.
  - **T3.6 Verify Task** — run T1–T3 tests and static checks; inspect the fixture capture for secret-free command/environment fields; commit with IDs.

### T4: Capture Guarded Runner Evidence

- **goal:** Runner evidence comes from a disposable Git workspace after check, prompt rendering, command rendering, read-only execution, changed-file report, and no-diff postcondition; otherwise the record selects preflight-only mode.
- **phase:** P1
- **depends_on:** [T3]
<!-- prettier-ignore -->
- **requirements:** [FR-004, FR-005, NFR-008]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/runner_capture.py` (create), `tests/video/test_runner_capture.py` (create), `media/repository-explainer/captures/manifest.json` (modify)
- **acceptance:** a successful fixture run records every preflight and a clean postcondition before permitting an accepted outcome (TC-T4-001); nonzero execution, changed files, hook failure, or absent provider selects `preflight-only` and never records fabricated acceptance (TC-T4-002); workspace and logs contain no credential fields or values (TC-T4-003).
- **sub-tasks:**
  - **T4.1 RED** — add disposable-repository tests with a fake runner; expected failure: no guarded runner-capture state machine exists.
  - **T4.2 Verify RED** — run `uv run pytest tests/video/test_runner_capture.py -x`; confirm the missing state machine causes failure.
  - **T4.3 GREEN** — implement ordered preflights, isolated run directory, changed-file detection, outcome selection, and cleanup.
  - **T4.4 Verify GREEN** — run runner-capture tests and the existing `tests/test_runner_operational.py`.
  - **T4.5 REFACTOR** — make state transitions explicit and typed; retain the capture layer as the only subprocess recorder.
  - **T4.6 Verify Task** — run T3–T4 plus existing runner tests and static checks; commit with IDs.

## Phase P2: Picture and Sound

### T5: Compose Conference-Safe SVG Scenes

- **goal:** The six scene renderers create deterministic 1920×1080 SVG panels from validated pseudocode, real captured evidence, and tracked theme data.
- **phase:** P2
- **depends_on:** [T2, T3, T4]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-003, FR-010, NFR-003, NFR-004, NFR-006]
- **priority:** must
- **files:** `media/repository-explainer/workflow.apseudo` (create), `media/repository-explainer/theme.json` (create), `media/repository-explainer/video_pipeline/scenes.py` (create), `media/repository-explainer/assets/` (create), `tests/video/test_scenes.py` (create), `tests/video/test_content.py` (create)
- **acceptance:** each scene has a stable SVG digest for fixed inputs and uses only referenced source/evidence text (TC-T5-001); code is at least 32 px, captions reserve at least 44 px, contrast is at least 4.5:1, and essential elements stay title-safe (TC-T5-002); the workflow formats and lints cleanly while the teaching defect remains clearly labeled (TC-T5-003).
- **sub-tasks:**
  - **T5.1 RED** — add scene provenance, geometry, contrast, disclosure, and pseudocode-content tests; expected failure: no renderer, theme, or hero workflow exists.
  - **T5.2 Verify RED** — run `uv run pytest tests/video/test_scenes.py tests/video/test_content.py -x`; confirm missing scene behavior causes failure.
  - **T5.3 GREEN** — implement minimal XML-safe SVG primitives and six scene builders; add the theme, hero workflow, and brand assets.
  - **T5.4 Verify GREEN** — run scene/content tests, then `uv run apseudo-format --check media/repository-explainer/workflow.apseudo` before `uv run apseudo-lint media/repository-explainer/workflow.apseudo`.
  - **T5.5 REFACTOR** — consolidate layout primitives only where scenes share semantics; keep scene-specific narrative code separate.
  - **T5.6 Verify Task** — run T2–T5 tests, pseudocode checks, SVG decode smoke test through FFmpeg, and static checks; commit with IDs.

### T6: Generate Bounded `marin` Narration

- **goal:** The speech adapter sends only approved narration text and delivery instructions to the Speech endpoint, writes validated WAV segments, and records bounded retry and estimated-spend metadata without exposing the key.
- **phase:** P2
- **depends_on:** [T2]
<!-- prettier-ignore -->
- **requirements:** [FR-006, NFR-007, NFR-008, NFR-009]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/speech.py` (create), `tests/video/test_speech.py` (create)
- **acceptance:** the request is `POST /v1/audio/speech` with `gpt-4o-mini-tts`, `marin`, WAV format, approved segment text, and calm technical instructions (TC-T6-001); transient retry uses bounded exponential backoff while auth, policy, malformed audio, and projected over-budget errors fail immediately (TC-T6-002); logs and manifests contain no authorization value (TC-T6-003).
- **sub-tasks:**
  - **T6.1 RED** — add local HTTP-server contract tests and synthetic WAV validation; expected failure: the speech client and spend guard do not exist.
  - **T6.2 Verify RED** — run `uv run pytest tests/video/test_speech.py -x`; confirm missing speech behavior causes failure without network access.
  - **T6.3 GREEN** — implement the standard-library HTTPS request, response validation, retry policy, atomic WAV write, and secret-free take manifest.
  - **T6.4 Verify GREEN** — run speech tests and a dry-run that prints only model, voice, segment count, and projected bound.
  - **T6.5 REFACTOR** — isolate transport injection and WAV probing so tests do not patch implementation internals.
  - **T6.6 Verify Task** — run T2 and T6 tests, static checks, and a dry-run secret scan; commit with IDs.

### T7: Render Narrated and Speaker Timelines

- **goal:** One frame-based render graph produces equivalent-picture narrated and speaker MP4s, burns captions, synthesizes the licensed-safe tonal bed, and supports bounded scene replacement.
- **phase:** P2
- **depends_on:** [T5, T6]
<!-- prettier-ignore -->
- **requirements:** [FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005, NFR-007]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/render.py` (create), `tests/video/test_render.py` (create)
- **acceptance:** fixture renders produce 1920×1080, 30 fps H.264/AAC files with matching video-frame counts and speech only in the narrated variant (TC-T7-001); captions are burned from the generated SRT and the audio graph applies loudness/peak targets (TC-T7-002); rendering one scene invalidates only that scene clip and dependent concatenations (TC-T7-003).
- **sub-tasks:**
  - **T7.1 RED** — add FFmpeg-command contract tests and a short real fixture render; expected failure: no render graph or encoder-capability selector exists.
  - **T7.2 Verify RED** — run `uv run pytest tests/video/test_render.py -x`; confirm missing render behavior causes failure, not an absent fixture tool.
  - **T7.3 GREEN** — implement capability probing, SVG scene clips, deterministic concat, caption burn-in, tonal bed, narration mix, and both export variants.
  - **T7.4 Verify GREEN** — run render tests and inspect the fixture with FFprobe; compare narrated/speaker video stream hashes after metadata removal.
  - **T7.5 REFACTOR** — separate pure command construction from subprocess execution and cache decisions.
  - **T7.6 Verify Task** — run T5–T7 tests, real fixture render/probe, and static checks; commit with IDs.

## Phase P3: Verification and Orchestration

### T8: Verify Media, Authenticity, and Security

- **goal:** A single verification report fails promotion unless media streams, duration, loudness, captions, safe layout, provenance, secret scans, and reproducibility evidence satisfy the specification.
- **phase:** P3
- **depends_on:** [T7]
<!-- prettier-ignore -->
- **requirements:** [FR-010, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/verify.py` (create), `tests/video/test_verify.py` (create)
- **acceptance:** probe and EBU R128 parsers produce explicit passing rows for format, duration, streams, loudness, and peak (TC-T8-001); altered evidence, caption omissions, unsafe scene metrics, speech in the speaker cut, or credential-like content blocks promotion (TC-T8-002); checksum and semantic manifests exclude nondeterministic container metadata (TC-T8-003).
- **sub-tasks:**
  - **T8.1 RED** — add parser, aggregate-report, tampering, redaction, and semantic-comparison tests; expected failure: no verifier exists.
  - **T8.2 Verify RED** — run `uv run pytest tests/video/test_verify.py -x`; confirm the missing verification behavior causes failure.
  - **T8.3 GREEN** — implement probe/loudness parsing, Must-gate aggregation, provenance/hash comparison, caption/theme checks, secret scanning, and checksum output.
  - **T8.4 Verify GREEN** — run verifier tests against passing and deliberately corrupted fixture outputs.
  - **T8.5 REFACTOR** — give every gate a stable ID and structured evidence payload; avoid ambiguous Boolean-only failures.
  - **T8.6 Verify Task** — run T7–T8 tests, real fixture verification, and static checks; commit with IDs.

### T9: Expose the Reproducible Production CLI

- **goal:** A stage-oriented CLI performs capability checks, capture, narration, rendering, verification, and full production with dry-run and explicit output roots, while never accepting unresolved paths or printing secrets.
- **phase:** P3
- **depends_on:** [T3, T4, T6, T7, T8]
<!-- prettier-ignore -->
- **requirements:** [FR-009, NFR-005, NFR-008]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/cli.py` (create), `media/repository-explainer/video_pipeline/__main__.py` (create), `media/repository-explainer/README.md` (create), `tests/video/test_cli.py` (create)
- **acceptance:** `check`, `capture`, `narrate`, `render`, `verify`, and `all` subcommands use the same manifest and return stable exit codes (TC-T9-001); `--dry-run` emits redacted argument vectors and planned outputs without writes or network (TC-T9-002); a clean fixture `all` run is reproducible and a failed stage prevents promotion (TC-T9-003).
- **sub-tasks:**
  - **T9.1 RED** — add subprocess CLI contract, dry-run, failure propagation, and fixture e2e tests; expected failure: no production entry point exists.
  - **T9.2 Verify RED** — run `uv run pytest tests/video/test_cli.py -x`; confirm the missing entry point causes failure.
  - **T9.3 GREEN** — implement argparse commands, shared context, atomic stage directories, stable exit codes, and concise documentation.
  - **T9.4 Verify GREEN** — run CLI tests and one real short fixture `all` run.
  - **T9.5 REFACTOR** — keep orchestration in the CLI and domain behavior in existing modules; remove duplicate validation.
  - **T9.6 Verify Task** — run all `tests/video`, static checks, `--help`, `check`, and dry-run commands; commit with IDs.

## Phase P4: Production and Delivery

### T10: Lock Approved Content and Real Captures

- **goal:** The committed production source contains the final six-scene copy, valid hero workflow, current diagnostics, real command evidence, truthful runner mode, disclosure, and conference-safe graphics at one named revision.
- **phase:** P4
- **depends_on:** [T5, T9]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-005, FR-008, FR-010, NFR-003, NFR-004, NFR-006, NFR-008]
- **priority:** must
- **files:** `media/repository-explainer/project.json` (modify), `media/repository-explainer/narration.json` (modify), `media/repository-explainer/captions.srt` (modify), `media/repository-explainer/workflow.apseudo` (modify), `media/repository-explainer/theme.json` (modify), `media/repository-explainer/assets/` (modify), `media/repository-explainer/captures/` (modify), `tests/video/test_content.py` (modify)
- **acceptance:** content tests bind all six scenes to approved copy and current evidence at the capture revision (TC-T10-001); formatter/linter/rule/Mermaid and runner records reproduce with recorded statuses and hashes (TC-T10-002); representative SVGs contain no unapproved text, credential-like content, or unsafe layout (TC-T10-003).
- **sub-tasks:**
  - **T10.1 RED** — tighten content tests to the approved scene/source ledger; expected failure: placeholder fixture content and captures do not satisfy the final ledger.
  - **T10.2 Verify RED** — run `uv run pytest tests/video/test_content.py -x`; confirm final content/evidence absence causes failure.
  - **T10.3 GREEN** — author final copy and visuals, validate the workflow, run real capture commands, review outputs, and promote only named evidence.
  - **T10.4 Verify GREEN** — run content/capture tests, then formatter check before linter, rule explanation, Mermaid generation, and guarded runner capture at the recorded revision.
  - **T10.5 REFACTOR** — remove redundant copy and unused capture candidates; keep the ledger as the only scene-to-evidence mapping.
  - **T10.6 Verify Task** — run all video tests, pseudocode tools, capture reproduction, SVG decode, secret scan, and static checks; commit with IDs.

### T11: Generate Narration and Both Final Candidates

- **goal:** A bounded live production run generates reviewed `marin` stems and both full-resolution candidate exports from the locked source.
- **phase:** P4
- **depends_on:** [T10]
<!-- prettier-ignore -->
- **requirements:** [FR-006, FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005, NFR-007, NFR-009]
- **priority:** must
- **files:** `dist/video/candidate/` (generated, ignored), `.project-pipeline/2026-07-23-repository-explainer-video/logs/` (evidence)
- **acceptance:** the approved dry-run projects spend below USD 1 and lists only Speech requests (TC-T11-001); selected `marin` segments are complete, intelligible, and normalized (TC-T11-002); both candidates render with matching picture timing and pass automated media verification (TC-T11-003).
- **sub-tasks:**
  - **T11.1 RED** — run the full candidate verification before generation; expected failure: required narration stems and MP4 candidates are absent.
  - **T11.2 Verify RED** — confirm only missing production artifacts fail; fix any source, environment, or capability error before spending or rendering.
  - **T11.3 GREEN** — resolve the key into the process environment, run bounded `marin` generation, review takes, and render both candidates.
  - **T11.4 Verify GREEN** — run automated verification, FFprobe, EBU R128, and a full narrated plus mute playback review; regenerate only rejected segments/scenes within the spend cap.
  - **T11.5 REFACTOR** — assess picture/audio changes; record `none` unless a source-level simplification is proven necessary, then rerender.
  - **T11.6 Verify Task** — save command/report evidence in the checklist logs, record spend without credential or billing detail, confirm Git source diff, and commit any reviewed source corrections with IDs.

### T12: Accept and Deliver the Verified Film

- **goal:** Accepted candidates are promoted to stable local filenames with checksums, disclosure, reusable sources, verification evidence, and accurate handoff records.
- **phase:** P4
- **depends_on:** [T11]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-006, FR-007, FR-008, FR-009, FR-010, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-009]
- **priority:** must
- **files:** `dist/video/final/` (generated, ignored), `media/repository-explainer/README.md` (modify), `docs/handoff/specs-plans.md` (modify), `docs/handoff/state.md` (modify), `docs/handoff/deployed.md` (modify)
- **acceptance:** final narrated and speaker files, SRT, reports, and checksum manifest match the verified candidates (TC-T12-001); narrated, muted, and representative-frame owner reviews accept the promise, readability, truth, and disclosure (TC-T12-002); repository source, handoff, and final report contain references only and distinguish local delivery from hosted publication (TC-T12-003).
- **sub-tasks:**
  - **T12.1 RED** — run final verification against `dist/video/final`; expected failure: no promoted delivery package exists.
  - **T12.2 Verify RED** — confirm missing finals are the only failure and the candidate verification remains green.
  - **T12.3 GREEN** — atomically promote accepted candidates, captions, reports, and checksums; update reproduction and handoff documentation.
  - **T12.4 Verify GREEN** — rerun final verification, checksum comparison, secret scan, Markdown checks, handoff checks, and clean-source render proof.
  - **T12.5 REFACTOR** — remove obsolete ignored candidates/intermediates only after final checksums are recorded; preserve reusable committed source.
  - **T12.6 Verify Task** — complete the owner acceptance checklist, run the repository-scoped final gate, commit durable close-out with IDs, and report clickable final paths without publishing externally.

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Error handling | yes | Stable stage errors and failed-promotion tests. | T3, T4, T6–T9 |
| Logging / observability | yes | Capture, take, render, and verification manifests with secret-free logs. | T3, T6, T8, T9 |
| Security | yes | Owned-path checks, no shell, restricted Speech call, secret scans, manual diff. | T3, T4, T6, T8, T12 |
| Performance | yes | Scene cache and bounded replacement; full render completes without retained frame explosion. | T7, T11 |
| Compatibility | yes | Capability probe selects a verified H.264 encoder and rejects missing filters/fonts. | T7, T9 |
| Accessibility | yes | Caption/content tests plus muted owner review. | T2, T5, T12 |
| Authenticity | yes | Revision-bound capture hashes and source-to-scene comparison. | T3, T8, T10 |
| Documentation | yes | Reproduction README and local-delivery handoff validation. | T9, T12 |

## 10. Integration and Migration

### 10.1 Integration Sequence

1. Establish strict manifests and caption compilation.
2. Capture normal repository evidence and guarded runner evidence.
3. Compose SVG scenes and implement the bounded Speech adapter.
4. Render both timelines, then add aggregate verification.
5. Expose the stage CLI and prove a fixture end-to-end run.
6. Lock final source/evidence, generate live narration, render candidates, and promote only after every Must gate passes.

### 10.2 Data or State Migration

- **Required:** no · **Rollback supported:** yes · **Idempotent:** yes
- No existing data is migrated. Rollback restores the last verified committed production source and rerenders ignored outputs. Evidence promotion is explicit and additive until its owning task commits.

### 10.3 Compatibility Plan

The production package is not part of the installed wheel or public CLI. Existing `apseudo_lint` behavior and entry points remain unchanged. The only project configuration change makes the local media package visible to tests and static analysis. Generated outputs remain under the already ignored `dist/` root.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Current diagnostics differ from storyboard wording. | medium | medium | Bind scenes to current captures and update copy rather than fake output. | T10 |
| R-002 | Runner cannot produce an accepted read-only result. | medium | low | Render the approved verified-preflight alternate. | T4, T10 |
| R-003 | `marin` pronunciation or pacing misses picture lock. | medium | medium | Segment narration by scene and retry only affected segments within cap. | T6, T11 |
| R-004 | Full render is slow or nondeterministic. | medium | medium | Use integer frames, cached scene clips, fixed metadata, and semantic comparison. | T7, T8 |
| R-005 | Secret material enters logs or media. | low | high | No environment dumps, restricted request logging, scans before promotion, rotation response. | T3, T6, T8, T12 |
| R-006 | Existing unrelated repository gates obscure video status. | high | low | Run and report scoped video gates separately; do not weaken repository policy. | T12 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Keep production code under `media/repository-explainer/`. | It remains reproducible but outside the shipped linter package. | T1–T9 |
| D-002 | Use integer frames as timeline truth. | It avoids floating-point drift across captions, SVGs, and FFmpeg. | T1, T2, T7 |
| D-003 | Generate truthful SVG composites instead of relying on opaque manual editing. | Source/evidence provenance remains reviewable and conference text stays large. | T3, T5, T10 |
| D-004 | Use standard-library HTTPS instead of adding the OpenAI SDK. | The pipeline needs one endpoint and the repository keeps runtime dependencies minimal. | T6 |
| D-005 | Generate a simple tonal bed with FFmpeg. | It avoids untracked licensing obligations and keeps the speaker cut complete. | T7 |
| D-006 | Keep binary delivery artifacts ignored. | Git contains reproducible source and evidence; local delivery retains checksums. | T7, T11, T12 |

## 12. Open Questions

| Question | Blocking? | Owner | Current assumption |
| --- | --- | --- | --- |
| Where should the final MP4 be published after local acceptance? | no | Chris Purcell | Deliver locally; publication is a separate authorized action. |
| Will a venue provide codec, loudness, or safe-area requirements? | no | Chris Purcell | Use `SPEC-NSBJ` NFR-001, NFR-004, and NFR-007. |

## 13. Final Verification

Run at close-out; store verbose evidence in checklist logs.

- `uv run pytest tests/video`
- `uv run pytest`
- `uv run ruff check media/repository-explainer/video_pipeline tests/video`
- `uv run ruff format --check media/repository-explainer/video_pipeline tests/video`
- `uv run basedpyright media/repository-explainer/video_pipeline tests/video`
- `uv run coverage run --source=media/repository-explainer/video_pipeline -m pytest tests/video`
- `uv run coverage report`
- `uv run apseudo-format --check media/repository-explainer/workflow.apseudo`
- `uv run apseudo-lint media/repository-explainer/workflow.apseudo`
- `uv run python -m video_pipeline check`
- `uv run python -m video_pipeline verify --output dist/video/final`
- `npx prettier --check "**/*.md" "**/*.json" "**/*.jsonc" "**/*.yml" "**/*.yaml" "!docs/reference/pre-migration/**" "!package-lock.json"`
- `npx markdownlint-cli2 "**/*.md"`
- Review narrated playback, muted playback, and representative frames from all six scenes.
- Confirm every requirement maps to completed evidence, every task is done or explicitly skipped, no blocker remains, and no publication claim exceeds local delivery.

The known whole-repository Prettier drift in five VS Code extension files and the unrelated existing coverage-floor backlog must be reported accurately if still present; neither may be hidden by weakening configuration.

## 14. Close-Out

- **Completed:** _pending_ · final commit _pending_
- **Deviations / decisions harvested from notes:** _pending close-out_
- **Risks closed / accepted:** _pending close-out_
- **Deferred work filed:** _pending close-out_

At close-out, harvest notes here and to the spec, ADRs, or issues as appropriate; set `status: complete`; update `updated`; commit the master; then remove `.project-pipeline/2026-07-23-repository-explainer-video/`.

## Appendices

### Appendix A. Interface and Data Changes

#### A.1 Public Interfaces

| Interface | Current | Planned | Compatibility |
| --- | --- | --- | --- |
| Installed `apseudo_lint` APIs and CLIs | Existing toolkit surfaces | Unchanged | Fully compatible |
| Local video-production CLI | Absent | `uv run python -m video_pipeline` with stage subcommands | Repository-local; not installed |
| Speech provider | Absent | Restricted `POST /v1/audio/speech` during production | Build-time only |

#### A.2 Data Models

| Model | Fields | Change | Validation | Migration |
| --- | --- | --- | --- | --- |
| Project manifest | delivery, safe area, audio, ordered scenes | add | Strict keys, integer frames, owned paths | none |
| Narration segment | scene, start/end frame, text, direction | add | Ordered, bounded, readable, disclosed | none |
| Capture evidence | command, cwd, revision, status, hashes, promoted path | add | Allowlist, owned paths, secret rejection | none |
| TTS take | segment, model, voice, output hash, retries, cost bound | add | `marin`, WAV probe, budget cap | none |
| Verification report | stable gate IDs, status, evidence paths, checksums | add | Every Must gate represented | none |

### Appendix B. Test Matrix

| Test ID | Requirement | Task | Test path | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | FR-002, NFR-001, NFR-002 | T1 | `tests/video/test_manifest.py::test_loads_approved_six_scene_manifest` | unit |
| TC-T1-002 | NFR-004, NFR-005 | T1 | `tests/video/test_manifest.py::test_rejects_invalid_manifest_invariants` | unit |
| TC-T1-003 | FR-009 | T1 | `tests/video/test_manifest.py::test_rejects_paths_outside_owned_roots` | security |
| TC-T2-001 | FR-001, FR-008, NFR-003 | T2 | `tests/video/test_captions.py::test_compiles_mute_safe_captions` | unit |
| TC-T2-002 | FR-010, NFR-002 | T2 | `tests/video/test_captions.py::test_rejects_invalid_timing_or_missing_disclosure` | regression |
| TC-T2-003 | FR-009, NFR-005 | T2 | `tests/video/test_captions.py::test_srt_compilation_is_deterministic` | unit |
| TC-T3-001 | FR-004 | T3 | `tests/video/test_capture.py::test_records_revision_bound_command_evidence` | integration |
| TC-T3-002 | NFR-008 | T3 | `tests/video/test_capture.py::test_rejects_unsafe_command_path_or_output` | security |
| TC-T3-003 | NFR-006 | T3 | `tests/video/test_capture.py::test_promotes_only_reviewed_exact_bytes` | regression |
| TC-T4-001 | FR-004, FR-005 | T4 | `tests/video/test_runner_capture.py::test_accepts_only_clean_guarded_run` | integration |
| TC-T4-002 | FR-005 | T4 | `tests/video/test_runner_capture.py::test_falls_back_to_verified_preflight` | regression |
| TC-T4-003 | NFR-008 | T4 | `tests/video/test_runner_capture.py::test_runner_record_excludes_credentials` | security |
| TC-T5-001 | FR-001, FR-002, NFR-006 | T5 | `tests/video/test_scenes.py::test_scenes_are_deterministic_and_provenanced` | unit |
| TC-T5-002 | NFR-003, NFR-004 | T5 | `tests/video/test_scenes.py::test_scene_geometry_and_contrast_are_safe` | unit |
| TC-T5-003 | FR-003, FR-010 | T5 | `tests/video/test_content.py::test_workflow_and_disclosure_are_valid` | content |
| TC-T6-001 | FR-006 | T6 | `tests/video/test_speech.py::test_builds_approved_speech_request` | contract |
| TC-T6-002 | NFR-007, NFR-009 | T6 | `tests/video/test_speech.py::test_retries_transient_only_within_budget` | unit |
| TC-T6-003 | NFR-008 | T6 | `tests/video/test_speech.py::test_take_manifest_and_logs_exclude_key` | security |
| TC-T7-001 | FR-007, NFR-001, NFR-002 | T7 | `tests/video/test_render.py::test_renders_matching_picture_variants` | integration |
| TC-T7-002 | FR-008, NFR-007 | T7 | `tests/video/test_render.py::test_burns_captions_and_builds_audio_graph` | contract |
| TC-T7-003 | FR-009, NFR-005 | T7 | `tests/video/test_render.py::test_rebuilds_only_changed_scene` | regression |
| TC-T8-001 | NFR-001, NFR-002, NFR-007 | T8 | `tests/video/test_verify.py::test_reports_passing_media_and_loudness` | integration |
| TC-T8-002 | FR-010, NFR-003, NFR-004, NFR-006, NFR-008 | T8 | `tests/video/test_verify.py::test_blocks_any_failed_must_gate` | regression |
| TC-T8-003 | NFR-005 | T8 | `tests/video/test_verify.py::test_semantic_comparison_ignores_only_metadata` | unit |
| TC-T9-001 | FR-009 | T9 | `tests/video/test_cli.py::test_stage_commands_share_manifest_and_exit_codes` | contract |
| TC-T9-002 | NFR-008 | T9 | `tests/video/test_cli.py::test_dry_run_is_write_free_and_redacted` | security |
| TC-T9-003 | NFR-005 | T9 | `tests/video/test_cli.py::test_fixture_all_run_is_reproducible` | end-to-end |
| TC-T10-001 | FR-001, FR-002, FR-003, FR-008, FR-010 | T10 | `tests/video/test_content.py::test_final_scene_source_ledger` | content |
| TC-T10-002 | FR-004, FR-005, NFR-006 | T10 | `tests/video/test_content.py::test_final_evidence_reproduces` | integration |
| TC-T10-003 | NFR-003, NFR-004, NFR-008 | T10 | `tests/video/test_content.py::test_final_scene_assets_are_safe` | content |
| TC-T11-001 | NFR-009 | T11 | `video_pipeline all --dry-run` evidence | operational |
| TC-T11-002 | FR-006, NFR-007 | T11 | narration review and WAV probe evidence | operational |
| TC-T11-003 | FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005 | T11 | candidate verification report | end-to-end |
| TC-T12-001 | FR-006, FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005, NFR-007 | T12 | final verification and checksum report | end-to-end |
| TC-T12-002 | FR-001, FR-002, FR-010, NFR-003, NFR-004, NFR-006 | T12 | owner playback and frame review | acceptance |
| TC-T12-003 | NFR-008, NFR-009 | T12 | secret/cost/delivery-scope review | security |

### Appendix C. Deferred Work

| Item | Reason deferred | Follow-up |
| --- | --- | --- |
| Hosted publication | Requires a separate destination and authorization decision. | Reopen `SPEC-NSBJ` OQ-001 after local acceptance. |
| Venue-specific transcode | No venue delivery profile has been supplied. | Reopen `SPEC-NSBJ` OQ-002 when requirements arrive. |
| Social aspect ratios and translations | Outside the approved conference v1. | Track only after a named channel or audience exists. |
