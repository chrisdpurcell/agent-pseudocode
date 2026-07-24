"""Compose deterministic SVG scene states from repository-owned truth surfaces.

The production entry point accepts no substitute editor image: capture validation
must first return the real revision-bound VS Code evidence. The pure renderer takes
that typed evidence as an explicit dependency so tests can exercise crop, geometry,
and serialization with temporary bytes that never enter the production manifest or
asset ledger.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
import struct
import subprocess
import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from xml.etree import ElementTree

from .captions import NarrationPackage, NarrationSegment, load_narration
from .capture import (
    CAPTION_RECTANGLE as CAPTURE_CAPTION_RECTANGLE,
)
from .capture import (
    HERO_SOURCE_PATH,
    SOURCE_CROP,
    CaptureError,
    CommandEvidence,
    EditorEvidence,
    EvidenceManifest,
    verify_evidence_manifest,
)
from .manifest import load_project
from .models import ProjectManifest, Rectangle, Scene
from .runner_capture import RunnerCaptureError, expand_display_command

type AssetKind = Literal["audio", "font", "graphic"]
type ReferenceKind = Literal["asset", "capture", "narration", "source", "theme"]

PRODUCTION_EDITOR_BLOCKER = "LOCKED-EDITOR BLOCKER"
MIN_MUTE_SAFE_FRAMES = 60
COPY_RECTANGLE = Rectangle(x=240, y=270, width=1440, height=540)
CAPTION_RECTANGLE = Rectangle(x=96, y=864, width=1728, height=162)
TITLE_SAFE_RECTANGLE = Rectangle(x=96, y=54, width=1728, height=972)
EDITOR_RECTANGLE = Rectangle(x=96, y=54, width=1728, height=786)
TEACHING_DEFECT_PATH = "tests/fixtures/invalid/unbounded_while.apseudo"
TEACHING_COMMAND_ID = "teaching-defect"
RUNNER_COMMANDS_NAME = "runner-commands.json"
NARRATION_RELATIVE_PATH = Path("media/repository-explainer/narration.json")
PROJECT_RELATIVE_PATH = Path("media/repository-explainer/project.json")
THEME_RELATIVE_PATH = Path("media/repository-explainer/theme.json")
CAPTURE_MANIFEST_RELATIVE_PATH = Path("media/repository-explainer/captures/manifest.json")
ASSET_PROVENANCE_RELATIVE_PATH = Path("media/repository-explainer/asset-provenance.json")
_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")

ElementTree.register_namespace("", _SVG_NAMESPACE)


class SceneError(ValueError):
    """Reject missing, mismatched, or untraceable scene input."""


class SceneBlockedError(SceneError):
    """Report an owner-gated production input that has not been captured."""


class _DuplicateJsonKeyError(ValueError):
    """Carry a duplicate key out of the JSON decoder."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(key)


@dataclass(frozen=True, slots=True)
class SceneTheme:
    """Validated colors, typography, and geometry used by every scene."""

    colors: dict[str, str]
    contrast_pairs: tuple[tuple[str, str], ...]
    font_sans: str
    font_sans_asset_id: str
    font_mono: str
    font_mono_asset_id: str
    title_size: int
    copy_size: int
    caption_size: int
    code_size: int
    label_size: int
    title_safe: Rectangle
    copy_rectangle: Rectangle
    caption_rectangle: Rectangle
    mute_safe_frames: int
    source_path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class AssetRecord:
    """One checksummed external or repository-owned rendering input."""

    id: str
    kind: AssetKind
    repository_path: Path | None
    system_path: Path | None
    source: str
    license_id: str | None
    generation_method: str | None
    sha256: str

    @property
    def path(self) -> Path:
        """Return the verified bytes used by the renderer."""
        if self.repository_path is not None:
            return self.repository_path
        if self.system_path is not None:
            return self.system_path
        raise SceneError(f"asset {self.id!r}: no resolved input path")


@dataclass(frozen=True, slots=True)
class AssetCatalog:
    """The complete verified font, graphic, and audio rights ledger."""

    assets: tuple[AssetRecord, ...]
    provenance_path: Path
    provenance_sha256: str

    @property
    def ids(self) -> frozenset[str]:
        """Return the classified asset identifiers."""
        return frozenset(asset.id for asset in self.assets)

    def require(self, asset_id: str) -> AssetRecord:
        """Return a classified asset or fail before composition."""
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        raise SceneError(f"asset-provenance: missing required asset {asset_id!r}")


@dataclass(frozen=True, slots=True)
class ContentReference:
    """A byte hash proving where visible scene content originated."""

    kind: ReferenceKind
    path: str
    sha256: str
    revision: str | None = None


@dataclass(frozen=True, slots=True)
class RenderedSceneState:
    """One frame interval and its byte-stable SVG composite."""

    scene_id: str
    state_id: str
    start_frame: int
    end_frame: int
    svg: bytes
    evidence_rectangles: tuple[Rectangle, ...]
    essential_rectangles: tuple[Rectangle, ...]
    copy_rectangle: Rectangle | None
    caption_rectangle: Rectangle
    display_text: str
    references: tuple[ContentReference, ...]
    asset_ids: tuple[str, ...]

    @property
    def digest(self) -> str:
        """Return the stable SHA-256 of this exact SVG state."""
        return _digest(self.svg)


