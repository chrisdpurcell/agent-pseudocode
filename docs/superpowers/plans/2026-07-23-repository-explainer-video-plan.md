---
title: 'Repository Explainer Video Implementation Plan'
slug: 'repository-explainer-video'
size: full
status: complete
source: 'docs/specs/repository-explainer-video.md (SPEC-NSBJ)'
spec_ref: 'docs/specs/repository-explainer-video.md'
created: 2026-07-23
updated: 2026-07-24
owners:
  - 'Chris Purcell'
  - 'Codex, supervised by the owner'
test_framework: pytest
---

# Repository Explainer Video Implementation Plan

**For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task by task.

> **This file is definition, not state.** It is read-only during implementation except when appending discovered work or harvesting close-out facts. Live progress belongs in the generated per-phase checklists under `.project-pipeline/2026-07-23-repository-explainer-video/`.

## 1. Objective

Build and deliver a polished 4050-frame (135-second), 1920×1080, 30 fps repository demo with truthful Pythonic Agent Pseudocode captures, OpenAI `marin` narration, burned-in narration captions, a same-picture narration-free speaker cut, a procedural tonal bed, basic media checks, and checksummed local delivery files.

## 2. Background

`SPEC-NSBJ` revision 0.5 defines a six-scene quick demo that makes agent behavior visible, verifiable, and executable. The owner explicitly recalibrated the work away from release-grade media assurance on `2026-07-24`. Tasks T8–T12 are therefore superseded for execution by T13–T15; their prior commits remain historical implementation evidence, not acceptance gates.

The pipeline treats repository output as evidence rather than decorative copy. Visuals may recompose genuine source and command output for conference legibility, but may not change their semantics. OpenBao owns the Speech API credential; generated intermediates and delivery media remain ignored.

## 3. Scope

### 3.1 In Scope

- A typed, validated project and evidence-manifest model.
- One source of truth for narration segments, fixed scene budgets, and caption timing.
- Reproducible capture of formatter, linter, rule, Mermaid, and runner evidence.
- Deterministic hybrid scene composition using real editor pixels, repository source, captured output, and SVG annotations.
- A restricted, retry-bounded OpenAI Speech adapter for `marin`, with an explicit provider-unavailable outcome.
- FFmpeg assembly of narrated and speaker exports from one 4050-frame timeline, including a procedural tonal bed.
- Basic FFprobe, per-variant EBU R128, caption, disclosure, targeted source/log, and checksum verification.
- The six approved scenes, production sources, reviewed captures, selected narration WAV, final local exports, `delivery.json`, asset provenance, and close-out documentation.

### 3.2 Out of Scope

- Modifying Pythonic Agent Pseudocode behavior to make filming easier.
- Publishing the MP4 to GitHub or another hosting service.
- Tracking generated WAV, MP4, frame sequences, or provider responses in Git.
- Alternate aspect ratios, translated narration, or human voice recording.
- A general-purpose video editor or public media-production API.
- Repairing the repository's unrelated existing coverage-floor backlog.
- Hermetic reproduction, decoded-stream equivalence, adversarial promotion gates, per-glyph pixel forensics, exhaustive dependency provenance, and rollback rehearsals.

### 3.3 Assumptions

- FFmpeg 8 with `librsvg`, `drawtext`, `subtitles`, `ebur128`, AAC, and an H.264 encoder remains available; capability checks fail early if the environment changes.
- Noto Sans and Noto Sans Mono remain available on the production workstation; missing fonts block rendering rather than silently substituting metrics.
- A real read-only runner result is shown only if its preserved post-checks pass; otherwise the approved preflight-only alternate scene is rendered.
- Venue-specific delivery requirements remain unknown, so the specification's codec, loudness, and title-safe contract is authoritative.
- The approved model, `marin` voice, WAV output, and narrowest available Speech-permitting Restricted-key bundle are reverified before paid generation; if any is unavailable, the speaker cut may be retained only as an interim artifact and v1 remains incomplete pending owner approval.
- The reference editor capture uses VS Code 1.130.0 and Spectacle 6.7.3 on a single 1920×1080 monitor. If those exact versions or the recorded capture settings are unavailable, editor recapture blocks content lock rather than silently changing the visual substrate.

### 3.4 Constraints

- Use Python 3.14, the standard library, uv, pytest, Ruff, and BasedPyright strict.
- Keep the production package under `media/repository-explainer/`; do not add it to the distributed `apseudo_lint` wheel.
- Use real tracked source or captured command output for every claimed interaction.
- Store only the OpenBao credential reference; never print, persist, capture, or scan the credential value into evidence.
- Use the narrowest available Restricted-key permission that permits Speech requests; set every separately configurable management, files, fine-tuning, assistants, and administration permission to None, record any provider-bundled model capability, and call only `/v1/audio/speech`.
- Validate changed pseudocode with formatter check before linter.
- Use generated checklists for progress; do not put routine state in this master.

## 4. Source Requirements

| ID | Requirement | Source | Priority | Task(s) |
| --- | --- | --- | --- | --- |
| FR-001 | Communicate that behavior can be read, understood, validated, and run. | `SPEC-NSBJ` §7.1 | must | T2, T5, T10, T12 |
| FR-002 | Preserve the approved six-scene order. | `SPEC-NSBJ` §7.1 | must | T1, T5, T10, T12 |
| FR-003 | Feature `docs/apseudo-docs/examples/review-loop.apseudo` as the recurring validated workflow. | `SPEC-NSBJ` §7.1 | must | T5, T10 |
| FR-004 | Trace each real interaction to a command and named Git revision. | `SPEC-NSBJ` §7.1 | must | T3, T4, T10 |
| FR-005 | Show runner success only after the exact bounded Codex preflights, read-only run, hooks, and no-diff post-checks. | `SPEC-NSBJ` §7.1 | must | T4, T10 |
| FR-006 | Produce the narrated master with OpenAI `marin` inside fixed scene budgets or record the owner-gated blocked outcome. | `SPEC-NSBJ` §7.1 | must | T2, T6, T11, T12 |
| FR-007 | Produce a same-picture 4050-frame speaker cut without narration or narration transcript. | `SPEC-NSBJ` §7.1 | must | T7, T11, T12 |
| FR-008 | Burn narration captions into the narrated master, retain reusable caption source, and keep both variants mute-safe. | `SPEC-NSBJ` §7.1 | must | T2, T7, T11, T12 |
| FR-009 | Reproduce the speaker cut from a clean checkout and the narrated master from that checkout plus the selected checksummed WAV. | `SPEC-NSBJ` §7.1 | must | T1, T7, T9, T11 |
| FR-010 | Disclose AI-generated narration on the end card and in `delivery.json`. | `SPEC-NSBJ` §7.1 | must | T2, T5, T8, T10, T12 |
| FR-011 | Generate the non-speech tonal bed and cues procedurally with recorded synthesis parameters. | `SPEC-NSBJ` §7.1 | must | T7, T8, T12 |
| NFR-001 | Deliver both variants as 1920×1080, 30 fps H.264/AAC MP4. | `SPEC-NSBJ` §7.2 | must | T1, T7, T8, T11 |
| NFR-002 | Keep both variants at exactly 4050 frames and 135 seconds, with no audio outside program or scene budgets. | `SPEC-NSBJ` §7.2 | must | T1, T2, T7, T8 |
| NFR-003 | Preserve the complete story without audio in each variant. | `SPEC-NSBJ` §7.2 | must | T2, T5, T10, T12 |
| NFR-004 | Enforce final-frame text size, central-90% title safety, and contrast at every required state. | `SPEC-NSBJ` §7.2 | must | T1, T5, T8, T10 |
| NFR-005 | Reproduce equivalent streams from approved source plus the selected local narration input without another provider call. | `SPEC-NSBJ` §7.2 | must | T1, T7, T8, T9, T11 |
| NFR-006 | Preserve source and output semantics in composites. | `SPEC-NSBJ` §7.2 | must | T3, T5, T8, T10 |
| NFR-007 | Meet the separate −16 LUFS narrated and −28 LUFS speaker-cut loudness and true-peak limits. | `SPEC-NSBJ` §7.2 | must | T6, T7, T8, T11 |
| NFR-008 | Keep credentials out of source, logs, and media. | `SPEC-NSBJ` §7.2 | must | T3, T4, T6, T8, T9, T12 |
| NFR-009 | Keep non-itemized attributable TTS spend under USD 1 unless re-approved. | `SPEC-NSBJ` §7.2 | should | T6, T11, T12 |
| NFR-010 | Block delivery unless every non-repository font, graphic, and audio input has open, procedural, or retained license provenance. | `SPEC-NSBJ` §7.2 | must | T5, T8, T10, T12 |
| C-001 | Make the film work for developers evaluating the toolkit during a conference presentation. | `SPEC-NSBJ` §3.4 | must | T5, T8, T10, T12 |
| C-002 | Combine “readable and executable” with “complex behavior made understandable.” | `SPEC-NSBJ` §3.4 | must | T2, T5, T10, T12 |
| C-003 | Keep real tracked source or captured tool output dominant for 60%–80% of timeline frames. | `SPEC-NSBJ` §3.4 | must | T1, T5, T8, T10 |
| C-004 | Use `gpt-4o-mini-tts`, `marin`, and calm, precise technical delivery unless the owner approves an AW-004 substitute. | `SPEC-NSBJ` §3.4 | must | T2, T6, T11, T12 |
| C-005 | Keep credential values out of source and output. | `SPEC-NSBJ` §3.4 | must | T3, T4, T6, T8, T9, T12 |
| C-006 | Validate displayed pseudocode with repository tooling except for the explicitly labeled teaching defect. | `SPEC-NSBJ` §3.4 | must | T3, T4, T5, T10 |
| C-007 | Keep total attributable TTS generation below USD 1 unless the owner re-approves spend. | `SPEC-NSBJ` §3.4 | must | T6, T11, T12 |
| C-008 | Disclose AI-generated narration. | `SPEC-NSBJ` §3.4 | must | T2, T5, T8, T10, T12 |
| C-009 | Include production Python in pytest, Ruff, BasedPyright strict, and targeted coverage. | `SPEC-NSBJ` §3.4 | must | T1, T9, T12 |
| IR-001 | Read tracked repository source and output without modifying product behavior. | `SPEC-NSBJ` §7.3 | must | T3, T10 |
| IR-002 | Validate the Restricted key, then limit production calls to approved Speech requests. | `SPEC-NSBJ` §7.3 | must | T6, T11 |
| IR-003 | Render and inspect delivery media through FFmpeg and FFprobe. | `SPEC-NSBJ` §7.3 | must | T7, T8, T11 |
| IR-004 | Use exact bounded `apseudo-run` preflights and a disposable clone for the execution scene. | `SPEC-NSBJ` §7.3 | must | T4, T10 |
| IR-005 | Emit the stable delivery filenames and complete inventory. | `SPEC-NSBJ` §7.3 | must | T12 |
| DR-001 | Retain provenance for every real interaction in the capture manifest. | `SPEC-NSBJ` §7.4 | must | T1, T3, T9, T12 |
| DR-002 | Retain the approved narration package and selected checksummed WAV. | `SPEC-NSBJ` §7.4 | must | T2, T6, T11, T12 |
| DR-003 | Retain a render manifest covering scene order, timing, toolchain, input assets, and exports. | `SPEC-NSBJ` §7.4 | must | T1, T7, T8, T12 |
| DR-004 | Isolate all transient production data below `dist/video/work/`. | `SPEC-NSBJ` §7.4 | must | T4, T6, T7, T9 |
| DR-005 | Retain asset provenance for fonts, graphics, and audio. | `SPEC-NSBJ` §7.4 | must | T5, T8, T10, T12 |

