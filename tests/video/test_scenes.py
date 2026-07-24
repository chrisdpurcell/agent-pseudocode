"""Behavior contracts for deterministic, conference-safe scene composition."""

from __future__ import annotations

import binascii
import hashlib
import json
import math
import struct
import zlib
from dataclasses import replace
from pathlib import Path
from typing import cast
from xml.etree import ElementTree

import pytest

from video_pipeline.captions import load_narration
from video_pipeline.capture import EditorEvidence, EditorFrame, verify_evidence_manifest
from video_pipeline.manifest import load_project
from video_pipeline.models import Rectangle

REPOSITORY_ROOT = Path(__file__).parents[2]
PRODUCTION_ROOT = REPOSITORY_ROOT / "media" / "repository-explainer"
PROJECT_PATH = PRODUCTION_ROOT / "project.json"
NARRATION_PATH = PRODUCTION_ROOT / "narration.json"
CAPTURE_MANIFEST_PATH = PRODUCTION_ROOT / "captures" / "manifest.json"
THEME_PATH = PRODUCTION_ROOT / "theme.json"
ASSET_PROVENANCE_PATH = PRODUCTION_ROOT / "asset-provenance.json"
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


def _temporary_editor_png() -> bytes:
    """Return an unmistakable test-only 1920x1080 PNG without production pixels."""
    width, height = 1920, 1080
    row = b"\x00" + b"\xff\x00\xff" * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(row * height, level=9))
        + _png_chunk(b"IEND", b"")
    )


def _test_editor_evidence(tmp_path: Path, source_sha256: str) -> EditorEvidence:
    fixture_path = tmp_path / "TEST-ONLY-NOT-PRODUCTION-editor-substrate.png"
    fixture_path.write_bytes(_temporary_editor_png())
    fixture_hash = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    frame = EditorFrame(
        id="TEST-ONLY-TEMPORARY-FRAME",
        path=fixture_path,
        png_sha256=fixture_hash,
        first_line=1,
        last_line=27,
        source_range_sha256=source_sha256,
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
        frames=(frame, frame),
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
    editor = _test_editor_evidence(tmp_path, teaching.source_sha256 or "")
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
    assert len(first) == 12
    assert [state.digest for state in first] == [state.digest for state in second]
    for scene in project.scenes:
        primary = next(
            state
            for state in first
            if state.scene_id == scene.id and state.state_id != "mute_safe_copy"
        )
        assert primary.evidence_rectangles == scene.visual_states[0].evidence_rectangles
        assert hashlib.sha256(primary.svg).hexdigest() == primary.digest
        root = ElementTree.fromstring(primary.svg)
        assert root.attrib["width"] == "1920"
        assert root.attrib["height"] == "1080"
        assert root.attrib["viewBox"] == "0 0 1920 1080"
        assert all(reference.sha256 for reference in primary.references)
        assert set(primary.asset_ids) <= assets.ids

    teaching = next(state for state in first if state.scene_id == "caught-defect")
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
    mismatched_scene = replace(workflow_scene, visual_states=(mismatched_state,))
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
                    or bottom > safe.y + safe.height
                ):
                    violations.append(
                        f"{state.scene_id}/{state.state_id}: "
                        f"{(run.text or '')!r} -> {(left, top, right, bottom)}"
                    )

    assert not violations, "\n".join(violations)


def test_tc_t5_002__wrapped_code_tspans__preserve_exact_semantic_line_ledgers(
    tmp_path: Path,
) -> None:
    _, _, evidence, _, _, states = _render_test_states(tmp_path)
    code_blocks: dict[str, ElementTree.Element] = {}
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
            code_blocks[state.scene_id] = blocks[0]

    assert set(code_blocks) == {"caught-defect", "shared-policy", "guarded-execution"}
    for block in code_blocks.values():
        assert _exact_line_ledger(block)

    teaching = next(command for command in evidence.commands if command.id == "teaching-defect")
    teaching_source = teaching.source_path
    assert teaching_source is not None
    exact_teaching_lines = [
        "$ "
        + "uv run apseudo-lint --stdin-filename "
        + "tests/fixtures/invalid/unbounded_while.apseudo "
        + "< tests/fixtures/invalid/unbounded_while.apseudo",
        "",
        *(REPOSITORY_ROOT / teaching_source).read_text(encoding="utf-8").splitlines(),
        "",
        *teaching.promoted_outputs[0].path.read_text(encoding="utf-8").splitlines(),
    ]
    encoded_lines = _exact_line_ledger(code_blocks["caught-defect"])
    assert encoded_lines == exact_teaching_lines
    assert [span.text or "" for span in code_blocks["caught-defect"]] != exact_teaching_lines


def test_tc_t5_003__editor_substrate__uses_native_crop_without_scene_copy(
    tmp_path: Path,
) -> None:
    _, narration, evidence, _, _, states = _render_test_states(tmp_path)
    editor_state = next(
        state
        for state in states
        if state.scene_id == "visible-workflow" and state.state_id != "mute_safe_copy"
    )
    editor = evidence.editor
    assert editor is not None
    root = ElementTree.fromstring(editor_state.svg)
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
    assert image.attrib["data-source-sha256"] == editor.frames[0].png_sha256
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
    assert workflow_copy not in _normalized_text(editor_state.svg)


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