def load_theme(path: Path) -> SceneTheme:
    """Load the strict conference-safe theme and reject unsafe substitutions."""
    raw, payload = _load_json(path, "theme")
    _exact_fields(
        payload,
        {
            "schema_version",
            "canvas",
            "colors",
            "contrast_pairs",
            "fonts",
            "text_sizes",
            "rectangles",
            "mute_safe_frames",
        },
        "theme",
    )
    if _integer(payload["schema_version"], "theme.schema_version") != 1:
        raise SceneError("theme.schema_version: expected 1")
    canvas = _object(payload["canvas"], "theme.canvas")
    _exact_fields(canvas, {"width", "height"}, "theme.canvas")
    if (
        _integer(canvas["width"], "theme.canvas.width"),
        _integer(canvas["height"], "theme.canvas.height"),
    ) != (1920, 1080):
        raise SceneError("theme.canvas: expected 1920x1080")

    color_values = _object(payload["colors"], "theme.colors")
    colors = {
        key: _color(value, f"theme.colors.{key}") for key, value in sorted(color_values.items())
    }
    required_colors = {"ink", "surface", "surface_alt", "paper", "blue", "mint", "coral"}
    if set(colors) != required_colors:
        raise SceneError(f"theme.colors: expected exactly {sorted(required_colors)!r}")
    contrast_pairs = tuple(
        _contrast_pair(value, index, colors)
        for index, value in enumerate(_array(payload["contrast_pairs"], "theme.contrast_pairs"))
    )
    if not contrast_pairs:
        raise SceneError("theme.contrast_pairs: must not be empty")
    for foreground, background in contrast_pairs:
        if contrast_ratio(colors[foreground], colors[background]) < 4.5:
            raise SceneError(
                f"theme.contrast_pairs: {foreground}/{background} must have at least 4.5:1 contrast"
            )

    fonts = _object(payload["fonts"], "theme.fonts")
    _exact_fields(fonts, {"sans", "mono"}, "theme.fonts")
    sans_family, sans_asset = _font(_object(fonts["sans"], "theme.fonts.sans"), "sans")
    mono_family, mono_asset = _font(_object(fonts["mono"], "theme.fonts.mono"), "mono")

    text_sizes = _object(payload["text_sizes"], "theme.text_sizes")
    _exact_fields(text_sizes, {"title", "copy", "caption", "code", "label"}, "theme.text_sizes")
    title_size = _integer(text_sizes["title"], "theme.text_sizes.title")
    copy_size = _integer(text_sizes["copy"], "theme.text_sizes.copy")
    caption_size = _integer(text_sizes["caption"], "theme.text_sizes.caption")
    code_size = _integer(text_sizes["code"], "theme.text_sizes.code")
    label_size = _integer(text_sizes["label"], "theme.text_sizes.label")
    if min(title_size, copy_size, label_size) < 32:
        raise SceneError("theme.text_sizes: title, copy, and label must be at least 32px")
    if code_size < 32:
        raise SceneError("theme.text_sizes.code: must be at least 32px")
    if caption_size < 44:
        raise SceneError("theme.text_sizes.caption: must be at least 44px")

    rectangles = _object(payload["rectangles"], "theme.rectangles")
    _exact_fields(rectangles, {"title_safe", "copy", "caption"}, "theme.rectangles")
    title_safe = _rectangle(rectangles["title_safe"], "theme.rectangles.title_safe")
    copy_rectangle = _rectangle(rectangles["copy"], "theme.rectangles.copy")
    caption_rectangle = _rectangle(rectangles["caption"], "theme.rectangles.caption")
    if title_safe != TITLE_SAFE_RECTANGLE:
        raise SceneError("theme.rectangles.title_safe: expected the central 90%")
    if copy_rectangle != COPY_RECTANGLE:
        raise SceneError("theme.rectangles.copy: expected [240, 270, 1440, 540]")
    if caption_rectangle != CAPTION_RECTANGLE:
        raise SceneError("theme.rectangles.caption: expected [96, 864, 1728, 162]")
    mute_safe_frames = _integer(payload["mute_safe_frames"], "theme.mute_safe_frames")
    if mute_safe_frames < MIN_MUTE_SAFE_FRAMES:
        raise SceneError("theme.mute_safe_frames: must be at least 60")

    return SceneTheme(
        colors=colors,
        contrast_pairs=contrast_pairs,
        font_sans=sans_family,
        font_sans_asset_id=sans_asset,
        font_mono=mono_family,
        font_mono_asset_id=mono_asset,
        title_size=title_size,
        copy_size=copy_size,
        caption_size=caption_size,
        code_size=code_size,
        label_size=label_size,
        title_safe=title_safe,
        copy_rectangle=copy_rectangle,
        caption_rectangle=caption_rectangle,
        mute_safe_frames=mute_safe_frames,
        source_path=path.resolve(),
        sha256=_digest(raw),
    )


def load_asset_catalog(path: Path, *, repository_root: Path) -> AssetCatalog:
    """Load asset rights, resolve every input, and verify its committed checksum."""
    root = repository_root.resolve()
    raw, payload = _load_json(path, "asset-provenance")
    _exact_fields(payload, {"schema_version", "assets"}, "asset-provenance")
    if _integer(payload["schema_version"], "asset-provenance.schema_version") != 1:
        raise SceneError("asset-provenance.schema_version: expected 1")
    assets = tuple(
        _asset_record(_object(value, f"assets[{index}]"), index, root)
        for index, value in enumerate(_array(payload["assets"], "asset-provenance.assets"))
    )
    if not assets:
        raise SceneError("asset-provenance.assets: must not be empty")
    if len({asset.id for asset in assets}) != len(assets):
        raise SceneError("asset-provenance.assets: ids must be unique")
    catalog = AssetCatalog(
        assets=assets,
        provenance_path=path.resolve(),
        provenance_sha256=_digest(raw),
    )
    for required in ("apseudo-mark", "policy-map", "noto-sans-regular", "noto-sans-mono-regular"):
        catalog.require(required)
    return catalog


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio for two #RRGGBB colors."""
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def compose_scene_states(repository_root: Path) -> tuple[RenderedSceneState, ...]:
    """Load every committed production input and compose all scene states.

    A blocked capture remains a hard production stop. In particular, no generated
    editor facsimile can enter through this entry point because the capture parser
    accepts only its exact real-editor schema and promoted screenshot hashes.
    """
    root = repository_root.resolve()
    production_root = root / "media" / "repository-explainer"
    project = load_project(production_root / "project.json", repository_root=root)
    narration = load_narration(production_root / "narration.json", project)
    try:
        evidence = verify_evidence_manifest(
            production_root / "captures" / "manifest.json",
            repository_root=root,
        )
    except CaptureError as exc:
        message = str(exc)
        if message.startswith("editor: blocked:"):
            raise SceneBlockedError(f"{PRODUCTION_EDITOR_BLOCKER}: {message}") from exc
        raise SceneError(f"capture manifest: {message}") from exc
    theme = load_theme(production_root / "theme.json")
    assets = load_asset_catalog(
        production_root / "asset-provenance.json",
        repository_root=root,
    )
    return render_scene_states(
        repository_root=root,
        project=project,
        narration=narration,
        evidence=evidence,
        theme=theme,
        assets=assets,
    )