## 5. Repository and Architecture Context

### 5.1 Relevant Components

| Component | Purpose | Paths |
| --- | --- | --- |
| Product CLI | Produces genuine formatter, linter, rule, Mermaid, and runner evidence. | `src/apseudo_lint/`, `scripts/apseudo-*` |
| Example source | Supplies the hero workflow, teaching defect, and runner task. | `docs/apseudo-docs/examples/`, `tests/fixtures/invalid/` |
| Video source | Owns project data, production package, editor capture, SVG assets, script, and evidence. | `media/repository-explainer/` |
| Generated delivery | Holds untracked intermediates, WAV stems, candidates, reports, and finals. | `dist/video/` |
| Production tests | Prove manifest, capture, speech, render, verification, and CLI behavior. | `tests/video/` |
| Handoff | Records approved spec, active plan, credential reference, and delivery state. | `docs/handoff/` |

### 5.2 Existing Behavior

The repository has no current video source or renderer. `uv run apseudo-format`, `uv run apseudo-lint`, `uv run apseudo-explain`, `uv run apseudo-mermaid`, and `uv run apseudo-run` provide the truthful product surfaces. FFmpeg, FFprobe, Noto fonts, SVG decoding, AAC, and H.264 encoding are available on the reference workstation. The existing Python test suite is rooted at `tests/`, and strict static checking currently covers `src` and `tests`.

### 5.3 Files Expected to Change

| Path | Action | Purpose | Owning task |
| --- | --- | --- | --- |
| `pyproject.toml` | modify | Add `media/repository-explainer` to pytest `pythonpath`, Ruff `src`, and BasedPyright `extraPaths`; add the production package to BasedPyright `include` without adding it to the build-backend module list. | T1 |
| `media/repository-explainer/project.json` | create | Six-scene timeline, delivery, title-safe, and audio configuration. | T1 |
| `media/repository-explainer/video_pipeline/models.py` | create | Typed immutable manifest records. | T1 |
| `media/repository-explainer/video_pipeline/manifest.py` | create | Load and validate project, narration, capture, and delivery manifests. | T1 |
| `media/repository-explainer/narration.json` | create | Narration and caption source of truth. | T2 |
| `media/repository-explainer/captions.srt` | create | Reusable generated caption delivery source. | T2 |
| `media/repository-explainer/video_pipeline/captions.py` | create | Validate segments and render SRT deterministically. | T2 |
| `media/repository-explainer/video_pipeline/capture.py` | create | Execute allowlisted commands and record evidence. | T3 |
| `media/repository-explainer/captures/manifest.json` | create | Reviewed mapping from scenes to real commands and revision. | T3, T10 |
| `media/repository-explainer/captures/evidence/` | create | Promoted text/JSON evidence safe for composition. | T3, T10 |
| `media/repository-explainer/captures/evidence/editor/` | create | Real editor capture sequence of the pinned hero workflow, revision-, line-range-, and viewport-bound in the capture manifest. | T3, T5, T10 |
| `media/repository-explainer/captures/evidence/runner/` | create | Selected secret-free hook, argv, run-record, post-check, changed-file, and outcome evidence promoted before disposable-clone cleanup. | T4, T10 |
| `media/repository-explainer/video_pipeline/runner_capture.py` | create | Disposable-worktree runner preflight, execution, and no-diff proof. | T4 |
| `media/repository-explainer/theme.json` | create | Colors, type sizes, safe area, and transition constants. | T5 |
| `media/repository-explainer/video_pipeline/scenes.py` | create | Render truthful scene SVGs from source and evidence. | T5 |
| `media/repository-explainer/assets/` | create | Tracked brand and scene-source SVGs. | T5, T10 |
| `media/repository-explainer/asset-provenance.json` | create | Source, license or generation method, and checksum for every non-repository asset. | T5, T8, T10 |
| `media/repository-explainer/video_pipeline/speech.py` | create | Restricted Speech request, retry, WAV, and spend manifest. | T6 |
| `media/repository-explainer/video_pipeline/render.py` | create | Build scene clips and both FFmpeg timelines. | T7 |
| `dist/video/candidate/render-manifest.json` | generate, ignored | Revision, toolchain, inputs, timing, synthesis, and candidate checksums. | T7, T8, T11 |
| `media/repository-explainer/video_pipeline/verify.py` | create | Probe, loudness, caption, authenticity, secret, and checksum gates. | T8 |
| `media/repository-explainer/video_pipeline/cli.py` | create | Stage-oriented `capture`, `permission-smoke`, `narrate`, `render`, `verify`, and `all` CLI. | T9 |
| `media/repository-explainer/video_pipeline/__main__.py` | create | Module entry point. | T9 |
| `media/repository-explainer/README.md` | create | Reproduction, credential, output, and verification instructions. | T9, T12 |
| `media/repository-explainer/production-evidence.json` | create | Durable, secret-free provider smoke, permission, spend-bound, render, and delivery evidence summary. | T6, T11, T12 |
| `dist/video/final/delivery.json` | generate, ignored | Checksummed delivery inventory and AI-narration disclosure. | T12 |
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
| VS Code | external | Exact reference version 1.130.0 | Real editor interaction and syntax-highlighted source capture. |
| Spectacle | external | Exact reference version 6.7.3 | Deterministic current-monitor PNG capture through `spectacle --current --background --nonotify --output PATH`. |
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
  - Video coverage diagnostic: `COVERAGE_FILE=.coverage.video uv run coverage run --source=media/repository-explainer/video_pipeline -m pytest tests/video`
  - Video coverage report: `COVERAGE_FILE=.coverage.video uv run coverage report --fail-under=0`
  - Aggregate coverage gate: `uv run coverage run -m pytest && uv run coverage report`
- **Acceptance:** Test Cases in Appendix B must pass. `pyproject.toml` must make the non-wheel production package and `tests/video/` visible to pytest, Ruff, BasedPyright strict, and the targeted coverage command. The isolated `.coverage.video` report is a diagnostic and does not overwrite aggregate coverage data. The repository's existing 85% aggregate floor remains authoritative, and no new coverage-floor setting is introduced.

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
| T1 | Define and validate the project manifest | P1 | None | FR-002, FR-009, NFR-001, NFR-002, NFR-004, NFR-005, C-003, C-009, DR-001, DR-003 | `uv run pytest tests/video/test_manifest.py` |
| T2 | Compile narration and captions from one source | P1 | T1 | FR-001, FR-006, FR-008, FR-010, NFR-002, NFR-003, C-002, C-004, C-008, DR-002 | `uv run pytest tests/video/test_captions.py` |
| T3 | Capture truthful command and editor evidence | P1 | T1 | FR-004, NFR-006, NFR-008, C-005, C-006, IR-001, DR-001 | `uv run pytest tests/video/test_capture.py` |
| T4 | Capture guarded runner evidence | P1 | T3 | FR-004, FR-005, NFR-008, C-005, C-006, IR-004, DR-004 | `uv run pytest tests/video/test_runner_capture.py` |
| T5 | Compose conference-safe hybrid scenes | P2 | T2, T3, T4 | FR-001–FR-003, FR-010, NFR-003, NFR-004, NFR-006, NFR-010, C-001–C-003, C-006, C-008, DR-005 | `uv run pytest tests/video/test_scenes.py tests/video/test_content.py` |
| T6 | Generate bounded `marin` narration | P2 | T2 | FR-006, NFR-007–NFR-009, C-004, C-005, C-007, IR-002, DR-002, DR-004 | `uv run pytest tests/video/test_speech.py` |
| T7 | Render narrated and speaker timelines | P2 | T5, T6 | FR-007–FR-009, FR-011, NFR-001, NFR-002, NFR-005, NFR-007, IR-003, DR-003, DR-004 | `uv run pytest tests/video/test_render.py` |
| T8 | Verify media, authenticity, rights, and security | P3 | T7 | FR-010, FR-011, NFR-001–NFR-008, NFR-010, C-001, C-003, C-005, C-008, IR-003, DR-003, DR-005 | `uv run pytest tests/video/test_verify.py` |
| T9 | Expose the reproducible production CLI | P3 | T3, T4, T6, T7, T8 | FR-009, NFR-005, NFR-008, C-005, C-009, DR-001, DR-004 | `uv run pytest tests/video/test_cli.py` |
| T10 | Lock approved content and real captures | P4 | T5, T9 | FR-001–FR-005, FR-008, FR-010, NFR-003, NFR-004, NFR-006, NFR-008, NFR-010, C-001–C-003, C-006, C-008, IR-001, IR-004, DR-005 | `uv run pytest tests/video/test_content.py` |
| T11 | Generate narration and both final candidates | P4 | T10 | FR-006–FR-009, NFR-001, NFR-002, NFR-005, NFR-007, NFR-009, C-004, C-007, IR-002, IR-003, DR-002 | `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline all --output ../../dist/video/candidate` |
| T12 | Accept and deliver the verified film | P4 | T11 | FR-001, FR-002, FR-006–FR-011, NFR-001–NFR-010, C-001, C-002, C-004–C-005, C-007–C-009, IR-005, DR-001–DR-003, DR-005 | `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline verify --output ../../dist/video/final` |
| T13 | Add quick-demo verification and CLI beside dormant strict assurance | P5 | T7 | FR-009, FR-010, NFR-001, NFR-002, NFR-005, NFR-007, NFR-008, C-005, C-008, IR-003 | `uv run pytest tests/video/test_quick_verify.py tests/video/test_cli.py` |
| T14 | Capture, narrate, and render the real quick demo | P5 | T13 | FR-001–FR-008, FR-010, FR-011, NFR-001–NFR-004, NFR-006–NFR-010, C-001–C-008, IR-001–IR-004, DR-001–DR-005 | `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline all` |
| T15 | Package, review, document, and close the local delivery | P5 | T14 | FR-001, FR-002, FR-006–FR-011, NFR-001–NFR-010, C-001, C-002, C-004, C-005, C-007–C-009, IR-005, DR-001–DR-003, DR-005 | `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline verify --output ../../dist/video/final` |

