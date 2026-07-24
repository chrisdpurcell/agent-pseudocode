"""Behavior contracts for deterministic, conference-safe scene composition."""

from __future__ import annotations

import binascii
import hashlib
import json
import math
import struct
import subprocess
import sys
import zlib
from dataclasses import replace
from pathlib import Path
from typing import cast
from xml.etree import ElementTree

import pytest

from video_pipeline.captions import load_narration
from video_pipeline.capture import EditorEvidence, EditorFrame, verify_evidence_manifest
from video_pipeline.manifest import load_project
from video_pipeline.models import ProjectManifest, Rectangle
from video_pipeline.scenes import RenderedSceneState

REPOSITORY_ROOT = Path(__file__).parents[2]
PRODUCTION_ROOT = REPOSITORY_ROOT / "media" / "repository-explainer"
PROJECT_PATH = PRODUCTION_ROOT / "project.json"
NARRATION_PATH = PRODUCTION_ROOT / "narration.json"
CAPTURE_MANIFEST_PATH = PRODUCTION_ROOT / "captures" / "manifest.json"
THEME_PATH = PRODUCTION_ROOT / "theme.json"
ASSET_PROVENANCE_PATH = PRODUCTION_ROOT / "asset-provenance.json"
APPROVED_DIGESTS_PATH = Path(__file__).with_name("fixtures") / "approved-scene-digests.json"
CAPTION_RECTANGLE = Rectangle(x=96, y=864, width=1728, height=162)
# Mirrors the renderer's pinned Noto Sans Mono ASCII advance so these tests
# estimate each actual SVG text run instead of trusting declared rectangles.
MONO_GLYPH_ADVANCE_EM = 0.6
SANS_GLYPH_ESTIMATE_EM = 0.65


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return (
        struct.pack(">I", len(payload))
        + body
        + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)
    )


def _temporary_editor_png(rgb: bytes) -> bytes:
    """Return an unmistakable test-only 1920x1080 PNG without production pixels."""
    width, height = 1920, 1080
    row = b"\x00" + rgb * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(row * height, level=9))
        + _png_chunk(b"IEND", b"")
    )


def _test_editor_evidence(tmp_path: Path, source: bytes, source_sha256: str) -> EditorEvidence:
    source_lines = source.splitlines(keepends=True)
    frames: list[EditorFrame] = []
    for frame_id, first_line, last_line, color in (
        ("editor-lines-1-14", 1, 14, b"\xff\x00\xff"),
        ("editor-lines-15-27", 15, 27, b"\x00\xff\xff"),
    ):
        fixture_path = tmp_path / f"TEST-ONLY-NOT-PRODUCTION-{frame_id}.png"
        fixture_path.write_bytes(_temporary_editor_png(color))
        fixture_hash = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        frames.append(
            EditorFrame(
                id=frame_id,
                path=fixture_path,
                png_sha256=fixture_hash,
                first_line=first_line,
                last_line=last_line,
                source_range_sha256=hashlib.sha256(
                    b"".join(source_lines[first_line - 1 : last_line])
                ).hexdigest(),
                spectacle_argv=(
                    "spectacle",
                    "--current",
                    "--background",
                    "--nonotify",
                    "--output",
                    str(fixture_path),
                ),
                output_argument=str(fixture_path),
            )
        )
    return EditorEvidence(
        operator_role="TEST-ONLY fixture creator",
        application="TEST-ONLY synthetic substrate",
        application_version="0",
        capture_tool="TEST-ONLY Python fixture",
        capture_tool_version="0",
        captured_at="1970-01-01T00:00:00Z",
        settings={"TEST-ONLY": True},
        viewport=(0, 0, 1920, 1080),
        source_crop=(0, 120, 1728, 786),
        destination_rectangle=(96, 54, 1728, 786),
        evidence_rectangle=(96, 54, 1728, 786),
        caption_rectangle=(96, 864, 1728, 162),
        native_scale=1.0,
        monitor_count=1,
        palette_foreground="#FFFFFF",
        palette_background="#000000",
        source_path="docs/apseudo-docs/examples/review-loop.apseudo",
        source_sha256=source_sha256,
        frames=tuple(frames),
    )