def render_scene_states(
    *,
    repository_root: Path,
    project: ProjectManifest,
    narration: NarrationPackage,
    evidence: EvidenceManifest,
    theme: SceneTheme,
    assets: AssetCatalog,
) -> tuple[RenderedSceneState, ...]:
    """Render the six evidence-bound primary states and six mute-safe states."""
    root = repository_root.resolve()
    editor = evidence.editor
    if editor is None:
        blocker = evidence.editor_blocker or "real editor evidence is unavailable"
        raise SceneBlockedError(f"{PRODUCTION_EDITOR_BLOCKER}: {blocker}")
    _validate_cross_inputs(project, narration, evidence, theme, assets)
    commands = {command.id: command for command in evidence.commands}
    teaching = _teaching_inputs(root, evidence.revision, commands)
    runner = _runner_inputs(evidence)
    segments = {segment.scene_id: segment for segment in narration.segments}
    source_cache = {
        scene.id: tuple(
            _source_reference(root, evidence.revision, source_path)
            for source_path in scene.source_paths
        )
        for scene in project.scenes
    }
    theme_reference = _path_reference(root, theme.source_path, "theme")
    narration_reference = _path_reference(
        root,
        root / NARRATION_RELATIVE_PATH,
        "narration",
    )

    rendered: list[RenderedSceneState] = []
    for scene in project.scenes:
        segment = segments[scene.id]
        primary_end = scene.end_frame - theme.mute_safe_frames
        if primary_end <= scene.start_frame:
            raise SceneError(f"scene {scene.id!r}: cannot reserve the mute-safe state")
        manifest_state = scene.visual_states[0]
        context = _SceneContext(
            root=root,
            revision=evidence.revision,
            scene=scene,
            segment=segment,
            theme=theme,
            assets=assets,
            editor=editor,
            teaching=teaching,
            runner=runner,
            source_references=source_cache[scene.id],
            theme_reference=theme_reference,
            narration_reference=narration_reference,
        )
        rendered.append(
            _render_primary(
                context,
                state_id=manifest_state.id,
                start_frame=scene.start_frame,
                end_frame=primary_end,
                evidence_rectangles=manifest_state.evidence_rectangles,
            )
        )
        rendered.append(
            _render_mute_safe(
                context,
                start_frame=primary_end,
                end_frame=scene.end_frame,
            )
        )
    return tuple(rendered)


@dataclass(frozen=True, slots=True)
class _TeachingInputs:
    command: str
    source: bytes
    source_reference: ContentReference
    output: bytes
    output_reference: ContentReference


@dataclass(frozen=True, slots=True)
class _RunnerInputs:
    display_command: str
    mode: str
    reason: str
    references: tuple[ContentReference, ...]


@dataclass(frozen=True, slots=True)
class _SourceInput:
    content: bytes
    reference: ContentReference


@dataclass(frozen=True, slots=True)
class _SceneContext:
    root: Path
    revision: str
    scene: Scene
    segment: NarrationSegment
    theme: SceneTheme
    assets: AssetCatalog
    editor: EditorEvidence
    teaching: _TeachingInputs
    runner: _RunnerInputs
    source_references: tuple[_SourceInput, ...]
    theme_reference: ContentReference
    narration_reference: ContentReference


def _render_primary(
    context: _SceneContext,
    *,
    state_id: str,
    start_frame: int,
    end_frame: int,
    evidence_rectangles: tuple[Rectangle, ...],
) -> RenderedSceneState:
    scene_id = context.scene.id
    references: list[ContentReference] = [
        context.theme_reference,
        context.narration_reference,
        *(source.reference for source in context.source_references),
    ]
    asset_ids: tuple[str, ...] = ()
    if scene_id == "problem":
        svg, display_text, asset_ids = _problem_svg(context)
        essential = (COPY_RECTANGLE,)
    elif scene_id == "visible-workflow":
        svg, display_text, editor_reference = _editor_svg(context, evidence_rectangles)
        references.append(editor_reference)
        essential = evidence_rectangles
    elif scene_id == "caught-defect":
        svg, display_text = _teaching_svg(context, evidence_rectangles)
        references.extend((context.teaching.source_reference, context.teaching.output_reference))
        essential = evidence_rectangles
    elif scene_id == "shared-policy":
        svg, display_text, asset_ids = _policy_svg(context, evidence_rectangles)
        references.append(_asset_reference(context.root, context.assets.require("policy-map")))
        essential = evidence_rectangles
    elif scene_id == "guarded-execution":
        svg, display_text = _runner_svg(context, evidence_rectangles)
        references.extend(context.runner.references)
        essential = evidence_rectangles
    elif scene_id == "promise":
        svg, display_text, asset_ids = _promise_svg(context)
        references.append(_asset_reference(context.root, context.assets.require("apseudo-mark")))
        essential = (COPY_RECTANGLE,)
    else:
        raise SceneError(f"scene {scene_id!r}: no approved renderer")
    _validate_essential_geometry(essential, context.theme.title_safe, scene_id)
    return RenderedSceneState(
        scene_id=scene_id,
        state_id=state_id,
        start_frame=start_frame,
        end_frame=end_frame,
        svg=svg,
        evidence_rectangles=evidence_rectangles,
        essential_rectangles=essential,
        copy_rectangle=None,
        caption_rectangle=CAPTION_RECTANGLE,
        display_text=display_text,
        references=_unique_references(references),
        asset_ids=asset_ids,
    )