## 8. Implementation Tasks

## Phase P1: Evidence Foundation

### T1: Define and Validate the Project Manifest

- **goal:** A typed loader accepts exactly one coherent six-scene production manifest and rejects invalid timing, paths, media settings, safe areas, or nondeterministic output configuration.
- **phase:** P1
- **depends_on:** []
<!-- prettier-ignore -->
- **requirements:** [FR-002, FR-009, NFR-001, NFR-002, NFR-004, NFR-005, C-003, C-009, DR-001, DR-003]
- **priority:** must

#### T1 Context

Use frozen, slotted dataclasses and explicit JSON decoding. Reject unknown fields so misspelled production settings cannot silently change a render. Represent time as integer frames, not floating-point seconds. The approved scene boundaries are frames 0, 450, 1050, 1800, 2550, 3450, and 4050 at 30 fps. Each visual state records its frame interval and the non-overlapping rectangles in which the scene renderer places tracked source or captured evidence. The renderer consumes those same rectangles, and the verifier derives their union area divided by the full frame area; no author-supplied ratio is trusted.

#### T1 Files

| Action | Path | Purpose |
| --- | --- | --- |
| modify | `pyproject.toml` | Add `media/repository-explainer` to `[tool.pytest.ini_options] pythonpath`, `[tool.ruff] src`, and `[tool.basedpyright] extraPaths`; add `media/repository-explainer/video_pipeline` to BasedPyright `include`, leaving `[tool.uv.build-backend] module-name` unchanged. |
| create | `media/repository-explainer/project.json` | Approved timeline and delivery configuration. |
| create | `media/repository-explainer/video_pipeline/__init__.py` | Production package marker. |
| create | `media/repository-explainer/video_pipeline/models.py` | Immutable records and enums. |
| create | `media/repository-explainer/video_pipeline/manifest.py` | Strict loader and cross-record validation. |
| create | `tests/video/conftest.py` | Shared manifest and executable fixtures. |
| create | `tests/video/test_manifest.py` | Unit and property-like boundary coverage. |

#### T1 Acceptance Criteria

- The approved manifest loads to six ordered, gap-free scenes totaling 4050 frames and declares 1920×1080 at 30 fps. (TC-T1-001)
- Unknown keys, path escapes, missing scene IDs, overlaps, gaps, any total other than 4050 frames, unsafe text sizes, and invalid output configuration are rejected with field-specific errors. (TC-T1-002)
- Source paths resolve inside the repository, while generated paths resolve only inside the selected ignored output root. (TC-T1-003)
- Visual-state intervals cover the timeline exactly once; each evidence rectangle is in bounds and non-overlapping so its union area is derivable without double counting. (TC-T1-004)

#### T1 Test Cases

| ID | Test | Type | Expected result |
| --- | --- | --- | --- |
| TC-T1-001 | `test_loads_approved_six_scene_manifest` | unit | Exact order, boundaries, dimensions, and fps are returned. |
| TC-T1-002 | `test_rejects_invalid_manifest_invariants` | unit | Each mutated invalid field produces its named validation error. |
| TC-T1-003 | `test_rejects_paths_outside_owned_roots` | security | Traversal and absolute output paths are rejected. |
| TC-T1-004 | `test_validates_visual_state_classification_inputs` | property-like | Rectangle and interval boundary mutations preserve full, non-overlapping coverage or fail with the named field. |

#### T1 Sub-tasks

- **T1.1 RED** — add the four tests in `tests/video/test_manifest.py`; expected failure: the production models and strict loader do not exist.
- **T1.2 Verify RED** — run `uv run pytest tests/video/test_manifest.py -x`; confirm the missing loader, not collection or fixture setup, causes the failure.
- **T1.3 GREEN** — add the minimum models, loader, project manifest, and the four explicit `pyproject.toml` path entries above; do not add the media package to the wheel or introduce a second Python tool configuration.
- **T1.4 Verify GREEN** — run `uv run pytest tests/video/test_manifest.py` and `uv run pytest tests/test_cli_json_output.py`.
- **T1.5 REFACTOR** — centralize integer/range/path validation without a generic framework; preserve precise error messages.
- **T1.6 Verify Task** — run the T1 tests, Ruff, Ruff format, BasedPyright, and `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline --help`; commit with requirement and test IDs.

### T2: Compile Narration and Captions from One Source

- **goal:** One ordered JSON narration source deterministically produces valid SRT captions and enforces fixed scene budgets, 15-frame narration margins, readability, disclosure, and mute-safe copy.
- **phase:** P1
- **depends_on:** [T1]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-006, FR-008, FR-010, NFR-002, NFR-003, C-002, C-004, C-008, DR-002]
- **priority:** must
- **files:** `media/repository-explainer/narration.json` (create), `media/repository-explainer/captions.srt` (create), `media/repository-explainer/video_pipeline/captions.py` (create), `tests/video/test_captions.py` (create)
- **acceptance:** ordered narration segments start at least 15 frames after their scene starts and end at least 15 frames before their scene ends, contain no overlap, keep captions to two lines and readable dwell time, preserve the six scene messages, and include the AI-narration disclosure (TC-T2-001, TC-T2-002); an overlong take is rejected for owner-approved line shortening rather than moving picture boundaries; repeated compilation is byte-identical (TC-T2-003).
- **sub-tasks:**
  - **T2.1 RED** — add caption parsing, invariant, disclosure, and deterministic SRT tests; expected failure: no compiler or narration source exists.
  - **T2.2 Verify RED** — run `uv run pytest tests/video/test_captions.py -x`; confirm the missing compiler/source causes failure.
  - **T2.3 GREEN** — implement frame-based segment and margin validation, overrun rejection, and SRT emission; author the six-scene narration source and generated SRT.
  - **T2.4 Verify GREEN** — run the caption tests and manifest tests; compare a second compile byte for byte.
  - **T2.5 REFACTOR** — isolate timestamp formatting and line wrapping; do not create alternate script sources.
  - **T2.6 Verify Task** — run T1–T2 tests plus static checks; commit with IDs.

### T3: Capture Truthful Command and Editor Evidence