def _render_test_states(tmp_path: Path):
    try:
        from video_pipeline.scenes import (
            load_asset_catalog,
            load_theme,
            render_scene_states,
        )
    except ModuleNotFoundError:
        pytest.fail("scene renderer is missing")
    project = load_project(PROJECT_PATH)
    narration = load_narration(NARRATION_PATH, project)
    evidence = verify_evidence_manifest(
        CAPTURE_MANIFEST_PATH,
        repository_root=REPOSITORY_ROOT,
        allow_blocked_editor=True,
    )
    teaching = next(command for command in evidence.commands if command.id == "hero-lint")
    hero = subprocess.run(
        ["git", "show", f"{evidence.revision}:docs/apseudo-docs/examples/review-loop.apseudo"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    editor = _test_editor_evidence(tmp_path, hero, teaching.source_sha256 or "")
    evidence = replace(evidence, editor=editor, editor_blocker=None)
    theme = load_theme(THEME_PATH)
    assets = load_asset_catalog(ASSET_PROVENANCE_PATH, repository_root=REPOSITORY_ROOT)
    states = render_scene_states(
        repository_root=REPOSITORY_ROOT,
        project=project,
        narration=narration,
        evidence=evidence,
        theme=theme,
        assets=assets,
    )
    return project, narration, evidence, theme, assets, states


def _normalized_text(svg: bytes) -> str:
    root = ElementTree.fromstring(svg)
    return " ".join(" ".join(root.itertext()).split())


def _exact_line_ledger(text_element: ElementTree.Element) -> list[str]:
    value: object = json.loads(text_element.attrib["data-exact-lines-json"])
    assert isinstance(value, list)
    values = cast(list[object], value)
    assert all(isinstance(line, str) for line in values)
    return cast(list[str], values)


def _estimated_text_width(text: str, family: str, font_size: int) -> float:
    advance = MONO_GLYPH_ADVANCE_EM if family == "Noto Sans Mono" else SANS_GLYPH_ESTIMATE_EM
    return len(text) * font_size * advance


def _text_run_bounds(
    text_element: ElementTree.Element,
    run: ElementTree.Element,
) -> tuple[int, int, int, int]:
    text = run.text or ""
    font_size = int(text_element.attrib["font-size"])
    width = _estimated_text_width(text, text_element.attrib["font-family"], font_size)
    x = int(run.attrib.get("x", text_element.attrib["x"]))
    y = int(run.attrib.get("y", text_element.attrib["y"]))
    anchor = text_element.attrib.get("text-anchor", "start")
    if anchor == "middle":
        left = x - width / 2
        right = x + width / 2
    elif anchor == "end":
        left = x - width
        right = x
    else:
        left = x
        right = x + width
    return math.floor(left), y - font_size, math.ceil(right), y + math.ceil(font_size * 0.25)


def _state_timeline(
    project_or_states: ProjectManifest | tuple[RenderedSceneState, ...],
) -> list[tuple[str, str, int, int]]:
    if isinstance(project_or_states, ProjectManifest):
        return [
            (scene.id, state.id, state.start_frame, state.end_frame)
            for scene in project_or_states.scenes
            for state in scene.visual_states
        ]
    return [
        (state.scene_id, state.state_id, state.start_frame, state.end_frame)
        for state in project_or_states
    ]


def test_tc_t5_001__fixed_inputs__produce_deterministic_provenanced_geometry(
    tmp_path: Path,
) -> None:
    project, narration, evidence, theme, assets, first = _render_test_states(tmp_path)
    from video_pipeline.scenes import SceneError, render_scene_states

    second = render_scene_states(
        repository_root=REPOSITORY_ROOT,
        project=project,
        narration=narration,
        evidence=evidence,
        theme=theme,
        assets=assets,
    )

    assert first == second
    assert len(first) == sum(len(scene.visual_states) for scene in project.scenes)
    assert _state_timeline(first) == _state_timeline(project)
    assert [state.digest for state in first] == [state.digest for state in second]
    for state in first:
        manifest_state = next(
            manifest_state
            for scene in project.scenes
            for manifest_state in scene.visual_states
            if scene.id == state.scene_id and manifest_state.id == state.state_id
        )
        assert state.evidence_rectangles == manifest_state.evidence_rectangles
        assert hashlib.sha256(state.svg).hexdigest() == state.digest
        root = ElementTree.fromstring(state.svg)
        assert root.attrib["width"] == "1920"
        assert root.attrib["height"] == "1080"
        assert root.attrib["viewBox"] == "0 0 1920 1080"
        assert root.attrib["data-state-id"] == state.state_id
        assert all(reference.sha256 for reference in state.references)
        assert set(state.asset_ids) <= assets.ids

    teaching = next(state for state in first if state.state_id == "teaching-source")
    assert (
        teaching.display_text
        == "uv run apseudo-lint --stdin-filename tests/fixtures/invalid/unbounded_while.apseudo "
        "< tests/fixtures/invalid/unbounded_while.apseudo"
    )
    runner = next(state for state in first if state.scene_id == "guarded-execution")
    runner_commands = (
        REPOSITORY_ROOT
        / "media"
        / "repository-explainer"
        / "captures"
        / "evidence"
        / "runner"
        / "runner-commands.json"
    )
    assert (
        runner.display_text
        == json.loads(runner_commands.read_text(encoding="utf-8"))["display"]["command"]
    )
    assert "/home/" not in runner.display_text

    workflow_scene = project.scenes[1]
    mismatched_state = replace(
        workflow_scene.visual_states[0],
        evidence_rectangles=(Rectangle(x=120, y=90, width=1680, height=840),),
    )
    mismatched_scene = replace(
        workflow_scene,
        visual_states=(mismatched_state, *workflow_scene.visual_states[1:]),
    )
    scenes = list(project.scenes)
    scenes[1] = mismatched_scene
    mismatched_project = replace(project, scenes=tuple(scenes))

    with pytest.raises(SceneError, match="editor destination/evidence geometry"):
        render_scene_states(
            repository_root=REPOSITORY_ROOT,
            project=mismatched_project,
            narration=narration,
            evidence=evidence,
            theme=theme,
            assets=assets,
        )


def test_tc_t5_002__all_states__meet_safe_geometry_contrast_and_mute_copy(
    tmp_path: Path,
) -> None:
    from video_pipeline.scenes import (
        COPY_RECTANGLE,
        MIN_MUTE_SAFE_FRAMES,
        contrast_ratio,
    )

    project, narration, _, theme, _, states = _render_test_states(tmp_path)
    safe = project.safe_area.rectangle
    narration_by_scene = {segment.scene_id: segment for segment in narration.segments}

    assert theme.code_size >= 32
    assert theme.caption_size >= 44
    assert all(
        contrast_ratio(theme.colors[foreground], theme.colors[background]) >= 4.5
        for foreground, background in theme.contrast_pairs
    )
    for state in states:
        root = ElementTree.fromstring(state.svg)
        assert all(
            int(element.attrib["font-size"]) >= 32
            for element in root.iter()
            if "font-size" in element.attrib
        )
        assert all(
            rectangle.x >= safe.x
            and rectangle.y >= safe.y
            and rectangle.x + rectangle.width <= safe.x + safe.width
            and rectangle.y + rectangle.height <= safe.y + safe.height
            for rectangle in state.essential_rectangles
        )

    for scene in project.scenes:
        mute = next(
            state
            for state in states
            if state.scene_id == scene.id and state.state_id == "mute_safe_copy"
        )
        expected_copy = narration_by_scene[scene.id].mute_safe_copy
        assert mute.end_frame - mute.start_frame >= MIN_MUTE_SAFE_FRAMES
        assert mute.evidence_rectangles == ()
        assert mute.copy_rectangle == COPY_RECTANGLE
        assert mute.caption_rectangle == CAPTION_RECTANGLE
        assert mute.display_text == expected_copy
        assert expected_copy in _normalized_text(mute.svg)
        assert b'data-caption-clear="true"' in mute.svg


def test_tc_t5_002__every_svg_text_run__stays_inside_title_safe_area(
    tmp_path: Path,
) -> None:
    project, _, _, _, _, states = _render_test_states(tmp_path)
    safe = project.safe_area.rectangle
    violations: list[str] = []

    for state in states:
        root = ElementTree.fromstring(state.svg)
        for text_element in root.iter():
            if not text_element.tag.endswith("text"):
                continue
            runs = [child for child in text_element if child.tag.endswith("tspan")] or [
                text_element
            ]
            for run in runs:
                left, top, right, bottom = _text_run_bounds(text_element, run)
                if (
                    left < safe.x
                    or top < safe.y
                    or right > safe.x + safe.width
                    or bottom > CAPTION_RECTANGLE.y
                ):
                    violations.append(
                        f"{state.scene_id}/{state.state_id}: "
                        f"{(run.text or '')!r} -> {(left, top, right, bottom)}"
                    )

    assert not violations, "\n".join(violations)


def test_tc_t5_002__actual_regular_font_bounds_and_resolution__match_every_text_run(
    tmp_path: Path,
) -> None:
    try:
        from video_pipeline.text_metrics import (
            TextMetricError,
            measure_text_bounds,
            probe_text_metric_capabilities,
            resolve_regular_font,
        )
    except ModuleNotFoundError:
        pytest.fail("declared FFmpeg/fontconfig text-metric probe is missing")

    _, _, _, _, assets, states = _render_test_states(tmp_path)
    sans = assets.require("noto-sans-regular")
    mono = assets.require("noto-sans-mono-regular")
    capabilities = probe_text_metric_capabilities()
    expected_paths = {
        "Noto Sans": sans.path,
        "Noto Sans Mono": mono.path,
    }
    for family, asset in (("Noto Sans", sans), ("Noto Sans Mono", mono)):
        assert resolve_regular_font(family, capabilities=capabilities) == asset.path
        assert hashlib.sha256(asset.path.read_bytes()).hexdigest() == asset.sha256
    policy_map = ElementTree.fromstring(assets.require("policy-map").path.read_bytes())
    assert all("font-weight" not in element.attrib for element in policy_map.iter())

    with pytest.raises(TextMetricError, match="ffmpeg executable was not found"):
        probe_text_metric_capabilities(ffmpeg="definitely-missing-ffmpeg-for-test")
    with pytest.raises(TextMetricError, match="fc-match executable was not found"):
        probe_text_metric_capabilities(fontconfig="definitely-missing-fontconfig-for-test")

    for state in states:
        root = ElementTree.fromstring(state.svg)
        assert all("font-weight" not in element.attrib for element in root.iter())
        for text_element in root.iter():
            if not text_element.tag.endswith("text"):
                continue
            runs = [child for child in text_element if child.tag.endswith("tspan")] or [
                text_element
            ]
            for run in runs:
                if not (run.text or "").strip():
                    continue
                bounds = measure_text_bounds(
                    run.text or "",
                    font_path=expected_paths[text_element.attrib["font-family"]],
                    font_size=int(text_element.attrib["font-size"]),
                    x=int(run.attrib.get("x", text_element.attrib["x"])),
                    baseline=int(run.attrib.get("y", text_element.attrib["y"])),
                    anchor=text_element.attrib.get("text-anchor", "start"),
                    capabilities=capabilities,
                )
                assert bounds.left >= 96
                assert bounds.top >= 54
                assert bounds.right <= 1824
                assert bounds.bottom <= CAPTION_RECTANGLE.y


def test_tc_t5_002__video_python__has_no_external_image_tool_dependency() -> None:
    forbidden = "mag" + "ick"
    paths = (
        *(REPOSITORY_ROOT / "media" / "repository-explainer" / "video_pipeline").glob("*.py"),
        *(REPOSITORY_ROOT / "tests" / "video").glob("*.py"),
    )
    offenders = [
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path in paths
        if forbidden in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []


def test_tc_t5_002__wrapped_code_tspans__preserve_exact_semantic_line_ledgers(
    tmp_path: Path,
) -> None:
    _, _, evidence, _, _, states = _render_test_states(tmp_path)
    code_blocks: dict[tuple[str, str], ElementTree.Element] = {}
    for state in states:
        root = ElementTree.fromstring(state.svg)
        blocks = [
            element
            for element in root.iter()
            if element.tag.endswith("text")
            and element.attrib.get("font-family") == "Noto Sans Mono"
        ]
        if blocks:
            assert len(blocks) == 1
            code_blocks[(state.scene_id, state.state_id)] = blocks[0]

    assert set(code_blocks) == {
        ("caught-defect", "teaching-source"),
        ("caught-defect", "teaching-diagnostics"),
        ("shared-policy", "system-map"),
        ("guarded-execution", "runner"),
    }
    for block in code_blocks.values():
        assert _exact_line_ledger(block)

    teaching = next(command for command in evidence.commands if command.id == "teaching-defect")
    teaching_source = teaching.source_path
    assert teaching_source is not None
    exact_source_lines = [
        "$ "
        + "uv run apseudo-lint --stdin-filename "
        + "tests/fixtures/invalid/unbounded_while.apseudo "
        + "< tests/fixtures/invalid/unbounded_while.apseudo",
        *(REPOSITORY_ROOT / teaching_source).read_text(encoding="utf-8").splitlines(),
    ]
    exact_diagnostic_lines = (
        teaching.promoted_outputs[0].path.read_text(encoding="utf-8").splitlines()
    )
    source_block = code_blocks[("caught-defect", "teaching-source")]
    diagnostic_block = code_blocks[("caught-defect", "teaching-diagnostics")]
    assert _exact_line_ledger(source_block) == exact_source_lines
    assert _exact_line_ledger(diagnostic_block) == exact_diagnostic_lines
    assert max(int(span.attrib["y"]) for span in source_block) < CAPTION_RECTANGLE.y
    assert max(int(span.attrib["y"]) for span in diagnostic_block) < CAPTION_RECTANGLE.y


def test_tc_t5_003__editor_substrate__uses_native_crop_without_scene_copy(
    tmp_path: Path,
) -> None:
    _, narration, evidence, _, _, states = _render_test_states(tmp_path)
    editor = evidence.editor
    assert editor is not None
    editor_states = [
        state
        for state in states
        if state.scene_id == "visible-workflow" and state.state_id != "mute_safe_copy"
    ]
    assert [state.state_id for state in editor_states] == [frame.id for frame in editor.frames]
    for state, frame in zip(editor_states, editor.frames, strict=True):
        root = ElementTree.fromstring(state.svg)
        image = next(element for element in root.iter() if element.tag.endswith("image"))
        clip_rect = next(
            element
            for element in root.iter()
            if element.tag.endswith("rect") and element.attrib.get("id") == "editor-native-crop"
        )
        assert image.attrib["x"] == "96"
        assert image.attrib["y"] == "-66"
        assert image.attrib["width"] == "1920"
        assert image.attrib["height"] == "1080"
        assert image.attrib["data-native-scale"] == "1"
        assert image.attrib["data-source-sha256"] == frame.png_sha256
        assert image.attrib["data-editor-frame-id"] == frame.id
        assert image.attrib["data-source-range"] == f"{frame.first_line}-{frame.last_line}"
        assert clip_rect.attrib == {
            "id": "editor-native-crop",
            "x": "96",
            "y": "54",
            "width": "1728",
            "height": "786",
        }
    workflow_copy = next(
        segment.mute_safe_copy
        for segment in narration.segments
        if segment.scene_id == "visible-workflow"
    )
    assert all(workflow_copy not in _normalized_text(state.svg) for state in editor_states)


def test_tc_t5_003__state_content_and_asset_ledgers__close_every_reference(
    tmp_path: Path,
) -> None:
    _, _, _, theme, assets, states = _render_test_states(tmp_path)
    for state in states:
        root = ElementTree.fromstring(state.svg)
        ledger_value: object = json.loads(root.attrib["data-content-ledger-json"])
        assert isinstance(ledger_value, list)
        ledger = cast(list[object], ledger_value)
        assert ledger and all(isinstance(value, str) and value for value in ledger)
        assert tuple(ledger) == getattr(state, "content_ledger", None)
        assert state.display_text in ledger
        assert state.references
        for reference in state.references:
            path_text = reference.path.split("#", maxsplit=1)[0]
            path = Path(path_text)
            assert not path.is_absolute()
            assert ".." not in path.parts
        expected_fonts = (
            {theme.font_mono_asset_id}
            if state.scene_id == "visible-workflow" and state.state_id != "mute_safe_copy"
            else {theme.font_sans_asset_id, theme.font_mono_asset_id}
            if state.scene_id in {"caught-defect", "shared-policy", "guarded-execution"}
            and state.state_id != "mute_safe_copy"
            else {theme.font_sans_asset_id}
        )
        assert expected_fonts <= set(state.asset_ids)
        for asset_id in state.asset_ids:
            asset = assets.require(asset_id)
            assert any(
                reference.kind == "asset"
                and reference.sha256 == asset.sha256
                and reference.path.endswith(f"#asset={asset_id}")
                for reference in state.references
            )


def test_tc_t5_003__renderer_labels__come_from_one_tracked_content_source(
    tmp_path: Path,
) -> None:
    try:
        from video_pipeline.scene_content import (
            POLICY_LABEL,
            POLICY_MAP_LABELS,
            PROBLEM_LABEL,
            RUNNER_ACCEPTED_LABEL,
            RUNNER_PREFLIGHT_LABEL,
            TEACHING_LABEL,
        )
    except ModuleNotFoundError:
        pytest.fail("tracked renderer-authored scene content source is missing")

    *_, states = _render_test_states(tmp_path)
    relative_path = Path("media/repository-explainer/video_pipeline/scene_content.py")
    content_path = REPOSITORY_ROOT / relative_path
    content_hash = hashlib.sha256(content_path.read_bytes()).hexdigest()
    expected_labels = {
        ("problem", "question"): (PROBLEM_LABEL,),
        ("caught-defect", "teaching-source"): (TEACHING_LABEL,),
        ("caught-defect", "teaching-diagnostics"): (TEACHING_LABEL,),
        ("shared-policy", "system-map"): (POLICY_LABEL, *POLICY_MAP_LABELS),
        ("guarded-execution", "runner"): (
            RUNNER_PREFLIGHT_LABEL,
            RUNNER_ACCEPTED_LABEL,
        ),
    }
    scenes_source = (
        REPOSITORY_ROOT / "media/repository-explainer/video_pipeline/scenes.py"
    ).read_text(encoding="utf-8")

    for state in states:
        labels = expected_labels.get((state.scene_id, state.state_id))
        references = [
            reference
            for reference in state.references
            if reference.path == relative_path.as_posix()
        ]
        if labels is None:
            assert references == []
            continue
        assert len(references) == 1
        assert references[0].kind == "source"
        assert references[0].sha256 == content_hash
        present = tuple(label for label in labels if label in state.content_ledger)
        assert present
        if state.scene_id != "guarded-execution":
            assert present == labels
        else:
            assert len(present) == 1

    renderer_labels = (
        PROBLEM_LABEL,
        TEACHING_LABEL,
        POLICY_LABEL,
        RUNNER_PREFLIGHT_LABEL,
        RUNNER_ACCEPTED_LABEL,
    )
    assert all(label not in scenes_source for label in renderer_labels)


def test_tc_t5_003__mutated_verified_assets_and_runner_bytes__fail_closed(
    tmp_path: Path,
) -> None:
    project, narration, evidence, theme, assets, _ = _render_test_states(tmp_path)
    from video_pipeline.scenes import SceneError, render_scene_states

    policy = assets.require("policy-map")
    asset_path = tmp_path / "mutated-policy-map.svg"
    asset_path.write_bytes(policy.path.read_bytes())
    replaced_policy = replace(policy, repository_path=None, system_path=asset_path)
    mutated_assets = replace(
        assets,
        assets=tuple(
            replaced_policy if asset.id == policy.id else asset for asset in assets.assets
        ),
    )
    asset_path.write_bytes(asset_path.read_bytes() + b"\n")
    with pytest.raises(SceneError, match="asset bytes changed"):
        render_scene_states(
            repository_root=REPOSITORY_ROOT,
            project=project,
            narration=narration,
            evidence=evidence,
            theme=theme,
            assets=mutated_assets,
        )

    runner = evidence.runner
    assert runner is not None
    commands = next(
        record for record in runner.evidence if record.path.name == "runner-commands.json"
    )
    runner_path = tmp_path / "runner-commands.json"
    runner_path.write_bytes(commands.path.read_bytes())
    replaced_commands = replace(commands, path=runner_path)
    mutated_runner = replace(
        runner,
        evidence=tuple(
            replaced_commands if record.path.name == "runner-commands.json" else record
            for record in runner.evidence
        ),
    )
    runner_path.write_bytes(runner_path.read_bytes() + b"\n")
    with pytest.raises(SceneError, match="runner evidence bytes changed"):
        render_scene_states(
            repository_root=REPOSITORY_ROOT,
            project=project,
            narration=narration,
            evidence=replace(evidence, runner=mutated_runner),
            theme=theme,
            assets=assets,
        )


def test_tc_t5_003__approved_state_digests__match_across_fresh_processes(
    tmp_path: Path,
) -> None:
    assert APPROVED_DIGESTS_PATH.exists(), "approved per-state digest fixture is missing"
    approved = json.loads(APPROVED_DIGESTS_PATH.read_text(encoding="utf-8"))
    script = """
import json
import sys
import tempfile
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root / "media/repository-explainer"))
sys.path.insert(0, str(root / "tests/video"))
from test_scenes import _render_test_states
with tempfile.TemporaryDirectory(prefix="scene-digest-") as directory:
    *_, states = _render_test_states(Path(directory))
print(json.dumps({f"{state.scene_id}/{state.state_id}": state.digest for state in states}, sort_keys=True))
"""
    runs = [
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout.strip()
        for _ in range(2)
    ]
    assert runs[0] == runs[1]
    assert json.loads(runs[0]) == approved


def test_compose_scene_states__blocked_editor__reports_locked_editor_only() -> None:
    from video_pipeline.scenes import (
        PRODUCTION_EDITOR_BLOCKER,
        SceneBlockedError,
        compose_scene_states,
    )

    with pytest.raises(
        SceneBlockedError,
        match="KDE session is locked; owner-authenticated unlock is required",
    ) as caught:
        compose_scene_states(REPOSITORY_ROOT)
    assert (
        str(caught.value) == f"{PRODUCTION_EDITOR_BLOCKER}: editor: blocked: "
        "KDE session is locked; owner-authenticated unlock is required"
    )