def _render_mute_safe(
    context: _SceneContext,
    *,
    start_frame: int,
    end_frame: int,
) -> RenderedSceneState:
    root = _svg_root(
        context,
        "mute_safe_copy",
        evidence_rectangles=(),
        extra={"data-caption-clear": "true"},
    )
    _background(root, context.theme.colors["ink"])
    _add_copy(
        root,
        context.segment.mute_safe_copy,
        context.theme,
        COPY_RECTANGLE,
    )
    ElementTree.SubElement(
        root,
        _svg("rect"),
        {
            "x": str(CAPTION_RECTANGLE.x),
            "y": str(CAPTION_RECTANGLE.y),
            "width": str(CAPTION_RECTANGLE.width),
            "height": str(CAPTION_RECTANGLE.height),
            "fill": context.theme.colors["ink"],
            "data-caption-clear": "true",
        },
    )
    _validate_essential_geometry((COPY_RECTANGLE,), context.theme.title_safe, context.scene.id)
    return RenderedSceneState(
        scene_id=context.scene.id,
        state_id="mute_safe_copy",
        start_frame=start_frame,
        end_frame=end_frame,
        svg=_serialize_svg(root),
        evidence_rectangles=(),
        essential_rectangles=(COPY_RECTANGLE,),
        copy_rectangle=COPY_RECTANGLE,
        caption_rectangle=CAPTION_RECTANGLE,
        display_text=context.segment.mute_safe_copy,
        references=(context.theme_reference, context.narration_reference),
        asset_ids=(),
    )


def _problem_svg(context: _SceneContext) -> tuple[bytes, str, tuple[str, ...]]:
    root = _svg_root(context, "problem", evidence_rectangles=())
    _background(root, context.theme.colors["ink"])
    _add_label(
        root,
        "Dense instructions. Hidden decisions.",
        context.theme,
        x=240,
        y=310,
        color="blue",
    )
    _add_copy(root, context.segment.caption, context.theme, COPY_RECTANGLE)
    return _serialize_svg(root), context.segment.caption, ()


def _editor_svg(
    context: _SceneContext,
    evidence_rectangles: tuple[Rectangle, ...],
) -> tuple[bytes, str, ContentReference]:
    editor = context.editor
    expected = _tuple_rectangle(editor.evidence_rectangle)
    destination = _tuple_rectangle(editor.destination_rectangle)
    if (
        evidence_rectangles != (expected,)
        or destination != expected
        or expected != EDITOR_RECTANGLE
    ):
        raise SceneError(
            "visible-workflow: editor destination/evidence geometry must equal the "
            "project manifest rectangle [96, 54, 1728, 786]"
        )
    if (
        editor.source_crop != SOURCE_CROP
        or editor.native_scale != 1.0
        or editor.caption_rectangle != CAPTURE_CAPTION_RECTANGLE
        or editor.source_path != HERO_SOURCE_PATH
    ):
        raise SceneError("visible-workflow: editor crop, source, scale, or caption band changed")
    frame = editor.frames[0]
    try:
        png = frame.path.read_bytes()
    except OSError as exc:
        raise SceneError("visible-workflow: editor PNG could not be read") from exc
    if _digest(png) != frame.png_sha256 or _png_dimensions(png) != (1920, 1080):
        raise SceneError("visible-workflow: editor PNG bytes or dimensions changed")
    hero = _git_source(context.root, context.revision, HERO_SOURCE_PATH)
    if _digest(hero) != editor.source_sha256:
        raise SceneError("visible-workflow: editor source bytes changed at the capture revision")

    root = _svg_root(context, "visible-workflow", evidence_rectangles=evidence_rectangles)
    _background(root, context.theme.colors["ink"])
    definitions = ElementTree.SubElement(root, _svg("defs"))
    clip = ElementTree.SubElement(
        definitions,
        _svg("clipPath"),
        {"id": "editor-clip", "clipPathUnits": "userSpaceOnUse"},
    )
    ElementTree.SubElement(
        clip,
        _svg("rect"),
        {
            "id": "editor-native-crop",
            "x": "96",
            "y": "54",
            "width": "1728",
            "height": "786",
        },
    )
    source_x, source_y, _, _ = editor.source_crop
    destination_x, destination_y, _, _ = editor.destination_rectangle
    ElementTree.SubElement(
        root,
        _svg("image"),
        {
            "x": str(destination_x - source_x),
            "y": str(destination_y - source_y),
            "width": "1920",
            "height": "1080",
            "preserveAspectRatio": "none",
            "clip-path": "url(#editor-clip)",
            "href": f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}",
            "data-native-scale": "1",
            "data-source-sha256": frame.png_sha256,
        },
    )
    reference = ContentReference(
        kind="capture",
        path=_reference_path(context.root, frame.path),
        sha256=frame.png_sha256,
        revision=context.revision,
    )
    return _serialize_svg(root), hero.decode("utf-8"), reference


def _teaching_svg(
    context: _SceneContext,
    evidence_rectangles: tuple[Rectangle, ...],
) -> tuple[bytes, str]:
    rectangle = _one_evidence_rectangle(evidence_rectangles, "caught-defect")
    root = _svg_root(context, "caught-defect", evidence_rectangles=evidence_rectangles)
    _background(root, context.theme.colors["ink"])
    _terminal_panel(root, rectangle, context.theme)
    _add_label(
        root,
        "Teaching example — deliberately invalid",
        context.theme,
        x=rectangle.x + 36,
        y=rectangle.y + 48,
        color="coral",
    )
    command_lines = _wrap_shell_text(context.teaching.command, 86)
    source_lines = context.teaching.source.decode("utf-8").splitlines()
    diagnostic_lines = context.teaching.output.decode("utf-8").splitlines()
    visible_lines = [
        "$ " + command_lines[0],
        *("  " + line for line in command_lines[1:]),
        "",
        *source_lines,
        "",
        *diagnostic_lines,
    ]
    _add_code_lines(
        root,
        visible_lines,
        context.theme,
        x=rectangle.x + 36,
        y=rectangle.y + 102,
        max_lines=18,
    )
    return _serialize_svg(root), context.teaching.command