- **goal:** An allowlisted capture stage records exact argument vectors, named Git revision, exit status, stdout/stderr hashes, a real editor capture, and promoted safe output for repository interactions.
- **phase:** P1
- **depends_on:** [T1]
<!-- prettier-ignore -->
- **requirements:** [FR-004, NFR-006, NFR-008, C-005, C-006, IR-001, DR-001]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/capture.py` (create), `media/repository-explainer/captures/manifest.json` (create), `media/repository-explainer/captures/evidence/` (create), `media/repository-explainer/captures/evidence/editor/` (create), `tests/video/test_capture.py` (create)
- **acceptance:** captures bind output to command, cwd, revision, exit status, timestamp, and SHA-256 (TC-T3-001); shell strings, disallowed executables, dirty-source ambiguity, path escapes, and credential-like environment or output fail closed (TC-T3-002); reviewed promotion copies only named evidence and preserves bytes (TC-T3-003); each editor PNG comes from a real VS Code editor view of the pinned hero file and records application/version, exact settings, viewport, displayed line range, source path/revision/range hash, and PNG hash rather than substituting a generated editor mockup (TC-T3-004); the teaching defect streams the tracked fixture through the exact `--stdin-filename` argv, records exit 1 plus `APSEUDO-WHILE-001`, and never authors a duplicate invalid source (TC-T3-005).
- **sub-tasks:**
  - **T3.1 RED** — add fake-executable, temporary-Git, teaching-defect stdin, and editor-evidence tests; expected failure: the allowlisted capture and promotion APIs do not exist.
  - **T3.2 Verify RED** — run `uv run pytest tests/video/test_capture.py -x`; confirm missing behavior rather than Git setup causes failure.
  - **T3.3 GREEN** — implement argument-vector subprocess capture, Git binding, redaction rejection, hashing, explicit evidence promotion, and a shared clean-clone helper that creates the exact pinned revision below `dist/video/work/` for both T3 editor capture and T4 runner capture. Capture the teaching defect by passing the tracked bytes of `tests/fixtures/invalid/unbounded_while.apseudo` on stdin to `uv run apseudo-lint --stdin-filename tests/fixtures/invalid/unbounded_while.apseudo`; require exit 1 and `APSEUDO-WHILE-001`, and record the tracked source path/hash, exact argv, and stdin source path instead of authoring a duplicate invalid file.
  - **T3.4 GREEN** — Editor Capture: from the shared disposable clean clone, open the pinned hero in VS Code 1.130.0 using the built-in Default High Contrast theme, Noto Sans Mono 32 px with 40 px line height and ligatures disabled, 100% display scale, window zoom 0, full-screen Zen Mode with unrelated UI hidden, and a single 1920×1080 monitor. For each required scroll state, an operator runs `spectacle --current --background --nonotify --output PATH` with a distinct owned PNG path below `media/repository-explainer/captures/evidence/editor/`. An editor-substrate state uses only source crop `[0, 120, 1728, 786]`, translated without scaling to destination/evidence rectangle `[96, 54, 1728, 786]`; it reserves `[96, 864, 1728, 162]` for at most two caption lines and carries no overlaid scene-copy text. Capture enough scroll states that every required displayed line is wholly visible inside the crop. Record operator role, tool versions, settings, crop/destination/caption rectangles, line ranges, source-range hashes, and PNG hashes.
  - **T3.5 REFACTOR** — share owned-path and canonical-JSON helpers with the manifest layer while keeping executable policy local to capture.
  - **T3.6 Verify Task** — run T1–T3 tests and static checks; assert that each captured source range is byte-equal to its tracked range, native scale is exactly 1.0 so recorded 32 px code remains 32 px, the configured palette is at least 4.5:1, source/destination/caption rectangles have the exact values above and do not overlap improperly, every displayed line is inside the title-safe destination crop, every clone path is below `dist/video/work/` at the pinned revision, and fixture captures contain no secret-bearing command/environment fields. Any pinned revision, displayed line range, theme/font/capture-setting, crop geometry, or source-range hash change invalidates the editor record and requires full recapture; missing exact tools/settings blocks T3.

### T4: Capture Guarded Runner Evidence

- **goal:** Runner evidence comes from a disposable Git workspace after check, prompt rendering, command rendering, read-only execution, changed-file report, and no-diff postcondition; otherwise the record selects preflight-only mode.
- **phase:** P1
- **depends_on:** [T3]
<!-- prettier-ignore -->
- **requirements:** [FR-004, FR-005, NFR-008, C-005, C-006, IR-004, DR-004]
- **priority:** must
- **files:** `docs/apseudo-docs/examples/runner/review-spec.apseudo` (read), `media/repository-explainer/video_pipeline/runner_capture.py` (create), `tests/video/test_runner_capture.py` (create), `media/repository-explainer/captures/manifest.json` (modify), `media/repository-explainer/captures/evidence/runner/` (create)
- **acceptance:** from cwd set to the disposable clone root, parse the tracked `.codex/config.toml`, require its `SessionStart` command to equal the allowlisted repository-root hook command, require the resolved hook file to be executable, and invoke that exact configured command through `/bin/bash -lc` with canonical stdin `{"hook_event_name":"SessionStart","source":"startup","cwd":"."}`. Remove `CLAUDE_PROJECT_DIR` from the preflight environment to pin the Codex transport, record the `python3` path selected by the shebang plus `python3 --version`, and require Python 3.14 or newer. Require exit 0, an `&lt;session_context>` wrapper, the clone's exact branch, one exact current-focus bullet from its hashed `docs/handoff/state.md`, and one exact short commit hash from its Git log; reject placeholder/unavailable text and any `session_start.py failed:` diagnostic. The output hash is an opaque per-run integrity record, not a cross-run reproducibility key. Preserve the parsed config command, resolved executable/interpreter/version/mode, normalized input, substantive assertions, exit status, and output hash in `hook-preflight.json`. This explicit configured-command preflight is the “hook execution results preserved” evidence for FR-005/IR-004 because the runner's stale `--require-hooks` probe recognizes only deleted `.codex/hooks.json` and Codex hook events are not a reliable runner output surface.

  Next, derive `operator_apseudo_run` as the `apseudo-run` console script beside the already-synced production process's `sys.executable`, and deterministically construct `POST_CHECK` with `shlex.join([operator_python, "-m", "apseudo_lint.cli", "docs/apseudo-docs/examples/runner/review-spec.apseudo"])`. Require the console-script hash, imported `apseudo_lint` file hash, and version to match the exact capture revision before any runner call. Execute four argument vectors built from `operator_apseudo_run --agent codex --workspace . --sandbox read-only --require-no-diff --post-check POST_CHECK --run-dir dist/video/work/runner-runs --set spec_path=docs/specs/repository-explainer-video.md docs/apseudo-docs/examples/runner/review-spec.apseudo`: insert `--check`, `--render-prompt`, and `--print-command` after `operator_apseudo_run` for the three preflights, then use the base vector for execution. Both resolved operator paths and `POST_CHECK` are recorded in the manifest, not supplied as free shell fragments; they reuse the synced environment, perform no dependency resolution or network access, and read the clone's tracked files through cwd.

  Derive the on-screen runner command by replacing only the exact recorded `operator_apseudo_run` path with `apseudo-run` and the exact recorded `[operator_python, "-m", "apseudo_lint.cli"]` post-check prefix with `apseudo-lint`; preserve every flag and repository-relative argument byte-for-byte. Store the alias map and derived display string in `runner-commands.json`. Content tests must expand the aliases back to the recorded argv, require equality, and reject any absolute operator path on screen.

  The capture records the hook preflight, all four runner vectors, exact rendered prompt substrings `no_hooks_requested: False` and `hooks_required: False`, the derived display mapping, resolved provider vector, post-check command/result, changed-file report, and clean no-diff postcondition before permitting an accepted outcome (TC-T4-001). Nonzero hook, execution, or post-check status; changed files; missing/changed hook wiring; interpreter/revision mismatch; unbound `spec_path`; wrong cwd; or absent provider selects `preflight-only` and never records fabricated acceptance (TC-T4-002). Workspace and logs contain no credential fields or values (TC-T4-003).

- **sub-tasks:**
  - **T4.1 RED** — add disposable-repository tests with a fake runner, configured-command hook preflight, degraded-hook rejection, synced-interpreter post-check, display-alias expansion, named-evidence promotion, clone deletion, and nonzero hook/post-check cases; expected failure: no guarded runner-capture state machine exists.
  - **T4.2 Verify RED** — run `uv run pytest tests/video/test_runner_capture.py -x`; confirm the missing state machine causes failure.
  - **T4.3 GREEN** — reuse T3's shared clean-clone helper at the exact capture revision, set subprocess cwd to that clone root, bind `spec_path` to the clone's tracked `docs/specs/repository-explainer-video.md`, and implement the configured-command hook preflight plus exact four runner vectors above, deterministic synced-interpreter linter post-check, display-alias mapping, isolated `dist/video/work/runner-runs` directory, changed-file detection, and outcome selection. Before cloning, run the repository's locked environment sync and require the production process interpreter/module hashes to match the capture revision; after that precondition, require no network beyond the bounded Codex provider call. Also require local Git object access and a configured Codex login; never reuse the operator's working tree as the agent workspace.
  - **T4.4 Verify GREEN** — run runner-capture tests and the existing `tests/test_runner_operational.py`. After a successful fixture run, selectively promote `hook-preflight.json`, `runner-commands.json`, `run-manifest.json`, `agent-command.json`, `validation-before.json`, `post-checks.json`, `changed-files.json`, and `outcome.json` to `media/repository-explainer/captures/evidence/runner/`; record their hashes in the capture manifest, delete the disposable clone, and require every manifest reference and hash still to resolve.
  - **T4.5 REFACTOR** — make state transitions explicit and typed; retain the capture layer as the only subprocess recorder.
  - **T4.6 Verify Task** — run T3–T4 plus existing runner tests and static checks; commit with IDs.

## Phase P2: Picture and Sound

### T5: Compose Conference-Safe Hybrid Scenes

- **goal:** The six scene renderers create deterministic 1920×1080 composites from validated pseudocode, real command/editor evidence, SVG annotations, and tracked theme data.
- **phase:** P2
- **depends_on:** [T2, T3, T4]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-003, FR-010, NFR-003, NFR-004, NFR-006, NFR-010, C-001, C-002, C-003, C-006, C-008, DR-005]
- **priority:** must
- **files:** `docs/apseudo-docs/examples/review-loop.apseudo` (read), `media/repository-explainer/theme.json` (create), `media/repository-explainer/video_pipeline/scenes.py` (create), `media/repository-explainer/assets/` (create), `media/repository-explainer/asset-provenance.json` (create), `tests/video/test_scenes.py` (create), `tests/video/test_content.py` (create)
- **acceptance:** each scene has a stable composite digest for fixed inputs and uses only referenced source/evidence text; the renderer positions evidence with the manifest's own rectangles and rejects any geometry mismatch (TC-T5-001); scene 3 displays the exact reproducible capture command derived from the manifest argv plus stdin source as `uv run apseudo-lint --stdin-filename tests/fixtures/invalid/unbounded_while.apseudo < tests/fixtures/invalid/unbounded_while.apseudo`, and content tests require byte equality with that derived display string; scene 5 displays only T4's tested path-aliased runner string and never an absolute operator path. Code is at least 32 px, captions reserve at least 44 px, contrast is at least 4.5:1, and essential elements stay within the central 90% of frame width and height (TC-T5-002); the pinned tracked workflow formats and lints cleanly, editor source ranges are byte-equal to the pinned revision, the teaching defect remains clearly labeled, the real editor pixels remain traceable beneath SVG annotations, and every non-repository asset has license or generation provenance (TC-T5-003). Every scene contains a separate `mute_safe_copy` visual state lasting at least 60 frames; that state has no evidence rectangles, places the complete scene message inside copy rectangle `[240, 270, 1440, 540]`, and leaves caption rectangle `[96, 864, 1728, 162]` clear.
- **sub-tasks:**
  - **T5.1 RED** — add scene provenance, manifest-to-renderer evidence-rectangle, editor-range fidelity, runner display-alias, per-scene mute-safe-copy state, geometry, contrast, disclosure, asset-rights, and pinned-pseudocode-content tests; expected failure: no renderer, theme, or provenance manifest exists.
  - **T5.2 Verify RED** — run `uv run pytest tests/video/test_scenes.py tests/video/test_content.py -x`; confirm missing scene behavior causes failure.
  - **T5.3 GREEN** — implement minimal XML-safe SVG primitives and six scene builders; crop the real editor capture at native 1:1 scale with the exact source/destination/evidence rectangle from T3.4, keep the non-overlapping caption band clear, and add SVG annotations without altering source semantics. The C-003 classifier consumes the same destination/evidence rectangle. Add a separate `mute_safe_copy` state of at least 60 frames to every scene, use the exact title-safe copy rectangle above, and do not overlay that copy on editor-substrate states. Add the theme, licensed or procedural brand assets, and provenance manifest; read the hero source only from `docs/apseudo-docs/examples/review-loop.apseudo`.
  - **T5.4 Verify GREEN** — run scene/content tests, then `uv run apseudo-format --check docs/apseudo-docs/examples/review-loop.apseudo` before `uv run apseudo-lint docs/apseudo-docs/examples/review-loop.apseudo`.
  - **T5.5 REFACTOR** — consolidate layout primitives only where scenes share semantics; keep scene-specific narrative code separate.
  - **T5.6 Verify Task** — run T2–T5 tests, pseudocode checks, SVG decode smoke test through FFmpeg, and static checks; commit with IDs.

### T6: Generate Bounded `marin` Narration

- **goal:** The speech adapter verifies the current model/voice/WAV and permission contract, sends only the complete locked narration script and delivery instructions to the Speech endpoint, rejects full-script takes whose extracted segments exceed fixed scene budgets, writes validated WAV segments, and records bounded retry and non-itemized spend metadata without exposing the key.
- **phase:** P2
- **depends_on:** [T2]
<!-- prettier-ignore -->
- **requirements:** [FR-006, NFR-007, NFR-008, NFR-009, C-004, C-005, C-007, IR-002, DR-002, DR-004]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/speech.py` (create), `media/repository-explainer/production-evidence.json` (create), `tests/video/test_speech.py` (create)
- **acceptance:** dated documentation/dashboard evidence records `gpt-4o-mini-tts`, `marin`, WAV, and the narrowest available Restricted permission bundle; a one-time preproduction permission smoke records only request class, date, status, and pass/fail while proving Speech succeeds and each separately denied non-model resource class is refused, after which production permits only `POST /v1/audio/speech` with the complete approved script and calm technical instructions (TC-T6-001); one provider response is one full-script take, every segment is extracted and measured locally, and no more than three total takes are generated for an unchanged script/model/voice/instructions hash without explicit owner approval. A rejected segment consumes that global series cap and requires a new full-script take rather than an uncounted segment call. Transient retry uses bounded exponential backoff while auth, permission, policy, malformed/overlong audio, and projected over-budget errors fail immediately, retains the speaker cut only as an interim artifact, and leaves v1 blocked pending owner approval under AW-004 (TC-T6-002); logs and manifests contain no authorization value, itemized billing data, response body from a denial probe, or claim that provider-bundled model capabilities are independently denied (TC-T6-003).
- **sub-tasks:**
  - **T6.1 RED** — add local HTTP-server contract, permission-smoke evidence, synthetic full-script WAV extraction, fixed-budget, unchanged-series hard three-take cap, provider-unavailable, and spend-bound tests; expected failure: the speech client and guards do not exist.
  - **T6.2 Verify RED** — run `uv run pytest tests/video/test_speech.py -x`; confirm missing speech behavior causes failure without network access.
  - **T6.3 GREEN** — implement the standard-library HTTPS request, one-time permission-smoke mode, full-script WAV response and local segment validation, a global hard cap of three provider takes for each unchanged script/model/voice/instructions hash, atomic WAV writes, and a secret-free non-itemized take manifest. Permission smoke is the only non-Speech provider access and cannot run from `narrate` or `all`.
  - **T6.4 Verify GREEN** — run speech tests and a dry-run that prints only model, voice, segment count, and projected bound.
  - **T6.5 REFACTOR** — isolate transport injection and WAV probing so tests do not patch implementation internals.
  - **T6.6 Verify Task** — run T2 and T6 tests, static checks, and a dry-run secret scan; commit with IDs.