def _policy_svg(
    context: _SceneContext,
    evidence_rectangles: tuple[Rectangle, ...],
) -> tuple[bytes, str, tuple[str, ...]]:
    rectangle = _one_evidence_rectangle(evidence_rectangles, "shared-policy")
    source = context.source_references[0].content.decode("utf-8")
    rule_lines = source.splitlines()[171:173]
    if not rule_lines or '"APSEUDO-WHILE-001"' not in "\n".join(rule_lines):
        raise SceneError(
            "shared-policy: pinned rule source range no longer names APSEUDO-WHILE-001"
        )
    asset = context.assets.require("policy-map")
    asset_bytes = asset.path.read_bytes()
    root = _svg_root(context, "shared-policy", evidence_rectangles=evidence_rectangles)
    _background(root, context.theme.colors["ink"])
    _terminal_panel(root, rectangle, context.theme)
    _add_label(
        root,
        "One shared policy",
        context.theme,
        x=rectangle.x + 36,
        y=rectangle.y + 48,
        color="mint",
    )
    _add_code_lines(
        root,
        rule_lines,
        context.theme,
        x=rectangle.x + 36,
        y=rectangle.y + 104,
        max_lines=12,
    )
    ElementTree.SubElement(
        root,
        _svg("image"),
        {
            "x": "940",
            "y": "250",
            "width": "780",
            "height": "403",
            "preserveAspectRatio": "xMidYMid meet",
            "href": f"data:image/svg+xml;base64,{base64.b64encode(asset_bytes).decode('ascii')}",
            "data-asset-id": asset.id,
            "data-asset-sha256": asset.sha256,
        },
    )
    return _serialize_svg(root), "\n".join(rule_lines), (asset.id,)


def _runner_svg(
    context: _SceneContext,
    evidence_rectangles: tuple[Rectangle, ...],
) -> tuple[bytes, str]:
    rectangle = _one_evidence_rectangle(evidence_rectangles, "guarded-execution")
    root = _svg_root(context, "guarded-execution", evidence_rectangles=evidence_rectangles)
    _background(root, context.theme.colors["ink"])
    _terminal_panel(root, rectangle, context.theme)
    mode_label = (
        "Verified preflight-only"
        if context.runner.mode == "preflight-only"
        else "Accepted guarded execution"
    )
    _add_label(
        root,
        mode_label,
        context.theme,
        x=rectangle.x + 36,
        y=rectangle.y + 48,
        color="mint" if context.runner.mode == "accepted" else "blue",
    )
    command_lines = _wrap_shell_text(context.runner.display_command, 86)
    reason_lines = textwrap.wrap(
        context.runner.reason,
        width=86,
        break_long_words=False,
        break_on_hyphens=False,
    )
    _add_code_lines(
        root,
        ["$ " + command_lines[0], *("  " + line for line in command_lines[1:]), "", *reason_lines],
        context.theme,
        x=rectangle.x + 36,
        y=rectangle.y + 104,
        max_lines=17,
    )
    return _serialize_svg(root), context.runner.display_command


def _promise_svg(context: _SceneContext) -> tuple[bytes, str, tuple[str, ...]]:
    asset = context.assets.require("apseudo-mark")
    asset_bytes = asset.path.read_bytes()
    root = _svg_root(context, "promise", evidence_rectangles=())
    _background(root, context.theme.colors["ink"])
    ElementTree.SubElement(
        root,
        _svg("image"),
        {
            "x": "260",
            "y": "70",
            "width": "200",
            "height": "200",
            "href": f"data:image/svg+xml;base64,{base64.b64encode(asset_bytes).decode('ascii')}",
            "data-asset-id": asset.id,
            "data-asset-sha256": asset.sha256,
        },
    )
    _add_copy(
        root,
        context.segment.mute_safe_copy,
        context.theme,
        COPY_RECTANGLE,
    )
    return _serialize_svg(root), context.segment.mute_safe_copy, (asset.id,)


def _validate_cross_inputs(
    project: ProjectManifest,
    narration: NarrationPackage,
    evidence: EvidenceManifest,
    theme: SceneTheme,
    assets: AssetCatalog,
) -> None:
    if (project.media.width, project.media.height) != (1920, 1080):
        raise SceneError("project.media: expected 1920x1080")
    if project.safe_area.rectangle != theme.title_safe:
        raise SceneError("theme title-safe rectangle does not match the project manifest")
    if project.safe_area.text_sizes.code != theme.code_size:
        raise SceneError("theme code size does not match the project manifest")
    if project.safe_area.text_sizes.caption != theme.caption_size:
        raise SceneError("theme caption size does not match the project manifest")
    if tuple(segment.scene_id for segment in narration.segments) != tuple(
        scene.id for scene in project.scenes
    ):
        raise SceneError("narration scene order does not match the project manifest")
    for asset_id in (theme.font_sans_asset_id, theme.font_mono_asset_id):
        asset = assets.require(asset_id)
        if asset.kind != "font":
            raise SceneError(f"theme font asset {asset_id!r} is not classified as a font")
    if evidence.editor is None:
        raise SceneError("real editor evidence is required")