### T7: Render Narrated and Speaker Timelines

- **goal:** One frame-based render graph produces equivalent-picture narrated and speaker MP4s, burns captions, synthesizes the licensed-safe tonal bed, and supports bounded scene replacement.
- **phase:** P2
- **depends_on:** [T5, T6]
<!-- prettier-ignore -->
- **requirements:** [FR-007, FR-008, FR-009, FR-011, NFR-001, NFR-002, NFR-005, NFR-007, IR-003, DR-003, DR-004]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/render.py` (create), `dist/video/candidate/render-manifest.json` (generate, ignored), `tests/video/test_render.py` (create)
- **acceptance:** fixture renders produce two 1920×1080, 30 fps H.264/AAC files with exactly 4050 video frames and decoded program audio trimmed to 135 seconds, with encoder priming represented only through container skip/discard metadata and no audible decoded sample after the program boundary; speech exists only in the narrated variant (TC-T7-001); narration captions are burned only into the narrated master, both variants retain mute-safe scene copy, the procedural tonal bed records its FFmpeg synthesis parameters, and the audio graph applies −16 LUFS/−1 dBTP narrated and −28 LUFS/−6 dBTP speaker-cut targets (TC-T7-002); rendering one scene invalidates only that scene clip and dependent concatenations, narrated reproduction accepts the checksummed selected WAV without a provider call, and the render manifest records source/input hashes plus exact FFmpeg, FFprobe, librsvg, fontconfig, font-file, encoder, and option versions (TC-T7-003).
- **sub-tasks:**
  - **T7.1 RED** — add FFmpeg-command contract tests and a short real fixture render; expected failure: no render graph or encoder-capability selector exists.
  - **T7.2 Verify RED** — run `uv run pytest tests/video/test_render.py -x`; confirm missing render behavior causes failure, not an absent fixture tool.
  - **T7.3 GREEN** — implement capability probing, SVG scene clips, deterministic 4050-frame concat, narrated-only caption burn-in, recorded procedural tonal-bed synthesis, per-variant audio graphs, selected-WAV input, render-manifest emission, and both export variants.
  - **T7.4 Verify GREEN** — run render tests and inspect the fixture with FFprobe; compare decoded video-frame hashes after metadata removal and verify decoded PCM stops at the 135-second program boundary.
  - **T7.5 REFACTOR** — separate pure command construction from subprocess execution and cache decisions.
  - **T7.6 Verify Task** — run T5–T7 tests, real fixture render/probe, and static checks; commit with IDs.

## Phase P3: Verification and Orchestration

### T8: Verify Media, Authenticity, Rights, and Security

- **goal:** A single verification report fails promotion unless media streams, exact frame/audio duration, per-variant loudness, captions, final-frame layout, authenticity, asset rights, disclosure, secret scans, and reproducibility evidence satisfy the specification.
- **phase:** P3
- **depends_on:** [T7]
<!-- prettier-ignore -->
- **requirements:** [FR-010, FR-011, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-010, C-001, C-003, C-005, C-008, IR-003, DR-003, DR-005]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/verify.py` (create), `tests/video/test_verify.py` (create)
- **acceptance:** probe and EBU R128 parsers produce explicit passing rows for both variants' format, 4050-frame/135-second program boundary, streams, separate loudness, and peak contracts (TC-T8-001); altered evidence, missing `delivery.json` disclosure, narration captions in the speaker cut, absent mute-safe copy, unsafe final frames at any scene/state/caption transition, unclassified assets, external music input, speech in the speaker cut, or credential-like content blocks promotion (TC-T8-002); on the exact toolchain recorded as an approved render input, a clean-checkout rerender must match decoded video-frame, decoded PCM, caption, and semantic-manifest hashes while excluding only container metadata; a toolchain mismatch blocks the reproducibility claim rather than applying an unapproved perceptual threshold (TC-T8-003); using the renderer-consumed evidence rectangles, the frame-weighted sum of visual states whose derived evidence union occupies at least half the frame must fall from 60% through 80% inclusive (TC-T8-004).
- **sub-tasks:**
  - **T8.1 RED** — add parser, exact-duration, per-variant loudness, aggregate-report, final-frame, asset-rights, disclosure, tampering, redaction, offline exact-toolchain semantic-comparison, render-manifest, and frame-share boundary tests; expected failure: no verifier exists.
  - **T8.2 Verify RED** — run `uv run pytest tests/video/test_verify.py -x`; confirm the missing verification behavior causes failure.
  - **T8.3 GREEN** — implement probe/per-variant-loudness parsing, Must-gate aggregation, authenticity and asset-rights comparison, render-manifest validation, exact-toolchain offline reproduction checks, sampled final-frame/caption checks, renderer-geometry-derived C-003 frame-share calculation, disclosure and procedural-audio checks, secret scanning, and checksum output.
  - **T8.4 Verify GREEN** — run verifier tests against passing and deliberately corrupted fixture outputs.
  - **T8.5 REFACTOR** — give every gate a stable ID and structured evidence payload; avoid ambiguous Boolean-only failures.
  - **T8.6 Verify Task** — run T7–T8 tests, real fixture verification, and static checks; commit with IDs.

### T9: Expose the Reproducible Production CLI

- **goal:** A stage-oriented CLI performs capability checks, capture, narration, rendering, verification, and full production with dry-run and explicit output roots, while never accepting unresolved paths or printing secrets.
- **phase:** P3
- **depends_on:** [T3, T4, T6, T7, T8]
<!-- prettier-ignore -->
- **requirements:** [FR-009, NFR-005, NFR-008, C-005, C-009, DR-001, DR-004]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/cli.py` (create), `media/repository-explainer/video_pipeline/__main__.py` (create), `media/repository-explainer/README.md` (create), `tests/video/test_cli.py` (create)
- **acceptance:** `check`, `capture`, `permission-smoke`, `narrate`, `render`, `verify`, and `all` subcommands use the same manifest, default final output to `dist/video/`, isolate every transient TTS response, disposable runner clone/record, and render intermediate below `dist/video/work/`, forbid `.apseudo/runs`, and return stable exit codes (TC-T9-001); `permission-smoke` is separately owner-invoked and unavailable through `all`, while `--dry-run` emits redacted argument vectors and planned outputs without writes or network (TC-T9-002); a clean fixture `all` run is reproducible from approved source plus the selected-WAV input and a failed stage prevents promotion (TC-T9-003).
- **sub-tasks:**
  - **T9.1 RED** — add subprocess CLI contract, dry-run, failure propagation, and fixture e2e tests; expected failure: no production entry point exists.
  - **T9.2 Verify RED** — run `uv run pytest tests/video/test_cli.py -x`; confirm the missing entry point causes failure.
  - **T9.3 GREEN** — implement argparse commands, shared context, enforced `dist/video/work/` transient roots, atomic stage directories, selected-WAV reproduction input, stable exit codes, and concise documentation. Document every repo-root command as `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline ...`, with `../../dist/video/...` output paths resolved from the production directory.
  - **T9.4 Verify GREEN** — run CLI tests and one real short fixture `all` run.
  - **T9.5 REFACTOR** — keep orchestration in the CLI and domain behavior in existing modules; remove duplicate validation.
  - **T9.6 Verify Task** — run all `tests/video`, static checks, `--help`, `check`, and dry-run commands; commit with IDs.

## Phase P4: Production and Delivery

### T10: Lock Approved Content and Real Captures

- **goal:** The committed production source contains the final six-scene copy, valid hero workflow, current diagnostics, real command evidence, truthful runner mode, disclosure, and conference-safe graphics at one named revision.
- **phase:** P4
- **depends_on:** [T5, T9]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-005, FR-008, FR-010, NFR-003, NFR-004, NFR-006, NFR-008, NFR-010, C-001, C-002, C-003, C-006, C-008, IR-001, IR-004, DR-005]
- **priority:** must
- **files:** `docs/apseudo-docs/examples/review-loop.apseudo` (read), `media/repository-explainer/project.json` (modify), `media/repository-explainer/narration.json` (modify), `media/repository-explainer/captions.srt` (modify), `media/repository-explainer/theme.json` (modify), `media/repository-explainer/assets/` (modify), `media/repository-explainer/asset-provenance.json` (modify), `media/repository-explainer/captures/` (modify), `tests/video/test_content.py` (modify)
- **acceptance:** content tests bind all six scenes to approved copy, the exact tracked hero path, the real editor-capture record, asset provenance, and current evidence at the capture revision (TC-T10-001); formatter/linter/captured rule-explanation/Mermaid and exact bounded runner records reproduce with recorded statuses and hashes (TC-T10-002); representative final states contain no unapproved text, credential-like content, unclassified asset, or unsafe layout, and the computed real-evidence frame share remains from 60% through 80% (TC-T10-003).
- **sub-tasks:**
  - **T10.1 RED** — tighten content tests to the approved scene/source ledger; expected failure: placeholder fixture content and captures do not satisfy the final ledger.
  - **T10.2 Verify RED** — run `uv run pytest tests/video/test_content.py -x`; confirm final content/evidence absence causes failure.
  - **T10.3 GREEN** — author final copy and visuals, validate the existing tracked workflow, run real capture commands including `apseudo-explain`, review outputs and asset provenance, and promote only named evidence.
  - **T10.4 Verify GREEN** — run content/capture tests, then formatter check before linter, rule explanation, Mermaid generation, and guarded runner capture at the recorded revision.
  - **T10.5 REFACTOR** — remove redundant copy and unused capture candidates; keep the ledger as the only scene-to-evidence mapping.
  - **T10.6 Verify Task** — run all video tests, pseudocode tools, capture reproduction, SVG decode, secret scan, and static checks; commit with IDs.

### T11: Generate Narration and Both Final Candidates

- **goal:** A bounded live production run generates reviewed, scene-budget-compliant `marin` stems, retains the selected checksummed WAV, and renders both full-resolution 4050-frame candidates from the locked source.
- **phase:** P4
- **depends_on:** [T10]
<!-- prettier-ignore -->
- **requirements:** [FR-006, FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005, NFR-007, NFR-009, C-004, C-007, IR-002, IR-003, DR-002]
- **priority:** must
- **files:** `dist/video/candidate/` (generated, ignored), `media/repository-explainer/production-evidence.json` (modify), `.project-pipeline/2026-07-23-repository-explainer-video/logs/` (scratch evidence)
- **acceptance:** the dated provider/permission smoke record and approved dry-run project a non-itemized spend below USD 1 and prove that production lists only Speech requests (TC-T11-001); selected `marin` segments are complete, intelligible, normalized, inside their 15-frame scene margins, derive from no more than three total full-script takes for the unchanged series hash, and are retained with the selected checksummed full narration WAV as delivery input (TC-T11-002); both 4050-frame candidates render with matching picture timing and pass automated media verification, or provider unavailability creates only the explicitly labeled interim speaker candidate described below and leaves T11 blocked pending owner approval (TC-T11-003).
- **sub-tasks:**
  - **T11.1 RED** — run the full candidate verification before generation; expected failure: required narration stems and MP4 candidates are absent.
  - **T11.2 Verify RED** — confirm only missing production artifacts fail; fix any source, environment, or capability error before spending or rendering.
  - **T11.3 GREEN** — record the exact provider permission bundle and successful preproduction smoke, resolve the key into the production process environment, run bounded `marin` generation, reject overlong takes for owner-approved line shortening without moving picture, retain the selected WAV, and render both candidates with a complete render manifest.
  - **T11.4 Verify GREEN** — run automated verification, FFprobe, EBU R128, and a full narrated plus mute playback review; regenerate only rejected segments/scenes within the spend cap.
  - **T11.5 REFACTOR** — assess picture/audio changes; record `none` unless a source-level simplification is proven necessary, then rerender.
  - **T11.6 Verify Task** — save verbose command/report evidence in checklist scratch, promote the secret-free permission, non-itemized spend-bound, render, and candidate-verification summary to `media/repository-explainer/production-evidence.json`, confirm selected-WAV checksum and Git source diff, and commit any reviewed source corrections with IDs. Do not delete scratch until the durable record and local delivery reports are verified.

### T12: Accept and Deliver the Verified Film

- **goal:** Accepted candidates are promoted to stable local filenames with the selected narration WAV, `delivery.json`, checksums, disclosure, asset provenance, reusable sources, verification evidence, and accurate handoff records.
- **phase:** P4
- **depends_on:** [T11]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-009, NFR-010, C-001, C-002, C-004, C-005, C-007, C-008, C-009, IR-005, DR-001, DR-002, DR-003, DR-005]
- **priority:** must
- **files:** `dist/video/final/` (generated, ignored), `media/repository-explainer/README.md` (modify), `media/repository-explainer/production-evidence.json` (modify), `docs/handoff/specs-plans.md` (modify), `docs/handoff/state.md` (modify), `docs/handoff/deployed.md` (modify)
- **acceptance:** `agent-pseudocode-explainer-narrated.mp4`, `agent-pseudocode-explainer-speaker.mp4`, `agent-pseudocode-explainer-narration-selected.wav`, `agent-pseudocode-explainer-captions.srt`, `delivery.json`, `render-manifest.json`, `asset-provenance.json`, `verification-report.json`, and `checksums.sha256` match the verified candidates (TC-T12-001); narrated, muted, and every required scene/state/caption final-frame owner review accept the promise, readability, truth, and disclosure (TC-T12-002); repository source, durable production evidence, handoff, and final report contain credential references and non-itemized cost evidence only, distinguish local delivery from hosted publication, and classify every asset (TC-T12-003); AW-004 interim promotion follows its separate branch and cannot satisfy final v1 acceptance (TC-T12-004); a fixture rollback rehearsal retains a prior Verified package, changes one reviewed input, creates a differently named candidate plus render manifest and checksums, and leaves the Verified bytes unchanged (TC-T12-005).
- **sub-tasks:**
  - **T12.1 RED** — run final verification against `dist/video/final`; expected failure: no promoted delivery package exists.
  - **T12.2 Verify RED** — confirm missing finals are the only failure and the candidate verification remains green.
  - **T12.3 GREEN** — atomically promote accepted candidates to the exact filenames above with the selected narration WAV, captions, `delivery.json`, render manifest, provenance, reports, and checksums; update reproduction and handoff documentation.
  - **T12.4 Verify GREEN** — rerun final verification, checksum comparison, secret scan, Markdown checks, handoff checks, and clean-source render proof.
  - **T12.5 REFACTOR** — remove obsolete ignored candidates/intermediates only after final checksums and durable evidence are recorded; preserve reusable committed source.
  - **T12.6 Recover / Roll Back** — rehearse rollback with fixture outputs before production acceptance: retain the prior Verified files and manifest, alter one reviewed fixture input, create a differently named candidate plus manifest/checksums, and prove the Verified checksums did not change. If credential exposure is suspected, stop production, delete only the identified affected local artifacts, rotate `secret/api-keys/ai/openai-tts` in OpenBao, and rerun from reviewed source. For a rejected render, retain the last Verified files and manifest, restore only the affected reviewed source, and create a new candidate plus manifest; never overwrite the last Verified package.
  - **T12.7 AW-004 Interim** — when narration is blocked, promote only the verified speaker candidate as `agent-pseudocode-explainer-speaker-interim.mp4`; require all speaker-applicable media, mute-safe story, authenticity, asset-rights, security, C-003, clean-checkout speaker reproduction, inventory, and checksum gates; set `delivery.json` to `status: interim`, name AW-004 and the missing narrated Must gates, record explicit owner acceptance, and state that v1 is incomplete. Never use the final speaker filename or mark T12 complete on this branch.
  - **T12.8 Verify Task** — complete the owner acceptance checklist, run the repository-scoped final gate, commit durable close-out with IDs, and report clickable final paths without publishing externally. Delete `.project-pipeline/2026-07-23-repository-explainer-video/` only after its durable secret-free evidence is present in tracked source or the final local bundle.

## Phase P5: Quick-Demo Recalibration

Tasks T8–T12 are skipped in the live checklist because their assurance scope exceeded the owner's quick-demo intent. T13–T15 are the only remaining execution path.

### T13: Add Quick-Demo Verification and CLI Beside Dormant Strict Assurance

- **goal:** A small local CLI renders or verifies the demo without a provider call when given the selected WAV, and reports only actionable media, disclosure, targeted credential-safety, and checksum results.
- **phase:** P5
- **depends_on:** [T7]
<!-- prettier-ignore -->
- **requirements:** [FR-009, FR-010, NFR-001, NFR-002, NFR-005, NFR-007, NFR-008, C-005, C-008, IR-003]
- **priority:** must
- **files:** `media/repository-explainer/video_pipeline/quick_verify.py` (create), `media/repository-explainer/video_pipeline/cli.py` (create), `media/repository-explainer/video_pipeline/__main__.py` (modify), `media/repository-explainer/README.md` (create), `tests/video/test_quick_verify.py` (create), `tests/video/test_cli.py` (create)
- **acceptance:** verification reads the two MP4s directly with FFprobe, checks 1920×1080, 30 fps, H.264/AAC stereo, 4050 frames, approximately 135 seconds, variant loudness targets, captions/disclosure, targeted source/log credential patterns, and SHA-256 inventory (TC-T13-001); the CLI exposes `check`, `capture`, `narrate`, `render`, `verify`, and `all`, keeps transient work below `dist/video/work`, and accepts the selected WAV for rerendering without another Speech call (TC-T13-002).
- **sub-tasks:**
  - **T13.1 RED** — add direct media and CLI contract tests; expected failure: the quick verifier and production entry point do not exist.
  - **T13.2 Verify RED** — run the focused tests and confirm failures name the missing simple contract.
  - **T13.3 GREEN** — implement the smallest verifier and orchestration CLI that satisfy the acceptance criteria.
  - **T13.4 Verify GREEN** — run a short fixture render through `verify` and `all --dry-run`.
  - **T13.5 REFACTOR** — keep quick orchestration readable and leave the strict-assurance verifier dormant and unchanged for possible future use.
  - **T13.6 Verify Task** — run T7, T13, Ruff, scoped BasedPyright, and `git diff --check`; commit with IDs.

### T14: Capture, Narrate, and Render the Real Quick Demo

- **goal:** Produce the real two-minute-fifteen-second narrated and speaker candidates from reviewed repository footage and the approved `marin` voice.
- **phase:** P5
- **depends_on:** [T13]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-010, FR-011, NFR-001, NFR-002, NFR-003, NFR-004, NFR-006, NFR-007, NFR-008, NFR-009, NFR-010, C-001, C-002, C-003, C-004, C-005, C-006, C-007, C-008, IR-001, IR-002, IR-003, IR-004, DR-001, DR-002, DR-003, DR-004, DR-005]
- **priority:** must
- **files:** `media/repository-explainer/captures/` (modify), `media/repository-explainer/production-evidence.json` (modify), `dist/video/candidate/` (generate, ignored)
- **acceptance:** two real editor frames replace the lock-screen blocker and visually match the hero workflow; the existing truthful command and preflight-only runner evidence remains unchanged (TC-T14-001); one bounded `marin` narration package fits the scene timing and both 4050-frame candidates pass the T13 media checks (TC-T14-002).
- **sub-tasks:**
  - **T14.1 RED** — run production readiness and confirm only real editor, narration, and final candidate artifacts are missing.
  - **T14.2 Verify RED** — inspect the missing-artifact report and fix source defects before any paid call.
  - **T14.3 GREEN** — capture the two editor frames, run the bounded Speech request, select the WAV, and render both candidates.
  - **T14.4 Verify GREEN** — run basic verification and inspect representative opening, diagnostic, runner, and end-card frames plus narrated and muted playback.
  - **T14.5 REFACTOR** — correct only visible or audible defects; do not add new assurance infrastructure.
  - **T14.6 Verify Task** — save secret-free production evidence and commit reviewed source/capture changes with IDs.

### T15: Package, Review, Document, and Close the Local Delivery

- **goal:** Promote the accepted candidates and reusable inputs to stable local filenames, document reproduction, and close the repository session.
- **phase:** P5
- **depends_on:** [T14]
<!-- prettier-ignore -->
- **requirements:** [FR-001, FR-002, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, NFR-001, NFR-002, NFR-003, NFR-004, NFR-005, NFR-006, NFR-007, NFR-008, NFR-009, NFR-010, C-001, C-002, C-004, C-005, C-007, C-008, C-009, IR-005, DR-001, DR-002, DR-003, DR-005]
- **priority:** must
- **files:** `dist/video/final/` (generate, ignored), `media/repository-explainer/README.md` (modify), `media/repository-explainer/production-evidence.json` (modify), `docs/handoff/` (modify)
- **acceptance:** final contains narrated and speaker MP4s, selected WAV, captions, `delivery.json`, render manifest, verification report, and checksums under stable names (TC-T15-001); representative playback/frame review accepts story, readability, truthfulness, narration, and disclosure, and the documented rerender command works with the selected WAV (TC-T15-002).
- **sub-tasks:**
  - **T15.1 RED** — verify the final directory before promotion; expected failure: stable delivery files are absent.
  - **T15.2 Verify RED** — confirm candidates remain green.
  - **T15.3 GREEN** — promote the reviewed files and write delivery metadata, checksums, reproduction documentation, and handoff facts.
  - **T15.4 Verify GREEN** — rerun basic media, checksum, targeted source/log, Markdown, pseudocode, and handoff checks.
  - **T15.5 REFACTOR** — remove obsolete local candidates only after final checksums exist.
  - **T15.6 Verify Task** — run the proportional final gate, harvest plan notes, close handoff, commit, merge to `main`, and push.

## 9. Cross-Cutting Requirements

| Concern | Applies? | How verified | Owning task |
| --- | --- | --- | --- |
| Error handling | yes | Stable stage errors and failed-promotion tests. | T3, T4, T6–T9 |
| Logging / observability | yes | Capture, take, render, and verification manifests with secret-free logs. | T3, T6, T8, T9 |
| Security | yes | Owned-path checks, no shell, dated narrowest-permission record, Speech-only process call, secret scans, manual diff. | T3, T4, T6, T8, T12 |
| Performance | yes | Scene cache and bounded replacement; full render completes without retained frame explosion. | T7, T11 |
| Compatibility | yes | Capability probe selects a verified H.264 encoder and rejects missing filters/fonts. | T7, T9 |
| Accessibility | yes | Caption/content tests plus muted owner review. | T2, T5, T12 |
| Authenticity | yes | Revision-bound command/editor hashes, real-evidence frame-share classification, and source-to-scene comparison. | T3, T8, T10 |
| Asset rights | yes | Provenance manifest and procedural tonal-bed evidence block unclassified inputs. | T5, T7, T8, T12 |
| Documentation | yes | Reproduction README and local-delivery handoff validation. | T9, T12 |

## 10. Integration and Migration

### 10.1 Integration Sequence

1. Establish strict manifests and caption compilation.
2. Capture normal repository evidence and guarded runner evidence.
3. Compose hybrid editor/SVG scenes from the pinned tracked workflow, classify assets, and implement the bounded Speech adapter.
4. Render both timelines, then add aggregate verification.
5. Expose the stage CLI and prove a fixture end-to-end run.
6. Lock final source/evidence, generate live narration, render candidates, and promote only after every Must gate passes.

### 10.2 Data or State Migration

- **Required:** no · **Rollback supported:** yes · **Idempotent:** yes
- No existing data is migrated. Rollback retains the last Verified files and render manifest, restores only the affected verified production source, and renders a newly named candidate plus manifest. Evidence promotion is explicit and additive until its owning task commits.

### 10.3 Compatibility Plan

The production package is not part of the installed wheel or public CLI. Existing `apseudo_lint` behavior and entry points remain unchanged. The only project configuration change makes the local media package visible to tests and static analysis. Generated outputs remain under the already ignored `dist/` root.

## 11. Risks and Decisions

| ID | Risk | Likelihood | Impact | Mitigation | Owning task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Current diagnostics differ from storyboard wording. | medium | medium | Bind scenes to current captures and update copy rather than fake output. | T10 |
| R-002 | Runner cannot produce an accepted read-only result. | medium | low | Render the approved verified-preflight alternate. | T4, T10 |
| R-003 | `marin` pronunciation or pacing misses a fixed scene budget. | medium | medium | Enforce 15-frame margins, reject overlong takes, and shorten only the owner-approved line without moving picture. | T2, T6, T11 |
| R-004 | Full render is slow or nondeterministic. | medium | medium | Use integer frames, cached scene clips, fixed metadata, and semantic comparison. | T7, T8 |
| R-005 | Secret material enters logs or media. | low | high | No environment dumps, restricted request logging, scans before promotion, rotation response. | T3, T6, T8, T12 |
| R-006 | Existing unrelated repository gates obscure video status. | high | low | Run and report scoped video gates separately; do not weaken repository policy. | T12 |
| R-007 | The approved model, voice, WAV format, or usable Restricted-key bundle becomes unavailable. | low | high | Stop paid calls, retain only a verified speaker cut as interim evidence, record AW-004, and require owner approval before any substitute. | T6, T11 |

| ID | Decision | Rationale | Affected task(s) |
| --- | --- | --- | --- |
| D-001 | Keep production code under `media/repository-explainer/`. | It remains reproducible but outside the shipped linter package. | T1–T9 |
| D-002 | Use integer frames as timeline truth. | It avoids floating-point drift across captions, SVGs, and FFmpeg. | T1, T2, T7 |
| D-003 | Use a real revision-bound editor capture for the editor interaction and truthful SVG composition/annotation elsewhere. | The film shows actual editor behavior while source/evidence provenance remains reviewable and conference text stays large. | T3, T5, T10 |
| D-004 | Use standard-library HTTPS instead of adding the OpenAI SDK. | The pipeline needs one endpoint and the repository keeps runtime dependencies minimal. | T6 |
| D-005 | Generate a simple tonal bed with FFmpeg. | It avoids untracked licensing obligations and keeps the speaker cut complete. | T7 |
| D-006 | Keep binary delivery artifacts ignored. | Git contains reproducible source and evidence; local delivery retains checksums. | T7, T11, T12 |
| D-007 | Retain the selected narration WAV in the checksummed local delivery bundle. | Provider output is not deterministic; clean-checkout narrated reproduction must not require another paid call. | T6–T9, T11, T12 |
| D-008 | Record the narrowest available Speech-permitting Restricted-key bundle without claiming provider-bundled model capabilities are independently denied. | The dashboard may group model capabilities more coarsely than the production process's single endpoint. | T6, T11, T12 |

## 12. Open Questions

| Question | Blocking? | Owner | Current assumption |
| --- | --- | --- | --- |
| Where should the final MP4 be published after local acceptance? | no | Chris Purcell | Deliver locally; publication is a separate authorized action. |
| Will a venue provide codec, loudness, or safe-area requirements? | no | Chris Purcell | Use `SPEC-NSBJ` NFR-001, NFR-004, and NFR-007. |

## 13. Final Verification

Run at close-out; store verbose evidence in checklist logs.

- `uv run pytest tests/video`
- `uv run pytest`
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run basedpyright`
- `uv run coverage run -m pytest`
- `uv run coverage report`
- `uv run pip-audit`
- `uv run ruff check media/repository-explainer/video_pipeline tests/video`
- `uv run ruff format --check media/repository-explainer/video_pipeline tests/video`
- `uv run basedpyright media/repository-explainer/video_pipeline tests/video`
- `COVERAGE_FILE=.coverage.video uv run coverage run --source=media/repository-explainer/video_pipeline -m pytest tests/video`
- `COVERAGE_FILE=.coverage.video uv run coverage report --fail-under=0`
- `uv run apseudo-format --check .`
- `uv run apseudo-lint .`
- `uv run apseudo-review .`
- `uv run apseudo-format --check docs/apseudo-docs/examples/review-loop.apseudo`
- `uv run apseudo-lint docs/apseudo-docs/examples/review-loop.apseudo`
- `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline check`
- `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline verify --output ../../dist/video/final`
- `npx prettier --check "**/*.md" "**/*.json" "**/*.jsonc" "**/*.yml" "**/*.yaml" "!docs/reference/pre-migration/**" "!package-lock.json"`
- `npx markdownlint-cli2 "**/*.md"`
- Reproduce the speaker cut from a clean checkout and the narrated master from that checkout plus the checksummed selected narration WAV while denying network access.
- Inspect `delivery.json`, `render-manifest.json`, the asset-provenance manifest, the procedural tonal-bed record, the dated permission-smoke/bundle record, and the exact stable filename inventory.
- Review narrated playback, muted playback, and final frames at every scene/state transition and caption-bearing state.
- Confirm every requirement maps to completed evidence, every task is done or explicitly skipped, no blocker remains, and no publication claim exceeds local delivery.