def _teaching_inputs(
    root: Path,
    revision: str,
    commands: Mapping[str, CommandEvidence],
) -> _TeachingInputs:
    try:
        record = commands[TEACHING_COMMAND_ID]
    except KeyError as exc:
        raise SceneError("caught-defect: teaching-defect capture is missing") from exc
    expected_argv = (
        "uv",
        "run",
        "apseudo-lint",
        "--stdin-filename",
        TEACHING_DEFECT_PATH,
    )
    if (
        record.argv != expected_argv
        or record.stdin_source != TEACHING_DEFECT_PATH
        or record.source_path != TEACHING_DEFECT_PATH
        or record.stdin_sha256 is None
        or record.source_sha256 is None
        or record.stdin_sha256 != record.source_sha256
        or record.exit_status != 1
    ):
        raise SceneError("caught-defect: argv, stdin source, source hash, or status changed")
    source = _git_source(root, revision, TEACHING_DEFECT_PATH)
    if _digest(source) != record.stdin_sha256:
        raise SceneError("caught-defect: stdin bytes changed at the capture revision")
    if len(record.promoted_outputs) != 1:
        raise SceneError("caught-defect: expected one promoted diagnostic output")
    output_record = record.promoted_outputs[0]
    output = output_record.path.read_bytes()
    if _digest(output) != output_record.sha256 or b"APSEUDO-WHILE-001" not in output:
        raise SceneError("caught-defect: promoted APSEUDO-WHILE-001 output changed")
    command = f"{shlex.join(record.argv)} < {shlex.quote(record.stdin_source)}"
    return _TeachingInputs(
        command=command,
        source=source,
        source_reference=ContentReference(
            kind="source",
            path=TEACHING_DEFECT_PATH,
            sha256=record.source_sha256,
            revision=revision,
        ),
        output=output,
        output_reference=ContentReference(
            kind="capture",
            path=_relative_or_error(root, output_record.path, "teaching output"),
            sha256=output_record.sha256,
            revision=revision,
        ),
    )


def _runner_inputs(evidence: EvidenceManifest) -> _RunnerInputs:
    runner = evidence.runner
    if runner is None:
        raise SceneError("guarded-execution: runner evidence ledger is missing")
    try:
        commands_record = next(
            record for record in runner.evidence if record.path.name == RUNNER_COMMANDS_NAME
        )
        outcome_record = next(
            record for record in runner.evidence if record.path.name == "outcome.json"
        )
    except StopIteration as exc:
        raise SceneError("guarded-execution: required runner evidence is missing") from exc
    try:
        commands_value: object = json.loads(commands_record.path.read_bytes())
        outcome_value: object = json.loads(outcome_record.path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SceneError("guarded-execution: runner evidence is unreadable") from exc
    commands = _object(commands_value, "runner-commands")
    display = _object(commands.get("display"), "runner-commands.display")
    aliases = _object(display.get("aliases"), "runner-commands.display.aliases")
    display_command = _nonempty_string(
        display.get("command"),
        "runner-commands.display.command",
    )
    base_argv = tuple(
        _nonempty_string(value, f"runner-commands.base_argv[{index}]")
        for index, value in enumerate(
            _array(commands.get("base_argv"), "runner-commands.base_argv")
        )
    )
    try:
        expanded = expand_display_command(display_command, aliases)
        display_tokens = shlex.split(display_command)
    except (RunnerCaptureError, ValueError) as exc:
        raise SceneError("guarded-execution: display aliases are not reversible") from exc
    if expanded != base_argv:
        raise SceneError("guarded-execution: display aliases do not equal the recorded argv")
    if any(Path(token).is_absolute() for token in display_tokens):
        raise SceneError("guarded-execution: display command contains an absolute operator path")
    outcome = _object(outcome_value, "runner-outcome")
    mode = _nonempty_string(outcome.get("mode"), "runner-outcome.mode")
    reason = _nonempty_string(outcome.get("reason"), "runner-outcome.reason")
    if mode != runner.mode or reason != runner.reason:
        raise SceneError("guarded-execution: displayed outcome does not match the runner ledger")
    references = tuple(
        ContentReference(
            kind="capture",
            path=record.path.as_posix(),
            sha256=record.sha256,
            revision=runner.revision,
        )
        for record in (commands_record, outcome_record)
    )
    return _RunnerInputs(
        display_command=display_command,
        mode=mode,
        reason=reason,
        references=references,
    )


def _source_reference(root: Path, revision: str, absolute_path: Path) -> _SourceInput:
    path = _relative_or_error(root, absolute_path, "scene source")
    content = _git_source(root, revision, path)
    return _SourceInput(
        content=content,
        reference=ContentReference(
            kind="source",
            path=path,
            sha256=_digest(content),
            revision=revision,
        ),
    )


def _path_reference(root: Path, path: Path, kind: ReferenceKind) -> ContentReference:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise SceneError(f"{kind}: referenced input could not be read") from exc
    return ContentReference(
        kind=kind,
        path=_relative_or_error(root, path, kind),
        sha256=_digest(content),
    )


def _asset_reference(root: Path, asset: AssetRecord) -> ContentReference:
    path = (
        _relative_or_error(root, asset.repository_path, f"asset {asset.id!r}")
        if asset.repository_path is not None
        else asset.path.as_posix()
    )
    return ContentReference(kind="asset", path=path, sha256=asset.sha256)


def _svg_root(
    context: _SceneContext,
    state_id: str,
    *,
    evidence_rectangles: tuple[Rectangle, ...],
    extra: Mapping[str, str] | None = None,
) -> ElementTree.Element:
    attributes = {
        "width": "1920",
        "height": "1080",
        "viewBox": "0 0 1920 1080",
        "role": "img",
        "aria-label": f"{context.scene.id} {state_id}",
        "data-scene-id": context.scene.id,
        "data-state-id": state_id,
        "data-evidence-rectangles": ";".join(
            _rectangle_string(value) for value in evidence_rectangles
        ),
    }
    if extra is not None:
        attributes.update(extra)
    root = ElementTree.Element(_svg("svg"), attributes)
    description = ElementTree.SubElement(root, _svg("desc"))
    description.text = f"Deterministic scene state for {context.scene.id}."
    return root


def _background(root: ElementTree.Element, color: str) -> None:
    ElementTree.SubElement(
        root,
        _svg("rect"),
        {"x": "0", "y": "0", "width": "1920", "height": "1080", "fill": color},
    )


def _terminal_panel(
    root: ElementTree.Element,
    rectangle: Rectangle,
    theme: SceneTheme,
) -> None:
    ElementTree.SubElement(
        root,
        _svg("rect"),
        {
            "x": str(rectangle.x),
            "y": str(rectangle.y),
            "width": str(rectangle.width),
            "height": str(rectangle.height),
            "rx": "28",
            "fill": theme.colors["surface"],
            "stroke": theme.colors["surface_alt"],
            "stroke-width": "4",
            "data-evidence-rectangle": _rectangle_string(rectangle),
        },
    )


def _add_label(
    root: ElementTree.Element,
    text: str,
    theme: SceneTheme,
    *,
    x: int,
    y: int,
    color: str,
) -> None:
    element = ElementTree.SubElement(
        root,
        _svg("text"),
        {
            "x": str(x),
            "y": str(y),
            "fill": theme.colors[color],
            "font-family": theme.font_sans,
            "font-size": str(theme.label_size),
            "font-weight": "700",
        },
    )
    element.text = text


def _add_copy(
    root: ElementTree.Element,
    text: str,
    theme: SceneTheme,
    rectangle: Rectangle,
) -> None:
    lines = textwrap.wrap(
        text,
        width=max(20, rectangle.width // (theme.copy_size // 2)),
        break_long_words=False,
        break_on_hyphens=False,
    )
    line_height = theme.copy_size + 18
    total_height = len(lines) * line_height
    first_y = rectangle.y + (rectangle.height - total_height) // 2 + theme.copy_size
    element = ElementTree.SubElement(
        root,
        _svg("text"),
        {
            "x": str(rectangle.x + rectangle.width // 2),
            "y": str(first_y),
            "fill": theme.colors["paper"],
            "font-family": theme.font_sans,
            "font-size": str(theme.copy_size),
            "font-weight": "700",
            "text-anchor": "middle",
            "aria-label": text,
            "data-copy-rectangle": _rectangle_string(rectangle),
        },
    )
    for index, line in enumerate(lines):
        span = ElementTree.SubElement(
            element,
            _svg("tspan"),
            {
                "x": str(rectangle.x + rectangle.width // 2),
                "y": str(first_y + index * line_height),
            },
        )
        span.text = line
        span.tail = " "


def _add_code_lines(
    root: ElementTree.Element,
    lines: Sequence[str],
    theme: SceneTheme,
    *,
    x: int,
    y: int,
    max_lines: int,
) -> None:
    if len(lines) > max_lines:
        raise SceneError(f"scene code layout: {len(lines)} lines exceed the {max_lines}-line frame")
    element = ElementTree.SubElement(
        root,
        _svg("text"),
        {
            "x": str(x),
            "y": str(y),
            "fill": theme.colors["paper"],
            "font-family": theme.font_mono,
            "font-size": str(theme.code_size),
            "xml:space": "preserve",
        },
    )
    for index, line in enumerate(lines):
        span = ElementTree.SubElement(
            element,
            _svg("tspan"),
            {"x": str(x), "y": str(y + index * 40)},
        )
        span.text = line or " "
        span.tail = "\n"


def _serialize_svg(root: ElementTree.Element) -> bytes:
    return ElementTree.tostring(
        root, encoding="utf-8", xml_declaration=True, short_empty_elements=True
    )


def _svg(name: str) -> str:
    return f"{{{_SVG_NAMESPACE}}}{name}"


def _one_evidence_rectangle(
    rectangles: tuple[Rectangle, ...],
    scene_id: str,
) -> Rectangle:
    if len(rectangles) != 1:
        raise SceneError(f"{scene_id}: expected exactly one project evidence rectangle")
    return rectangles[0]


def _validate_essential_geometry(
    rectangles: Sequence[Rectangle],
    title_safe: Rectangle,
    scene_id: str,
) -> None:
    for rectangle in rectangles:
        if (
            rectangle.x < title_safe.x
            or rectangle.y < title_safe.y
            or rectangle.x + rectangle.width > title_safe.x + title_safe.width
            or rectangle.y + rectangle.height > title_safe.y + title_safe.height
        ):
            raise SceneError(
                f"{scene_id}: essential content escapes the central 90% title-safe area"
            )


def _wrap_shell_text(command: str, width: int) -> list[str]:
    lines = textwrap.wrap(
        command,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if " ".join(lines) != command:
        raise SceneError("display command: wrapping changed the recorded shell text")
    return lines


def _git_source(root: Path, revision: str, path: str) -> bytes:
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != path:
        raise SceneError("scene source: expected a normalized repository-relative path")
    try:
        completed = subprocess.run(
            ["git", "show", f"{revision}:{path}"],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SceneError(f"scene source {path!r}: Git lookup could not complete") from exc
    if completed.returncode != 0:
        raise SceneError(f"scene source {path!r}: unavailable at capture revision {revision}")
    return completed.stdout


def _load_json(path: Path, field: str) -> tuple[bytes, dict[str, object]]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise SceneError(f"{field}: file not found") from exc
    except OSError as exc:
        raise SceneError(f"{field}: could not be read") from exc
    try:
        value: object = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_object_keys,
        )
    except UnicodeDecodeError as exc:
        raise SceneError(f"{field}: invalid UTF-8") from exc
    except _DuplicateJsonKeyError as exc:
        raise SceneError(f"{field}: duplicate JSON key {exc.key!r}") from exc
    except json.JSONDecodeError as exc:
        raise SceneError(f"{field}: invalid JSON: {exc.msg}") from exc
    return raw, _object(value, field)


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    decoded: dict[str, object] = {}
    for key, value in pairs:
        if key in decoded:
            raise _DuplicateJsonKeyError(key)
        decoded[key] = value
    return decoded


def _asset_record(payload: dict[str, object], index: int, root: Path) -> AssetRecord:
    field = f"assets[{index}]"
    _exact_fields(
        payload,
        {
            "id",
            "kind",
            "repository_path",
            "system_path",
            "source",
            "license_id",
            "generation_method",
            "sha256",
        },
        field,
    )
    asset_id = _nonempty_string(payload["id"], f"{field}.id")
    kind_value = _nonempty_string(payload["kind"], f"{field}.kind")
    if kind_value not in {"audio", "font", "graphic"}:
        raise SceneError(f"{field}.kind: expected audio, font, or graphic")
    kind = cast(AssetKind, kind_value)
    repository_value = _optional_string(payload["repository_path"], f"{field}.repository_path")
    system_value = _optional_string(payload["system_path"], f"{field}.system_path")
    if (repository_value is None) == (system_value is None):
        raise SceneError(f"{field}: exactly one of repository_path or system_path is required")
    repository_path: Path | None = None
    system_path: Path | None = None
    if repository_value is not None:
        relative = Path(repository_value)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != repository_value
        ):
            raise SceneError(f"{field}.repository_path: expected a normalized relative path")
        repository_path = (root / relative).resolve()
        if not repository_path.is_relative_to(root):
            raise SceneError(f"{field}.repository_path: escapes the repository")
        selected_path = repository_path
    else:
        if system_value is None:
            raise SceneError(f"{field}.system_path: is required")
        system_path = Path(system_value)
        if not system_path.is_absolute() or system_path.as_posix() != system_value:
            raise SceneError(f"{field}.system_path: expected a normalized absolute path")
        selected_path = system_path
    expected_hash = _hash(payload["sha256"], f"{field}.sha256")
    try:
        actual_hash = _digest(selected_path.read_bytes())
    except OSError as exc:
        raise SceneError(f"{field}: asset bytes could not be read") from exc
    if actual_hash != expected_hash:
        raise SceneError(f"{field}.sha256: asset bytes changed")
    license_id = _optional_string(payload["license_id"], f"{field}.license_id")
    generation_method = _optional_string(
        payload["generation_method"],
        f"{field}.generation_method",
    )
    if license_id is None and generation_method is None:
        raise SceneError(f"{field}: license_id or generation_method is required")
    return AssetRecord(
        id=asset_id,
        kind=kind,
        repository_path=repository_path,
        system_path=system_path,
        source=_nonempty_string(payload["source"], f"{field}.source"),
        license_id=license_id,
        generation_method=generation_method,
        sha256=expected_hash,
    )


def _contrast_pair(
    value: object,
    index: int,
    colors: Mapping[str, str],
) -> tuple[str, str]:
    field = f"theme.contrast_pairs[{index}]"
    parts = _array(value, field)
    if len(parts) != 2:
        raise SceneError(f"{field}: expected foreground and background names")
    foreground = _nonempty_string(parts[0], f"{field}[0]")
    background = _nonempty_string(parts[1], f"{field}[1]")
    if foreground not in colors or background not in colors:
        raise SceneError(f"{field}: references an unknown theme color")
    return foreground, background


def _font(payload: dict[str, object], name: str) -> tuple[str, str]:
    field = f"theme.fonts.{name}"
    _exact_fields(payload, {"family", "asset_id"}, field)
    return (
        _nonempty_string(payload["family"], f"{field}.family"),
        _nonempty_string(payload["asset_id"], f"{field}.asset_id"),
    )


def _relative_or_error(root: Path, path: Path, field: str) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise SceneError(f"{field}: path escapes the repository")
    return resolved.relative_to(root).as_posix()


def _reference_path(root: Path, path: Path) -> str:
    """Keep injected evidence traceable without weakening production path validation.

    ``compose_scene_states`` can only receive editor frames that
    ``verify_evidence_manifest`` already confined below the repository capture
    root. The lower-level renderer also accepts typed evidence for isolated
    callers, so its provenance record preserves an external path instead of
    pretending those bytes were repository-owned.
    """
    resolved = path.resolve()
    if resolved.is_relative_to(root):
        return resolved.relative_to(root).as_posix()
    return resolved.as_posix()


def _unique_references(
    references: Sequence[ContentReference],
) -> tuple[ContentReference, ...]:
    unique: dict[tuple[ReferenceKind, str, str, str | None], ContentReference] = {}
    for reference in references:
        key = (reference.kind, reference.path, reference.sha256, reference.revision)
        unique[key] = reference
    return tuple(unique.values())


def _rectangle(value: object, field: str) -> Rectangle:
    parts = _array(value, field)
    if len(parts) != 4:
        raise SceneError(f"{field}: expected [x, y, width, height]")
    rectangle = Rectangle(
        x=_integer(parts[0], f"{field}[0]"),
        y=_integer(parts[1], f"{field}[1]"),
        width=_integer(parts[2], f"{field}[2]"),
        height=_integer(parts[3], f"{field}[3]"),
    )
    if rectangle.x < 0 or rectangle.y < 0 or rectangle.width <= 0 or rectangle.height <= 0:
        raise SceneError(f"{field}: expected a positive on-canvas rectangle")
    return rectangle


def _tuple_rectangle(value: tuple[int, int, int, int]) -> Rectangle:
    return Rectangle(x=value[0], y=value[1], width=value[2], height=value[3])


def _rectangle_string(rectangle: Rectangle) -> str:
    return f"{rectangle.x},{rectangle.y},{rectangle.width},{rectangle.height}"


def _relative_luminance(color: str) -> float:
    normalized = _color(color, "color")
    channels = [int(normalized[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _png_dimensions(content: bytes) -> tuple[int, int]:
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n":
        raise SceneError("editor PNG: invalid PNG header")
    return cast(tuple[int, int], struct.unpack(">II", content[16:24]))


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SceneError(f"{field}: expected an object")
    typed = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in typed):
        raise SceneError(f"{field}: expected string keys")
    return cast(dict[str, object], typed)


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise SceneError(f"{field}: expected an array")
    return cast(list[object], value)


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise SceneError(f"{field}: expected an integer")
    return value


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SceneError(f"{field}: expected a non-empty string")
    return value


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty_string(value, field)


def _hash(value: object, field: str) -> str:
    text = _nonempty_string(value, field)
    if not _SHA256.fullmatch(text):
        raise SceneError(f"{field}: expected a lowercase SHA-256")
    return text


def _color(value: object, field: str) -> str:
    text = _nonempty_string(value, field)
    if not _HEX_COLOR.fullmatch(text):
        raise SceneError(f"{field}: expected #RRGGBB")
    return text.upper()


def _exact_fields(
    payload: Mapping[str, object],
    expected: set[str],
    field: str,
) -> None:
    actual = set(payload)
    if actual != expected:
        raise SceneError(
            f"{field}: fields differ "
            f"(missing={sorted(expected - actual)}, unknown={sorted(actual - expected)})"
        )