The known whole-repository Prettier drift in five VS Code extension files and the unrelated existing coverage-floor backlog must be reported accurately if still present. DEV-001 may block a repository-complete green claim while the isolated media suite and local delivery are Verified; neither blocker may be hidden by weakening configuration.

## 14. Close-Out

- **Completed:** `2026-07-24` · T14 production checkpoint `d3ac117`; T15 close-out recorded by the plan-completion commit.
- **Deviations / decisions harvested from notes:** OpenAI returned streaming WAV headers with an unknown-length sentinel, so the saved selected take was losslessly normalized through FFmpeg before local segmentation. Six narration segments were placed at their locked scene starts. A measured 1.3 dB post-normalization gain met the narrated loudness and peak limits, and libass production captions use 12 points to render at approximately the intended 44-pixel height.
- **Risks closed / accepted:** Quick verification passed both 4050-frame MP4s, captions/disclosure, targeted credential scanning, loudness, and required-file hashes. Representative opening, editor, diagnostic, runner, and end-card frames passed visual review. The truthful runner scene remains preflight-only. The unrelated 62% repository coverage result remains an existing project backlog, not a media-delivery blocker.
- **Deferred work filed:** T8–T12 release-grade assurance remains skipped under the owner-approved quick-demo boundary. The strict verifier and tests remain dormant and preserved for optional future hardening. Hosted publication and venue-specific transcoding remain open decisions.

The ephemeral `.project-pipeline/2026-07-23-repository-explainer-video/` checklists were removed after final validation.

## Appendices

### Appendix A. Interface and Data Changes

#### A.1 Public Interfaces

| Interface | Current | Planned | Compatibility |
| --- | --- | --- | --- |
| Installed `apseudo_lint` APIs and CLIs | Existing toolkit surfaces | Unchanged | Fully compatible |
| Local video-production CLI | Absent | `uv run --project ../.. --directory media/repository-explainer python -m video_pipeline` with stage subcommands | Repository-local; not installed |
| Speech provider | Absent | Narrowest available Restricted permission with production calls limited to `POST /v1/audio/speech` | Build-time only; bundled model capabilities are recorded rather than overstated |

#### A.2 Data Models

| Model | Fields | Change | Validation | Migration |
| --- | --- | --- | --- | --- |
| Project manifest | delivery, safe area, audio, ordered scenes, visual states with evidence rectangles | add | Strict keys, integer frames, owned paths, complete state coverage, in-bounds non-overlapping rectangles | none |
| Narration segment | scene, start/end frame, 15-frame margins, text, direction | add | Ordered, fixed-picture bounded, readable, disclosed | none |
| Capture evidence | kind, command or editor application, cwd/source, revision, status, viewport, hashes, promoted path | add | Allowlist, owned paths, real-editor provenance, secret rejection | none |
| TTS take | segment, model, voice, output hash, retries, cost bound | add | `marin`, WAV probe, budget cap | none |
| Verification report | stable gate IDs, status, evidence paths, checksums | add | Every Must gate represented | none |
| Asset provenance | path, source, license or generation method, checksum | add | No unclassified delivery input | none |
| Delivery manifest | filename, role, checksum, AI-narration disclosure | add | Every required artifact represented | none |
| Render manifest | source revision, scene timing, input hashes, toolchain, synthesis, export hashes | add | Exact approved toolchain and every input/output represented | none |
| Production evidence | permission smoke, provider contract, spend bound, candidate/final status | add | Secret-free summaries only; no denial bodies or itemized billing | none |

### Appendix B. Test Matrix

| Test ID | Requirement | Task | Test path | Type |
| --- | --- | --- | --- | --- |
| TC-T1-001 | FR-002, NFR-001, NFR-002 | T1 | `tests/video/test_manifest.py::test_loads_approved_4050_frame_six_scene_manifest` | unit |
| TC-T1-002 | NFR-004, NFR-005 | T1 | `tests/video/test_manifest.py::test_rejects_invalid_manifest_invariants` | unit |
| TC-T1-003 | FR-009 | T1 | `tests/video/test_manifest.py::test_rejects_paths_outside_owned_roots` | security |
| TC-T1-004 | C-003 | T1 | `tests/video/test_manifest.py::test_validates_visual_state_classification_inputs` | property-like |
| TC-T2-001 | FR-001, FR-008, NFR-003 | T2 | `tests/video/test_captions.py::test_compiles_mute_safe_captions` | unit |
| TC-T2-002 | FR-006, FR-010, NFR-002 | T2 | `tests/video/test_captions.py::test_rejects_outside_scene_margins_or_missing_disclosure` | regression |
| TC-T2-003 | FR-009, NFR-005 | T2 | `tests/video/test_captions.py::test_srt_compilation_is_deterministic` | unit |
| TC-T3-001 | FR-004 | T3 | `tests/video/test_capture.py::test_records_revision_bound_command_evidence` | integration |
| TC-T3-002 | NFR-008 | T3 | `tests/video/test_capture.py::test_rejects_unsafe_command_path_or_output` | security |
| TC-T3-003 | NFR-006 | T3 | `tests/video/test_capture.py::test_promotes_only_reviewed_exact_bytes` | regression |
| TC-T3-004 | FR-004, C-003, IR-001, DR-001 | T3 | `tests/video/test_capture.py::test_records_real_editor_capture_provenance` | authenticity |
| TC-T3-005 | C-006, DR-001 | T3 | `tests/video/test_capture.py::test_streams_tracked_teaching_defect_with_synthetic_filename` | integration |
| TC-T4-001 | FR-004, FR-005 | T4 | `tests/video/test_runner_capture.py::test_accepts_only_exact_clean_guarded_codex_run` | integration |
| TC-T4-002 | FR-005 | T4 | `tests/video/test_runner_capture.py::test_falls_back_to_verified_preflight` | regression |
| TC-T4-003 | NFR-008 | T4 | `tests/video/test_runner_capture.py::test_runner_record_excludes_credentials` | security |
| TC-T5-001 | FR-001, FR-002, NFR-006 | T5 | `tests/video/test_scenes.py::test_scenes_are_deterministic_and_provenanced` | unit |
| TC-T5-002 | NFR-003, NFR-004 | T5 | `tests/video/test_scenes.py::test_scene_geometry_and_contrast_are_safe` | unit |
| TC-T5-003 | FR-003, FR-010, NFR-010 | T5 | `tests/video/test_content.py::test_pinned_workflow_disclosure_and_asset_provenance_are_valid` | content |
| TC-T6-001 | FR-006, C-004, IR-002 | T6 | `tests/video/test_speech.py::test_builds_approved_speech_request_with_permission_smoke_record` | contract |
| TC-T6-002 | FR-006, NFR-007, NFR-009, C-007 | T6 | `tests/video/test_speech.py::test_caps_three_full_script_takes_per_unchanged_series` | unit |
| TC-T6-003 | NFR-008, NFR-009 | T6 | `tests/video/test_speech.py::test_take_manifest_and_logs_exclude_key_and_itemized_billing` | security |
| TC-T7-001 | FR-007, NFR-001, NFR-002 | T7 | `tests/video/test_render.py::test_renders_matching_picture_variants` | integration |
| TC-T7-002 | FR-008, FR-011, NFR-007 | T7 | `tests/video/test_render.py::test_builds_variant_caption_and_procedural_audio_graphs` | contract |
| TC-T7-003 | FR-009, NFR-005, DR-003 | T7 | `tests/video/test_render.py::test_rebuilds_changed_scene_and_records_exact_toolchain` | regression |
| TC-T8-001 | NFR-001, NFR-002, NFR-007 | T8 | `tests/video/test_verify.py::test_reports_exact_program_and_variant_loudness` | integration |
| TC-T8-002 | FR-010, FR-011, NFR-003, NFR-004, NFR-006, NFR-008, NFR-010 | T8 | `tests/video/test_verify.py::test_blocks_any_failed_must_or_provenance_gate` | regression |
| TC-T8-003 | NFR-005, DR-003 | T8 | `tests/video/test_verify.py::test_offline_reproduction_requires_recorded_toolchain_and_decoded_hashes` | unit |
| TC-T8-004 | C-003 | T8 | `tests/video/test_verify.py::test_real_evidence_frame_share_is_inclusive_60_to_80_percent` | property-like |
| TC-T9-001 | FR-009 | T9 | `tests/video/test_cli.py::test_stage_commands_share_manifest_and_exit_codes` | contract |
| TC-T9-002 | NFR-008 | T9 | `tests/video/test_cli.py::test_dry_run_is_write_free_and_redacted` | security |
| TC-T9-003 | NFR-005 | T9 | `tests/video/test_cli.py::test_fixture_all_run_is_reproducible` | end-to-end |
| TC-T10-001 | FR-001, FR-002, FR-003, FR-008, FR-010, NFR-010 | T10 | `tests/video/test_content.py::test_final_scene_source_and_asset_ledger` | content |
| TC-T10-002 | FR-004, FR-005, NFR-006 | T10 | `tests/video/test_content.py::test_final_evidence_reproduces` | integration |
| TC-T10-003 | NFR-003, NFR-004, NFR-008 | T10 | `tests/video/test_content.py::test_final_scene_assets_are_safe` | content |
| TC-T11-001 | NFR-009 | T11 | `video_pipeline all --dry-run` evidence | operational |
| TC-T11-002 | FR-006, NFR-007 | T11 | narration review, frame-budget check, WAV probe, and selected-WAV checksum evidence | operational |
| TC-T11-003 | FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005 | T11 | candidate verification report | end-to-end |
| TC-T12-001 | FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, NFR-001, NFR-002, NFR-005, NFR-007 | T12 | final verification, `delivery.json`, provenance, and checksum report | end-to-end |
| TC-T12-002 | FR-001, FR-002, FR-010, NFR-003, NFR-004, NFR-006 | T12 | owner playback and frame review | acceptance |
| TC-T12-003 | NFR-008, NFR-009, NFR-010 | T12 | secret, non-itemized cost, asset-rights, and delivery-scope review | security |
| TC-T12-004 | FR-006, FR-007, IR-005 | T12 | AW-004 interim filename, status, applicable-gate, and owner-acceptance review | acceptance |
| TC-T12-005 | NFR-005 | T12 | fixture rollback rehearsal report with old/new manifest and checksum sets | recovery |

### Appendix C. Deferred Work

| Item | Reason deferred | Follow-up |
| --- | --- | --- |
| Hosted publication | Requires a separate destination and authorization decision. | Reopen `SPEC-NSBJ` OQ-001 after local acceptance. |
| Venue-specific transcode | No venue delivery profile has been supplied. | Reopen `SPEC-NSBJ` OQ-002 when requirements arrive. |
| Social aspect ratios and translations | Outside the approved conference v1. | Track only after a named channel or audience exists. |
