"""Produce the structured, promotion-blocking repository explainer QA report.

The verifier treats rendered media and review artifacts as untrusted evidence.
Every Must gate returns a stable identifier and a structured evidence payload;
promotion is the conjunction of those rows, never an implicit exception path.
Container bytes are deliberately excluded from reproduction equality because
decoded video, decoded PCM, captions, and the semantic render contract are the
stable delivery meaning.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Literal, NamedTuple, cast
from xml.etree import ElementTree

from .captions import AI_NARRATION_DISCLOSURE
from .models import MediaSettings, Rectangle, VisualState
from .render import (
    PRODUCTION_FPS,
    PRODUCTION_FRAMES,
    PRODUCTION_HEIGHT,
    PRODUCTION_WIDTH,
    RenderConfig,
    RenderError,
    hash_command_output,
    probe_render_capabilities,
    render_production,
    toolchain_manifest,
)
from .runner_security import (
    ProcessResult,
    RunnerCaptureError,
    build_child_environment,
    run_capture_process,
)
from .scenes import RenderedSceneState, SceneError, compose_scene_states

type GateStatus = Literal["pass", "fail"]
type VariantName = Literal["narrated", "speaker"]
type VerificationMode = Literal["production", "diagnostic"]

REPORT_SCHEMA_VERSION = 1
PRODUCTION_MEDIA = MediaSettings(
    width=PRODUCTION_WIDTH,
    height=PRODUCTION_HEIGHT,
    fps=PRODUCTION_FPS,
    total_frames=PRODUCTION_FRAMES,
)
REQUIRED_DELIVERY_INVENTORY: dict[str, str] = {
    "narrated_mp4": "agent-pseudocode-explainer-narrated.mp4",
    "speaker_mp4": "agent-pseudocode-explainer-speaker.mp4",
    "selected_narration_wav": "agent-pseudocode-explainer-narration-selected.wav",
    "captions_srt": "agent-pseudocode-explainer-captions.srt",
    "delivery_json": "delivery.json",
    "render_manifest_json": "render-manifest.json",
    "asset_provenance_json": "asset-provenance.json",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INTEGRATED_LOUDNESS = re.compile(r"^\s*I:\s*(-?(?:\d+(?:\.\d+)?|inf))\s+LUFS\s*$", re.M)
_TRUE_PEAK = re.compile(r"^\s*Peak:\s*(-?(?:\d+(?:\.\d+)?|inf))\s+dB(?:FS|TP)\s*$", re.M)
_HIGH_ENTROPY_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/=_-]{32,}(?![A-Za-z0-9+/=_-])"
)
_SRT_TIMING = re.compile(
    r"(?m)^(?P<start>\d{2}:\d{2}:\d{2},\d{3}) --> "
    r"(?P<end>\d{2}:\d{2}:\d{2},\d{3})$"
)
_SECRET_PATTERNS = (
    (
        "credential-assignment",
        re.compile(
            r"(?:\b|_)(?:authorization|api[_-]?key|access[_-]?token|secret[_-]?key|password)"
            r"\s*[:=]\s*[^\s,;]+",
            re.I,
        ),
    ),
    (
        "private-key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.I),
    ),
    (
        "credential-token",
        re.compile(r"\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{8,}\b", re.I),
    ),
)
_RENDER_MANIFEST_FIELDS = {
    "schema_version",
    "source_revision",
    "project_timing",
    "inputs",
    "synthesis",
    "audio_targets",
    "toolchain",
    "shared_picture",
    "outputs",
}


class VerificationError(ValueError):
    """Reject evidence that cannot be parsed into an auditable gate row."""


class LoudnessMeasurement(NamedTuple):
    """One EBU R128 integrated loudness and true-peak summary."""

    integrated_lufs: float
    true_peak_dbtp: float


@dataclass(frozen=True, slots=True)
class GateResult:
    """One stable verification decision with reviewable measurements."""

    id: str
    status: GateStatus
    evidence: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class FrameReview:
    """Measurements from one decoded final frame required by NFR-004."""

    variant: VariantName
    frame: int
    scene_id: str
    state_id: str
    minimum_text_size: int
    within_title_safe: bool
    minimum_contrast: float
    narration_caption_present: bool


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """The single report consumed by later promotion orchestration."""

    gates: tuple[GateResult, ...]
    checksums: Mapping[str, str] = field(default_factory=dict[str, str])
    schema_version: int = REPORT_SCHEMA_VERSION

    @property
    def promotable(self) -> bool:
        """Return whether every Must gate passed."""
        return bool(self.gates) and all(gate.status == "pass" for gate in self.gates)

    @property
    def failed_gate_ids(self) -> tuple[str, ...]:
        """Return failed identifiers in deterministic report order."""
        return tuple(gate.id for gate in self.gates if gate.status == "fail")

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-compatible report with no Boolean-only gate entries."""
        return {
            "schema_version": self.schema_version,
            "promotable": self.promotable,
            "failed_gate_ids": list(self.failed_gate_ids),
            "gates": [
                {"id": gate.id, "status": gate.status, "evidence": dict(gate.evidence)}
                for gate in self.gates
            ],
            "checksums": dict(sorted(self.checksums.items())),
        }


@dataclass(frozen=True, slots=True)
class VerificationInputs:
    """All reviewed evidence needed to make one promotion decision."""

    mode: VerificationMode
    repository_root: Path
    media: MediaSettings
    states: tuple[RenderedSceneState, ...]
    render_manifest: Mapping[str, object]
    reproduced_manifest: Mapping[str, object]
    actual_toolchain: Mapping[str, object]
    probes: Mapping[VariantName, Mapping[str, object]]
    loudness: Mapping[VariantName, LoudnessMeasurement]
    asset_provenance: Mapping[str, object]
    delivery: Mapping[str, object]
    frame_reviews: tuple[FrameReview, ...]
    required_frame_samples: tuple[tuple[VariantName, int, str, str], ...]
    speaker_speech_detected: bool
    clean_checkout: bool
    speech_api_calls: int
    secret_artifacts: Mapping[str, bytes | str]
    deliverables: Mapping[str, Path]


def verify_delivery(inputs: VerificationInputs) -> VerificationReport:
    """Run diagnostic verification; production must use source-derived entry point."""
    if inputs.mode == "production":
        return aggregate_report(
            (
                GateResult(
                    "API-production-entry",
                    "fail",
                    {
                        "reason": "source-derived-production-entry-required",
                        "required_function": "verify_production_delivery",
                    },
                ),
            )
        )
    return _verify_loaded_delivery(inputs)


def _verify_loaded_delivery(inputs: VerificationInputs) -> VerificationReport:
    """Run every T8 Must gate after production inputs were loaded internally."""
    expected_media = PRODUCTION_MEDIA if inputs.mode == "production" else inputs.media
    mode_gate = _gate(
        "MODE-production",
        inputs.mode == "production",
        {
            "mode": inputs.mode,
            "production_required_for_promotion": True,
        },
    )
    inventory_gate = verify_delivery_inventory(inputs.deliverables)
    manifest_gate = verify_render_manifest(
        inputs.render_manifest,
        media=expected_media,
        states=inputs.states,
    )
    rights_gate, classified_ids = verify_asset_provenance(
        inputs.asset_provenance,
        repository_root=inputs.repository_root,
    )
    closed_world_rights_gate = verify_closed_world_provenance(
        inputs.render_manifest,
        states=inputs.states,
        asset_provenance=inputs.asset_provenance,
        repository_root=inputs.repository_root,
        selected_wav=inputs.deliverables.get(
            "selected_narration_wav",
            inputs.repository_root / "dist/video/missing-selected-narration.wav",
        ),
    )
    media_gates = (
        verify_candidate_media(
            inputs.deliverables,
            manifest=inputs.render_manifest,
            states=inputs.states,
            mode="production",
        )
        if inputs.mode == "production"
        else tuple(
            gate
            for variant in ("narrated", "speaker")
            for gate in verify_media_variant(
                variant,
                inputs.probes.get(variant, {}),
                inputs.loudness.get(
                    variant,
                    LoudnessMeasurement(integrated_lufs=float("inf"), true_peak_dbtp=float("inf")),
                ),
                mode="diagnostic",
                media=inputs.media,
            )
        )
    )
    synthesis = _mapping(inputs.render_manifest.get("synthesis"))
    external_value = synthesis.get("external_music_inputs")
    external_music = (
        tuple(str(value) for value in cast(list[object], external_value))
        if isinstance(external_value, list)
        else ("invalid-render-manifest-value",)
    )
    content_gates = verify_content_contracts(
        repository_root=inputs.repository_root,
        states=inputs.states,
        classified_asset_ids=classified_ids,
        delivery=inputs.delivery,
        external_music_inputs=external_music,
        speaker_speech_detected=inputs.speaker_speech_detected,
        frame_reviews=inputs.frame_reviews,
        required_frame_samples=tuple(
            sorted(
                {
                    *required_frame_samples(inputs.states, ()),
                    *inputs.required_frame_samples,
                }
            )
        ),
        secret_artifacts=inputs.secret_artifacts,
        render_manifest=inputs.render_manifest,
    )
    if inputs.mode == "production":
        content_gates = (
            *(
                gate
                for gate in content_gates
                if gate.id
                not in {
                    "SECURITY-secrets",
                    "CAPTION-speaker",
                    "FRAME-final-layout",
                    "AUDIO-speaker-speech",
                }
            ),
            verify_required_artifact_secrets(inputs.deliverables, inputs.states),
            verify_renderer_layout(inputs.states, inputs.render_manifest),
        )
    share_gate = verify_evidence_frame_share(
        inputs.states,
        width=expected_media.width,
        height=expected_media.height,
        total_frames=expected_media.total_frames,
    )
    reproduction_gate = (
        run_offline_reproduction(
            repository_root=inputs.repository_root,
            work_root=inputs.repository_root / "dist" / "video" / "work",
            approved_manifest=inputs.render_manifest,
            selected_wav=inputs.deliverables.get(
                "selected_narration_wav",
                inputs.repository_root / "dist/video/missing-selected-narration.wav",
            ),
            selected_wav_sha256=cast(
                str,
                _mapping(
                    _mapping(inputs.render_manifest.get("inputs")).get("selected_narration_wav")
                ).get("sha256", ""),
            ),
        )
        if inputs.mode == "production"
        else verify_reproduction(
            inputs.render_manifest,
            inputs.reproduced_manifest,
            actual_toolchain=inputs.actual_toolchain,
            clean_checkout=inputs.clean_checkout,
            speech_api_calls=inputs.speech_api_calls,
            mode="diagnostic",
        )
    )
    checksums: dict[str, str] = {}
    checksum_findings: list[dict[str, str]] = []
    for name, path in sorted(inputs.deliverables.items()):
        digest = _file_sha256_or_none(path)
        if digest is None:
            checksum_findings.append({"deliverable": name, "reason": "unreadable-or-missing"})
        else:
            checksums[name] = digest
    checksum_gate = _gate(
        "CHECKSUM-deliverables",
        bool(inputs.deliverables) and not checksum_findings,
        {
            "deliverables": sorted(inputs.deliverables),
            "checksums": checksums,
            "findings": checksum_findings,
        },
    )
    return aggregate_report(
        (
            mode_gate,
            inventory_gate,
            manifest_gate,
            rights_gate,
            closed_world_rights_gate,
            *media_gates,
            *content_gates,
            share_gate,
            reproduction_gate,
            checksum_gate,
        ),
        checksums=checksums,
    )


def verify_production_delivery(
    *,
    repository_root: Path,
    deliverables: Mapping[str, Path],
) -> VerificationReport:
    """Load all production truth surfaces and execute the closed promotion gate."""
    root = repository_root.resolve()
    try:
        states = compose_scene_states(root)
    except SceneError as exc:
        return aggregate_report(
            (
                GateResult(
                    "SOURCE-production-states",
                    "fail",
                    {
                        "production_source_required": True,
                        "fixture_fallback_used": False,
                        "reason": str(exc),
                    },
                ),
            )
        )
    source_gate = GateResult(
        "SOURCE-production-states",
        "pass",
        {
            "production_source_required": True,
            "fixture_fallback_used": False,
            "state_count": len(states),
        },
    )
    inventory_gate = verify_delivery_inventory(deliverables)
    if inventory_gate.status == "fail":
        return aggregate_report((source_gate, inventory_gate))
    try:
        render_manifest = _read_json_mapping(
            deliverables["render_manifest_json"],
            "render manifest",
        )
        asset_provenance = _read_json_mapping(
            deliverables["asset_provenance_json"],
            "asset provenance",
        )
        delivery = _read_json_mapping(deliverables["delivery_json"], "delivery metadata")
    except VerificationError as exc:
        return aggregate_report(
            (
                source_gate,
                inventory_gate,
                GateResult(
                    "ARTIFACT-structured-inputs",
                    "fail",
                    {"reason": str(exc)},
                ),
            )
        )
    report = _verify_loaded_delivery(
        VerificationInputs(
            mode="production",
            repository_root=root,
            media=PRODUCTION_MEDIA,
            states=states,
            render_manifest=render_manifest,
            reproduced_manifest={},
            actual_toolchain={},
            probes={},
            loudness={},
            asset_provenance=asset_provenance,
            delivery=delivery,
            frame_reviews=(),
            required_frame_samples=(),
            speaker_speech_detected=True,
            clean_checkout=False,
            speech_api_calls=-1,
            secret_artifacts={},
            deliverables=deliverables,
        )
    )
    return aggregate_report(
        (source_gate, *report.gates),
        checksums=report.checksums,
    )


def verify_delivery_inventory(deliverables: Mapping[str, Path]) -> GateResult:
    """Require the exact production roles and stable filenames."""
    actual_roles = set(deliverables)
    required_roles = set(REQUIRED_DELIVERY_INVENTORY)
    name_mismatches = [
        {
            "role": role,
            "expected": expected_name,
            "actual": deliverables[role].name,
        }
        for role, expected_name in REQUIRED_DELIVERY_INVENTORY.items()
        if role in deliverables and deliverables[role].name != expected_name
    ]
    missing_roles = sorted(required_roles - actual_roles)
    unexpected_roles = sorted(actual_roles - required_roles)
    unreadable_roles = sorted(
        role for role, path in deliverables.items() if role in required_roles and not path.is_file()
    )
    return _gate(
        "INVENTORY-delivery",
        not missing_roles and not unexpected_roles and not name_mismatches and not unreadable_roles,
        {
            "required": dict(REQUIRED_DELIVERY_INVENTORY),
            "missing_roles": missing_roles,
            "unexpected_roles": unexpected_roles,
            "name_mismatches": name_mismatches,
            "unreadable_roles": unreadable_roles,
        },
    )


def verify_required_artifact_secrets(
    deliverables: Mapping[str, Path],
    states: Sequence[RenderedSceneState],
) -> GateResult:
    """Scan the complete production inventory and rendered scene bytes."""
    required_roles = set(REQUIRED_DELIVERY_INVENTORY)
    missing_roles = sorted(required_roles - set(deliverables))
    findings: list[dict[str, str]] = []
    scanned: list[str] = []
    for role in sorted(required_roles & set(deliverables)):
        scanned.append(role)
        path = deliverables[role]
        for classification in _scan_file_secret_classes(path):
            findings.append({"artifact": role, "classification": classification})
    for state in states:
        artifact = f"state:{state.scene_id}/{state.state_id}"
        scanned.append(artifact)
        for classification in _secret_classes(
            state.svg.decode("utf-8", errors="ignore"),
            include_entropy=True,
        ):
            findings.append({"artifact": artifact, "classification": classification})
    return _gate(
        "SECURITY-secrets",
        not missing_roles and not findings,
        {
            "artifacts_scanned": scanned,
            "missing_roles": missing_roles,
            "findings": findings,
            "high_entropy_minimum_bits_per_character": 4.5,
            "secret_values_recorded": False,
        },
    )


def verify_candidate_media(
    deliverables: Mapping[str, Path],
    *,
    manifest: Mapping[str, object],
    states: Sequence[RenderedSceneState],
    mode: VerificationMode = "production",
    diagnostic_media: MediaSettings | None = None,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> tuple[GateResult, ...]:
    """Derive media, caption, sample, and speech evidence from candidate bytes."""
    expected_media = (
        PRODUCTION_MEDIA
        if mode == "production"
        else diagnostic_media
        if diagnostic_media is not None
        else _raise_missing_diagnostic_media()
    )
    required_paths = {"narrated_mp4", "speaker_mp4", "captions_srt"}
    if not required_paths <= set(deliverables):
        missing = sorted(required_paths - set(deliverables))
        return (
            GateResult(
                "CANDIDATE-semantic-hashes",
                "fail",
                {"reason": "missing-candidate-artifacts", "missing_roles": missing},
            ),
        )
    narrated = deliverables["narrated_mp4"]
    speaker = deliverables["speaker_mp4"]
    captions = deliverables["captions_srt"]
    try:
        probes = {
            "narrated": probe_media_file(narrated, ffprobe=ffprobe, ffmpeg=ffmpeg),
            "speaker": probe_media_file(speaker, ffprobe=ffprobe, ffmpeg=ffmpeg),
        }
        loudness = {
            "narrated": measure_loudness(narrated, ffmpeg=ffmpeg),
            "speaker": measure_loudness(speaker, ffmpeg=ffmpeg),
        }
    except VerificationError as exc:
        return (
            GateResult(
                "CANDIDATE-analysis",
                "fail",
                {
                    "reason": "candidate-probe-or-loudness-failed",
                    "error_class": type(exc).__name__,
                },
            ),
        )
    media_gates = tuple(
        gate
        for variant in ("narrated", "speaker")
        for gate in verify_media_variant(
            variant,
            probes[variant],
            loudness[variant],
            mode=mode,
            media=expected_media,
        )
    )
    total_samples = round(expected_media.total_frames / expected_media.fps * 48_000)
    try:
        actual_outputs = {
            variant: _decoded_candidate_hashes(
                path,
                ffmpeg=ffmpeg,
                total_samples=total_samples,
            )
            for variant, path in (("narrated", narrated), ("speaker", speaker))
        }
        caption_bytes = captions.read_bytes()
    except (OSError, RenderError) as exc:
        return (
            *media_gates,
            GateResult(
                "CANDIDATE-semantic-hashes",
                "fail",
                {"reason": "candidate-decode-failed", "error_class": type(exc).__name__},
            ),
        )
    actual_semantics: dict[str, object] = {
        "caption_sha256": hashlib.sha256(caption_bytes).hexdigest(),
        "outputs": actual_outputs,
    }
    expected_semantics = _semantic_hash_evidence(manifest)
    semantic_gate = _gate(
        "CANDIDATE-semantic-hashes",
        actual_semantics == expected_semantics,
        {
            "comparison": "exact-decoded-hash",
            "actual": actual_semantics,
            "expected": expected_semantics,
        },
    )
    caption_frames, caption_findings = _caption_transition_frames(
        caption_bytes,
        fps=expected_media.fps,
        total_frames=expected_media.total_frames,
    )
    required_samples = required_frame_samples(states, caption_frames)
    sample_findings: list[dict[str, object]] = []
    sample_hashes: list[dict[str, object]] = []
    for variant, frame, scene_id, state_id in required_samples:
        path = narrated if variant == "narrated" else speaker
        try:
            digest = _decoded_frame_hash(
                path,
                frame=frame,
                width=expected_media.width,
                height=expected_media.height,
                ffmpeg=ffmpeg,
            )
        except RenderError as exc:
            sample_findings.append(
                {
                    "variant": variant,
                    "frame": frame,
                    "scene_id": scene_id,
                    "state_id": state_id,
                    "error_class": type(exc).__name__,
                }
            )
        else:
            sample_hashes.append(
                {
                    "variant": variant,
                    "frame": frame,
                    "scene_id": scene_id,
                    "state_id": state_id,
                    "decoded_frame_sha256": digest,
                }
            )
    sample_gate = _gate(
        "FRAME-final-samples",
        not caption_findings
        and not sample_findings
        and len(sample_hashes) == len(required_samples),
        {
            "sampled_frames": sorted({sample[1] for sample in required_samples}),
            "required_samples": len(required_samples),
            "samples": sample_hashes,
            "caption_findings": caption_findings,
            "sample_findings": sample_findings,
            "derivation": "decoded-candidate-frames-and-caption-source",
        },
    )
    outputs = _mapping(manifest.get("outputs"))
    speaker_output = _mapping(outputs.get("speaker"))
    shared_picture = _mapping(manifest.get("shared_picture"))
    actual_speaker = actual_outputs["speaker"]
    speaker_picture_clean = actual_speaker["decoded_video_sha256"] == speaker_output.get(
        "decoded_video_sha256"
    ) == shared_picture.get("decoded_video_sha256") and speaker_output.get("inputs") == [
        "shared_picture",
        "procedural_tonal_bed_and_cues",
    ]
    caption_gate = _gate(
        "CAPTION-speaker",
        speaker_picture_clean,
        {
            "derivation": "decoded-speaker-picture",
            "actual_decoded_video_sha256": actual_speaker["decoded_video_sha256"],
            "expected_shared_picture_sha256": shared_picture.get("decoded_video_sha256"),
            "speaker_inputs": speaker_output.get("inputs"),
        },
    )
    speaker_audio_clean = actual_speaker["decoded_pcm_sha256"] == speaker_output.get(
        "decoded_pcm_sha256"
    ) and speaker_output.get("inputs") == ["shared_picture", "procedural_tonal_bed_and_cues"]
    speech_gate = _gate(
        "AUDIO-speaker-speech",
        speaker_audio_clean,
        {
            "derivation": "decoded-speaker-pcm",
            "actual_decoded_pcm_sha256": actual_speaker["decoded_pcm_sha256"],
            "expected_procedural_pcm_sha256": speaker_output.get("decoded_pcm_sha256"),
            "speaker_inputs": speaker_output.get("inputs"),
        },
    )
    return (*media_gates, semantic_gate, sample_gate, caption_gate, speech_gate)


def verify_renderer_layout(
    states: Sequence[RenderedSceneState],
    manifest: Mapping[str, object],
) -> GateResult:
    """Bind final-frame layout claims to exact renderer SVG and render options."""
    safe = Rectangle(x=96, y=54, width=1728, height=972)
    findings: list[dict[str, object]] = []
    for state in states:
        state_name = f"{state.scene_id}/{state.state_id}"
        try:
            root = ElementTree.fromstring(state.svg)
        except ElementTree.ParseError:
            findings.append({"state": state_name, "reason": "invalid-rendered-svg"})
            continue
        for element in root.iter():
            raw_size = element.attrib.get("font-size")
            if raw_size is None:
                continue
            try:
                size = int(raw_size)
            except ValueError:
                findings.append(
                    {"state": state_name, "reason": "invalid-text-size", "value": raw_size}
                )
                continue
            if size < 32:
                findings.append(
                    {
                        "state": state_name,
                        "reason": "text-below-32px",
                        "measured_px": size,
                    }
                )
        for rectangle in state.essential_rectangles:
            if (
                rectangle.x < safe.x
                or rectangle.y < safe.y
                or rectangle.x + rectangle.width > safe.x + safe.width
                or rectangle.y + rectangle.height > safe.y + safe.height
            ):
                findings.append(
                    {
                        "state": state_name,
                        "reason": "essential-content-outside-title-safe",
                    }
                )
    toolchain = _mapping(manifest.get("toolchain"))
    options = _mapping(toolchain.get("options"))
    render_config = _mapping(options.get("render_config"))
    if render_config.get("caption_size") != 44:
        findings.append(
            {
                "reason": "caption-size-not-44px",
                "actual": render_config.get("caption_size"),
            }
        )
    return _gate(
        "FRAME-final-layout",
        not findings and bool(states),
        {
            "states_checked": len(states),
            "title_safe": {
                "x": safe.x,
                "y": safe.y,
                "width": safe.width,
                "height": safe.height,
            },
            "caption_size_px": render_config.get("caption_size"),
            "findings": findings,
            "binding": "renderer-svg-digest-plus-decoded-frame-samples",
        },
    )


def parse_ebur128(raw: str) -> LoudnessMeasurement:
    """Parse FFmpeg's final EBU R128 summary.

    The filter may emit interval measurements before the summary, so the final
    matching integrated and peak values are authoritative.
    """
    integrated_matches = _INTEGRATED_LOUDNESS.findall(raw)
    peak_matches = _TRUE_PEAK.findall(raw)
    if not integrated_matches or not peak_matches:
        raise VerificationError("EBU R128 output did not contain integrated loudness and true peak")
    try:
        integrated = float(integrated_matches[-1])
        peak = float(peak_matches[-1])
    except ValueError as exc:
        raise VerificationError("EBU R128 summary contained an invalid measurement") from exc
    if not math.isfinite(integrated) or not math.isfinite(peak):
        raise VerificationError("EBU R128 summary must contain finite measurements")
    return LoudnessMeasurement(integrated_lufs=integrated, true_peak_dbtp=peak)


def _run_media_analyzer(
    argv: Sequence[str],
    *,
    path: Path,
    timeout: int,
    operation: str,
) -> ProcessResult:
    result = run_capture_process(
        argv,
        cwd=path.resolve().parent,
        environment=build_child_environment({}),
        timeout=timeout,
        operation=operation,
    )
    if result.returncode != 0:
        raise RunnerCaptureError(f"{operation}: exited {result.returncode}")
    return result


def _parse_compact_packets(raw: str) -> list[dict[str, object]]:
    packets: list[dict[str, object]] = []
    for line in raw.splitlines():
        if not line:
            continue
        packet: dict[str, object] = {}
        skip_samples: int | None = None
        for packet_field in line.split("|"):
            name, separator, value = packet_field.partition("=")
            if not separator:
                raise VerificationError("FFprobe packet output contained an invalid field")
            if name in {"stream_index", "pts", "duration"}:
                parsed = _integer_or_none(value)
                if parsed is None:
                    raise VerificationError("FFprobe packet output contained an invalid integer")
                packet[name] = parsed
            elif name.endswith(":skip_samples"):
                skip_samples = _integer_or_none(value)
        if skip_samples is not None:
            packet["side_data_list"] = [
                {
                    "side_data_type": "Skip Samples",
                    "skip_samples": skip_samples,
                }
            ]
        packets.append(packet)
    return packets


def probe_media_file(
    path: Path, *, ffprobe: str = "ffprobe", ffmpeg: str = "ffmpeg"
) -> dict[str, object]:
    """Return FFprobe JSON augmented with the exact decoded PCM boundary."""
    try:
        completed = _run_media_analyzer(
            (
                ffprobe,
                "-v",
                "error",
                "-count_frames",
                "-show_entries",
                (
                    "format=format_name,duration:"
                    "stream=index,codec_type,codec_name,profile,width,height,pix_fmt,field_order,"
                    "r_frame_rate,duration,nb_read_frames,channels,sample_rate,time_base"
                ),
                "-of",
                "json",
                str(path),
            ),
            path=path,
            timeout=120,
            operation="media metadata probe",
        )
        decoded: object = json.loads(completed.stdout)
        packet_output = _run_media_analyzer(
            (
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_packets",
                "-show_entries",
                "packet=stream_index,pts,duration,side_data_list",
                "-of",
                "compact=p=0:nk=0",
                str(path),
            ),
            path=path,
            timeout=120,
            operation="media packet-boundary probe",
        )
        probe = cast(dict[str, object], decoded)
        probe["packets"] = _parse_compact_packets(packet_output.stdout)
        # This shared render primitive drains incrementally, hashes without retaining
        # PCM, caps output at the longest approved program, and kills its process group.
        _, pcm_bytes = hash_command_output(
            (
                ffmpeg,
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-c:a",
                "pcm_s16le",
                "-f",
                "s16le",
                "-",
            ),
            "media decoded PCM boundary",
            timeout_seconds=120,
            max_output_bytes=PRODUCTION_FRAMES // PRODUCTION_FPS * 48_000 * 4,
        )
    except (RunnerCaptureError, RenderError) as exc:
        raise VerificationError(f"media probe failed for {path.name!r}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError("FFprobe returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise VerificationError("FFprobe JSON must be an object")
    if pcm_bytes % 4:
        raise VerificationError("decoded stereo PCM ended between sample frames")
    streams = cast(list[dict[str, object]], probe.get("streams", []))
    audio = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"),
        None,
    )
    if audio is None or not isinstance(audio.get("index"), int):
        raise VerificationError("FFprobe did not report one indexed audio stream")
    packet_boundary = _derive_packet_boundary(
        probe,
        audio_stream_index=cast(int, audio["index"]),
        expected_samples=pcm_bytes // 4,
    )
    probe["program_audio_boundary"] = {
        "first_program_sample": 0,
        "last_program_sample_exclusive": pcm_bytes // 4,
        **packet_boundary,
    }
    return probe


def measure_loudness(path: Path, *, ffmpeg: str = "ffmpeg") -> LoudnessMeasurement:
    """Measure one variant independently with FFmpeg's EBU R128 filter."""
    try:
        completed = _run_media_analyzer(
            (
                ffmpeg,
                "-hide_banner",
                "-nostats",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-filter:a",
                "ebur128=peak=true",
                "-f",
                "null",
                "-",
            ),
            path=path,
            timeout=600,
            operation="media loudness analysis",
        )
    except RunnerCaptureError as exc:
        raise VerificationError(f"loudness analysis failed for {path.name!r}") from exc
    return parse_ebur128(completed.stderr)


def verify_media_variant(
    variant: VariantName,
    probe: Mapping[str, object],
    loudness: LoudnessMeasurement,
    *,
    mode: VerificationMode = "production",
    media: MediaSettings | None = None,
) -> tuple[GateResult, ...]:
    """Return explicit format, stream, duration, loudness, and peak rows."""
    if mode == "diagnostic" and media is None:
        raise VerificationError("diagnostic media verification requires explicit fixture settings")
    expected_media = PRODUCTION_MEDIA if mode == "production" else cast(MediaSettings, media)
    streams_value = probe.get("streams")
    streams = (
        cast(list[dict[str, object]], streams_value)
        if isinstance(streams_value, list)
        and all(isinstance(stream, dict) for stream in cast(list[object], streams_value))
        else []
    )
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
    video = videos[0] if len(videos) == 1 else {}
    audio = audios[0] if len(audios) == 1 else {}
    format_value = probe.get("format")
    format_record = cast(dict[str, object], format_value) if isinstance(format_value, dict) else {}
    container = str(format_record.get("format_name", ""))
    format_evidence = {
        "container": container,
        "codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "pixel_format": video.get("pix_fmt"),
        "field_order": video.get("field_order"),
        "frame_rate": video.get("r_frame_rate"),
        "expected": {
            "container": "mp4",
            "codec": "h264",
            "width": expected_media.width,
            "height": expected_media.height,
            "pixel_format": "yuv420p",
            "field_order": "progressive",
            "frame_rate": f"{expected_media.fps}/1",
        },
    }
    format_pass = (
        "mp4" in container.split(",")
        and video.get("codec_name") == "h264"
        and video.get("width") == expected_media.width
        and video.get("height") == expected_media.height
        and video.get("pix_fmt") == "yuv420p"
        and video.get("field_order") == "progressive"
        and video.get("r_frame_rate") == f"{expected_media.fps}/1"
    )
    stream_evidence = {
        "video_streams": len(videos),
        "audio_streams": len(audios),
        "audio_codec": audio.get("codec_name"),
        "audio_profile": audio.get("profile"),
        "sample_rate": audio.get("sample_rate"),
        "channels": audio.get("channels"),
    }
    stream_pass = (
        len(videos) == 1
        and len(audios) == 1
        and audio.get("codec_name") == "aac"
        and audio.get("profile") == "LD"
        and audio.get("sample_rate") == "48000"
        and audio.get("channels") == 2
    )
    expected_duration = expected_media.total_frames / expected_media.fps
    expected_samples = round(expected_duration * 48_000)
    boundary_value = probe.get("program_audio_boundary")
    boundary = cast(dict[str, object], boundary_value) if isinstance(boundary_value, dict) else {}
    audio_index = audio.get("index")
    packet_boundary = (
        _derive_packet_boundary(
            probe,
            audio_stream_index=audio_index,
            expected_samples=expected_samples,
        )
        if isinstance(audio_index, int)
        else {
            "packet_after_program_boundary": True,
            "packet_final_sample_exclusive": None,
            "priming_skip_samples": None,
        }
    )
    decoded_frames = _integer_or_none(video.get("nb_read_frames"))
    durations = {
        "container": _float_or_none(format_record.get("duration")),
        "video": _float_or_none(video.get("duration")),
        "audio": _float_or_none(audio.get("duration")),
    }
    duration_evidence = {
        "expected_frames": expected_media.total_frames,
        "decoded_frames": decoded_frames,
        "expected_seconds": expected_duration,
        "reported_seconds": durations,
        "expected_audio_samples": expected_samples,
        "decoded_audio_samples": boundary.get("last_program_sample_exclusive"),
        "packet_after_program_boundary": packet_boundary["packet_after_program_boundary"],
        "packet_final_sample_exclusive": packet_boundary["packet_final_sample_exclusive"],
        "priming_skip_samples": packet_boundary["priming_skip_samples"],
    }
    duration_pass = (
        decoded_frames == expected_media.total_frames
        and all(
            value is not None and abs(value - expected_duration) <= 1 / expected_media.fps
            for value in durations.values()
        )
        and boundary.get("first_program_sample") == 0
        and boundary.get("last_program_sample_exclusive") == expected_samples
        and packet_boundary["packet_after_program_boundary"] is False
        and packet_boundary["packet_final_sample_exclusive"] == expected_samples
        and packet_boundary["priming_skip_samples"] == 480
    )
    integrated, peak = loudness
    loudness_target, loudness_tolerance, peak_ceiling = (
        (-16.0, 1.0, -1.0) if variant == "narrated" else (-28.0, 2.0, -6.0)
    )
    return (
        _gate(f"MEDIA-{variant}-format", format_pass, format_evidence),
        _gate(f"MEDIA-{variant}-streams", stream_pass, stream_evidence),
        _gate(f"MEDIA-{variant}-duration", duration_pass, duration_evidence),
        _gate(
            f"AUDIO-{variant}-loudness",
            abs(integrated - loudness_target) <= loudness_tolerance,
            {
                "measured_lufs": integrated,
                "target_lufs": loudness_target,
                "tolerance_lu": loudness_tolerance,
            },
        ),
        _gate(
            f"AUDIO-{variant}-peak",
            peak <= peak_ceiling,
            {"measured_dbtp": peak, "maximum_dbtp": peak_ceiling},
        ),
    )


def aggregate_report(
    gates: Sequence[GateResult], *, checksums: Mapping[str, str] | None = None
) -> VerificationReport:
    """Aggregate unique Must rows without erasing any failure evidence."""
    gate_tuple = tuple(gates)
    ids = [gate.id for gate in gate_tuple]
    if len(set(ids)) != len(ids):
        raise VerificationError("verification gate identifiers must be unique")
    if any(not gate.evidence for gate in gate_tuple):
        raise VerificationError("every verification gate must contain structured evidence")
    return VerificationReport(gates=gate_tuple, checksums=checksums or {})


def verify_content_contracts(
    *,
    repository_root: Path,
    states: Sequence[RenderedSceneState],
    classified_asset_ids: frozenset[str],
    delivery: Mapping[str, object],
    external_music_inputs: Sequence[str],
    speaker_speech_detected: bool,
    frame_reviews: Sequence[FrameReview],
    required_frame_samples: Sequence[tuple[VariantName, int, str, str]],
    secret_artifacts: Mapping[str, bytes | str],
    render_manifest: Mapping[str, object] | None = None,
) -> tuple[GateResult, ...]:
    """Verify authenticity, rights, accessibility, layout, audio, and secrecy."""
    authenticity_findings: list[dict[str, object]] = []
    semantic_findings: list[dict[str, object]] = []
    expected_state_hashes = _render_state_hashes(render_manifest)
    for state in states:
        state_name = f"{state.scene_id}/{state.state_id}"
        try:
            root = ElementTree.fromstring(state.svg)
        except ElementTree.ParseError:
            semantic_findings.append({"state": state_name, "reason": "invalid-rendered-svg"})
        else:
            raw_ledger = root.attrib.get("data-content-ledger-json")
            if raw_ledger is None:
                semantic_findings.append(
                    {"state": state_name, "reason": "missing-renderer-content-ledger"}
                )
            else:
                try:
                    ledger_value: object = json.loads(raw_ledger)
                except json.JSONDecodeError:
                    ledger_value = None
                if ledger_value != list(state.content_ledger):
                    semantic_findings.append(
                        {"state": state_name, "reason": "renderer-content-ledger-mismatch"}
                    )
            expected_rectangles = ";".join(
                f"{value.x},{value.y},{value.width},{value.height}"
                for value in state.evidence_rectangles
            )
            if root.attrib.get("data-evidence-rectangles") != expected_rectangles:
                semantic_findings.append(
                    {"state": state_name, "reason": "renderer-evidence-geometry-mismatch"}
                )
        expected_digest = expected_state_hashes.get((state.scene_id, state.state_id))
        if expected_digest is not None and state.digest != expected_digest:
            semantic_findings.append(
                {
                    "state": state_name,
                    "reason": "render-manifest-state-digest-mismatch",
                    "expected_sha256": expected_digest,
                    "actual_sha256": state.digest,
                }
            )
        for reference in state.references:
            path_text = reference.path.split("#", maxsplit=1)[0]
            try:
                content = _reference_bytes(repository_root, path_text, reference.revision)
            except VerificationError as exc:
                authenticity_findings.append(
                    {
                        "state": f"{state.scene_id}/{state.state_id}",
                        "path": path_text,
                        "reason": str(exc),
                    }
                )
                continue
            actual = hashlib.sha256(content).hexdigest()
            if actual != reference.sha256:
                authenticity_findings.append(
                    {
                        "state": f"{state.scene_id}/{state.state_id}",
                        "path": path_text,
                        "expected_sha256": reference.sha256,
                        "actual_sha256": actual,
                    }
                )
    end_card_disclosed = any(
        state.scene_id == "promise" and AI_NARRATION_DISCLOSURE in state.display_text
        for state in states
    )
    delivery_disclosed = delivery.get("ai_narration_disclosure") == AI_NARRATION_DISCLOSURE
    speaker_caption_frames = sorted(
        review.frame
        for review in frame_reviews
        if review.variant == "speaker" and review.narration_caption_present
    )
    scene_ids = {state.scene_id for state in states}
    mute_safe = {
        state.scene_id: state
        for state in states
        if state.state_id == "mute_safe_copy"
        and state.copy_rectangle is not None
        and state.end_frame - state.start_frame >= 60
        and state.display_text.strip()
    }
    unknown_assets = sorted(
        {asset_id for state in states for asset_id in state.asset_ids} - classified_asset_ids
    )
    review_index = {
        (review.variant, review.frame, review.scene_id, review.state_id): review
        for review in frame_reviews
    }
    unsafe_frames: list[dict[str, object]] = []
    for sample in required_frame_samples:
        review = review_index.get(sample)
        if review is None:
            unsafe_frames.append(
                {
                    "variant": sample[0],
                    "frame": sample[1],
                    "scene_id": sample[2],
                    "state_id": sample[3],
                    "reason": "missing-review",
                }
            )
            continue
        required_size = 44 if review.narration_caption_present else 32
        if (
            review.minimum_text_size < required_size
            or not review.within_title_safe
            or review.minimum_contrast < 4.5
        ):
            unsafe_frames.append(
                {
                    "variant": review.variant,
                    "frame": review.frame,
                    "scene_id": review.scene_id,
                    "state_id": review.state_id,
                    "minimum_text_size": review.minimum_text_size,
                    "required_text_size": required_size,
                    "within_title_safe": review.within_title_safe,
                    "minimum_contrast": review.minimum_contrast,
                }
            )
    secret_findings = _secret_findings(secret_artifacts)
    return (
        _gate(
            "AUTH-evidence",
            not authenticity_findings and not semantic_findings,
            {
                "references_checked": sum(len(state.references) for state in states),
                "findings": authenticity_findings,
                "semantic_findings": semantic_findings,
            },
        ),
        _gate(
            "DISCLOSURE-delivery",
            delivery_disclosed and end_card_disclosed,
            {
                "expected": AI_NARRATION_DISCLOSURE,
                "delivery_present": delivery_disclosed,
                "end_card_present": end_card_disclosed,
            },
        ),
        _gate(
            "CAPTION-speaker",
            not speaker_caption_frames,
            {"narration_caption_frames": speaker_caption_frames},
        ),
        _gate(
            "ACCESS-mute-safe",
            set(mute_safe) == scene_ids,
            {
                "scene_count": len(scene_ids),
                "passing_scenes": sorted(mute_safe),
                "missing_scenes": sorted(scene_ids - set(mute_safe)),
            },
        ),
        _gate(
            "FRAME-final-layout",
            not unsafe_frames and bool(required_frame_samples),
            {
                "required_samples": len(required_frame_samples),
                "reviewed_samples": len(review_index),
                "unsafe_frames": unsafe_frames,
            },
        ),
        _gate(
            "RIGHTS-assets",
            not unknown_assets,
            {
                "classified_asset_ids": sorted(classified_asset_ids),
                "unclassified_asset_ids": unknown_assets,
            },
        ),
        _gate(
            "AUDIO-procedural-only",
            not external_music_inputs,
            {"external_music_inputs": list(external_music_inputs)},
        ),
        _gate(
            "AUDIO-speaker-speech",
            not speaker_speech_detected,
            {"speech_detected": speaker_speech_detected, "variant": "speaker"},
        ),
        _gate(
            "SECURITY-secrets",
            not secret_findings,
            {"artifacts_scanned": sorted(secret_artifacts), "findings": secret_findings},
        ),
    )


def required_frame_samples(
    states: Sequence[RenderedSceneState],
    caption_frames: Sequence[int],
) -> tuple[tuple[VariantName, int, str, str], ...]:
    """Return every state-final and narrated caption-transition sample."""
    by_frame = {
        frame: state for state in states for frame in range(state.start_frame, state.end_frame)
    }
    samples: set[tuple[VariantName, int, str, str]] = set()
    for state in states:
        for variant in ("narrated", "speaker"):
            samples.add((variant, state.end_frame - 1, state.scene_id, state.state_id))
    for frame in caption_frames:
        state = by_frame.get(frame)
        if state is None:
            raise VerificationError(f"caption sample frame {frame} is outside the visual timeline")
        samples.add(("narrated", frame, state.scene_id, state.state_id))
    return tuple(sorted(samples))


def verify_evidence_frame_share(
    states: Sequence[VisualState] | Sequence[RenderedSceneState],
    *,
    width: int,
    height: int,
    total_frames: int,
) -> GateResult:
    """Verify C-003 from the exact rectangles consumed by the renderer."""
    frame_area = width * height
    if frame_area <= 0 or total_frames <= 0:
        raise VerificationError("frame dimensions and total frame count must be positive")
    dominant_frames = 0
    states_evidence: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []
    cursor = 0
    for state in states:
        state_id = state.id if isinstance(state, VisualState) else state.state_id
        if state.start_frame != cursor:
            findings.append(
                {
                    "state_id": state_id,
                    "reason": "gap-or-overlap",
                    "expected_start_frame": cursor,
                    "actual_start_frame": state.start_frame,
                }
            )
        union_area = _rectangle_union_area(state.evidence_rectangles)
        is_dominant = union_area * 2 >= frame_area
        frame_count = state.end_frame - state.start_frame
        if frame_count <= 0:
            findings.append(
                {
                    "state_id": state_id,
                    "reason": "non-positive-frame-duration",
                    "start_frame": state.start_frame,
                    "end_frame": state.end_frame,
                }
            )
        for index, rectangle in enumerate(state.evidence_rectangles):
            if (
                rectangle.width <= 0
                or rectangle.height <= 0
                or rectangle.x < 0
                or rectangle.y < 0
                or rectangle.x + rectangle.width > width
                or rectangle.y + rectangle.height > height
            ):
                findings.append(
                    {
                        "state_id": state_id,
                        "rectangle_index": index,
                        "reason": "rectangle-outside-frame",
                        "rectangle": {
                            "x": rectangle.x,
                            "y": rectangle.y,
                            "width": rectangle.width,
                            "height": rectangle.height,
                        },
                    }
                )
        if is_dominant:
            dominant_frames += max(0, frame_count)
        states_evidence.append(
            {
                "state_id": state_id,
                "frames": frame_count,
                "evidence_union_area": union_area,
                "frame_area": frame_area,
                "dominant": is_dominant,
            }
        )
        cursor = state.end_frame
    if cursor != total_frames:
        findings.append(
            {
                "reason": "incomplete-timeline",
                "expected_end_frame": total_frames,
                "actual_end_frame": cursor,
            }
        )
    percentage = dominant_frames * 100 / total_frames
    return _gate(
        "C-003-evidence-frame-share",
        not findings and 60 <= percentage <= 80,
        {
            "dominant_frames": dominant_frames,
            "total_frames": total_frames,
            "percentage": percentage,
            "inclusive_range_percent": [60, 80],
            "states": states_evidence,
            "timeline_geometry_findings": findings,
        },
    )


def semantic_manifest_sha256(manifest: Mapping[str, object]) -> str:
    """Hash render semantics while excluding only container-level metadata."""
    semantic = _json_clone(manifest)
    outputs = semantic.get("outputs")
    if isinstance(outputs, dict):
        output_records = cast(dict[str, object], outputs)
        for value in output_records.values():
            if isinstance(value, dict):
                output = cast(dict[str, object], value)
                for field_name in ("path", "sha256", "probe"):
                    output.pop(field_name, None)
    shared = semantic.get("shared_picture")
    if isinstance(shared, dict):
        shared_record = cast(dict[str, object], shared)
        for field_name in ("path", "cache_key", "sha256", "probe"):
            shared_record.pop(field_name, None)
    serialized = json.dumps(
        semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(serialized).hexdigest()


def verify_reproduction(
    approved: Mapping[str, object],
    reproduced: Mapping[str, object],
    *,
    actual_toolchain: Mapping[str, object],
    clean_checkout: bool,
    speech_api_calls: int,
    mode: VerificationMode = "production",
) -> GateResult:
    """Require exact-toolchain, offline, exact semantic reproduction."""
    if mode == "production":
        return GateResult(
            "REPRO-exact",
            "fail",
            {
                "reason": "actual-probe-and-offline-run-required",
                "required_runner": "clean-checkout-network-denied",
                "required_comparison": "decoded-files-and-semantic-manifest",
            },
        )
    approved_toolchain = approved.get("toolchain")
    reproduced_toolchain = reproduced.get("toolchain")
    if actual_toolchain != approved_toolchain or reproduced_toolchain != approved_toolchain:
        return GateResult(
            "REPRO-exact",
            "fail",
            {
                "reason": "toolchain-mismatch",
                "comparison": "exact-structured-equality",
                "approved_toolchain_sha256": _canonical_sha256(approved_toolchain),
                "actual_toolchain_sha256": _canonical_sha256(actual_toolchain),
                "reproduced_toolchain_sha256": _canonical_sha256(reproduced_toolchain),
            },
        )
    approved_semantic = semantic_manifest_sha256(approved)
    reproduced_semantic = semantic_manifest_sha256(reproduced)
    approved_hashes = _semantic_hash_evidence(approved)
    reproduced_hashes = _semantic_hash_evidence(reproduced)
    passed = (
        clean_checkout
        and speech_api_calls == 0
        and approved_semantic == reproduced_semantic
        and approved_hashes == reproduced_hashes
    )
    return _gate(
        "REPRO-exact",
        passed,
        {
            "reason": "matched" if passed else "semantic-mismatch",
            "comparison": "exact-hash",
            "clean_checkout": clean_checkout,
            "speech_api_calls": speech_api_calls,
            "approved_semantic_manifest_sha256": approved_semantic,
            "reproduced_semantic_manifest_sha256": reproduced_semantic,
            "approved_hashes": approved_hashes,
            "reproduced_hashes": reproduced_hashes,
            "container_metadata_excluded": True,
        },
    )


def build_offline_reproduction_command(
    *,
    checkout: Path,
    selected_wav: Path,
    selected_wav_sha256: str,
    python: Path,
    bwrap: Path = Path("/usr/bin/bwrap"),
) -> tuple[str, ...]:
    """Build the fixed clean-checkout render command inside a denied network namespace."""
    resolved_checkout = checkout.resolve()
    resolved_selected = selected_wav.resolve()
    resolved_python = python.resolve()
    resolved_bwrap = bwrap.resolve()
    if not resolved_checkout.is_dir():
        raise VerificationError("offline reproduction checkout must exist")
    if not resolved_selected.is_file() or not _is_sha256(selected_wav_sha256):
        raise VerificationError("offline reproduction selected WAV is missing or unchecksummed")
    if (
        not resolved_python.is_file()
        or not os.access(resolved_python, os.X_OK)
        or not resolved_bwrap.is_file()
        or not os.access(resolved_bwrap, os.X_OK)
    ):
        raise VerificationError("offline reproduction executables are unavailable")
    python_path = (resolved_checkout / "media" / "repository-explainer").as_posix()
    return (
        str(resolved_bwrap),
        "--unshare-net",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        str(resolved_checkout),
        str(resolved_checkout),
        "--tmpfs",
        "/tmp",
        "--dir",
        "/tmp/home",
        "--setenv",
        "HOME",
        "/tmp/home",
        "--setenv",
        "PATH",
        "/usr/local/bin:/usr/bin:/bin",
        "--setenv",
        "PYTHONPATH",
        python_path,
        "--setenv",
        "VIDEO_PIPELINE_OFFLINE_REPRODUCTION",
        "1",
        "--chdir",
        str(resolved_checkout),
        "--",
        str(resolved_python),
        "-m",
        "video_pipeline.verify",
        "--offline-render",
        str(resolved_selected),
        "--selected-wav-sha256",
        selected_wav_sha256,
    )


def run_offline_reproduction(
    *,
    repository_root: Path,
    work_root: Path,
    approved_manifest: Mapping[str, object],
    selected_wav: Path,
    selected_wav_sha256: str,
    python: Path | None = None,
) -> GateResult:
    """Rerender at the approved revision with exact tools and no network or Speech key."""
    root = repository_root.resolve()
    trusted_work = work_root.resolve()
    required_work = root / "dist" / "video" / "work"
    if not trusted_work.is_relative_to(required_work):
        return GateResult(
            "REPRO-exact",
            "fail",
            {
                "reason": "untrusted-work-root",
                "required_root": str(required_work),
                "actual_root": str(trusted_work),
            },
        )
    if _file_sha256_or_none(selected_wav) != selected_wav_sha256:
        return GateResult(
            "REPRO-exact",
            "fail",
            {"reason": "selected-narration-checksum-mismatch"},
        )
    trusted_work.mkdir(parents=True, exist_ok=True)
    try:
        capabilities = probe_render_capabilities(
            work_root=trusted_work / "toolchain-probe",
        )
        actual_toolchain = toolchain_manifest(capabilities, RenderConfig.production())
    except RenderError as exc:
        return GateResult(
            "REPRO-exact",
            "fail",
            {"reason": "actual-toolchain-probe-failed", "error_class": type(exc).__name__},
        )
    if actual_toolchain != approved_manifest.get("toolchain"):
        return GateResult(
            "REPRO-exact",
            "fail",
            {
                "reason": "toolchain-mismatch",
                "comparison": "actual-probe-exact-structured-equality",
                "approved_toolchain_sha256": _canonical_sha256(approved_manifest.get("toolchain")),
                "actual_toolchain_sha256": _canonical_sha256(actual_toolchain),
            },
        )
    revision = approved_manifest.get("source_revision")
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        return GateResult(
            "REPRO-exact",
            "fail",
            {"reason": "invalid-approved-source-revision"},
        )
    environment = build_child_environment({})
    with tempfile.TemporaryDirectory(dir=trusted_work, prefix="reproduction-") as temporary:
        temporary_root = Path(temporary)
        checkout = temporary_root / "checkout"
        added = False
        try:
            _run_reproduction_process(
                ("git", "-C", str(root), "worktree", "add", "--detach", str(checkout), revision),
                cwd=root,
                environment=environment,
                timeout=120,
                operation="reproduction clean checkout",
            )
            added = True
            before_status = _run_reproduction_process(
                ("git", "status", "--porcelain"),
                cwd=checkout,
                environment=environment,
                timeout=30,
                operation="reproduction pre-status",
            )
            if before_status:
                return GateResult(
                    "REPRO-exact",
                    "fail",
                    {"reason": "clean-checkout-precondition-failed"},
                )
            command = build_offline_reproduction_command(
                checkout=checkout,
                selected_wav=selected_wav,
                selected_wav_sha256=selected_wav_sha256,
                python=Path(sys.executable) if python is None else python,
            )
            _run_reproduction_process(
                command,
                cwd=checkout,
                environment=environment,
                timeout=1800,
                operation="network-denied offline reproduction",
            )
            after_status = _run_reproduction_process(
                ("git", "status", "--porcelain"),
                cwd=checkout,
                environment=environment,
                timeout=30,
                operation="reproduction post-status",
            )
            if after_status:
                return GateResult(
                    "REPRO-exact",
                    "fail",
                    {"reason": "clean-checkout-postcondition-failed"},
                )
            reproduced_manifest_path = (
                checkout / "dist" / "video" / "candidate" / "render-manifest.json"
            )
            reproduced_manifest = _read_json_mapping(
                reproduced_manifest_path,
                "reproduced render manifest",
            )
            actual_semantics = _actual_reproduction_semantics(checkout, capabilities.ffmpeg)
            expected_semantics = _semantic_hash_evidence(approved_manifest)
            approved_semantic = semantic_manifest_sha256(approved_manifest)
            reproduced_semantic = semantic_manifest_sha256(reproduced_manifest)
            passed = (
                actual_semantics == expected_semantics and approved_semantic == reproduced_semantic
            )
            return _gate(
                "REPRO-exact",
                passed,
                {
                    "reason": "matched" if passed else "semantic-mismatch",
                    "comparison": "actual-exact-decoded-hash",
                    "clean_checkout": True,
                    "network_namespace": "denied",
                    "speech_credentials_available": False,
                    "actual_toolchain_probe": True,
                    "actual": actual_semantics,
                    "expected": expected_semantics,
                    "approved_semantic_manifest_sha256": approved_semantic,
                    "reproduced_semantic_manifest_sha256": reproduced_semantic,
                    "container_metadata_excluded": True,
                },
            )
        except (VerificationError, RunnerCaptureError, OSError) as exc:
            return GateResult(
                "REPRO-exact",
                "fail",
                {
                    "reason": "offline-reproduction-failed",
                    "error_class": type(exc).__name__,
                },
            )
        finally:
            if added:
                with suppress(RunnerCaptureError):
                    _run_reproduction_process(
                        (
                            "git",
                            "-C",
                            str(root),
                            "worktree",
                            "remove",
                            "--force",
                            str(checkout),
                        ),
                        cwd=root,
                        environment=environment,
                        timeout=120,
                        operation="reproduction checkout cleanup",
                    )


def verify_render_manifest(
    manifest: Mapping[str, object],
    *,
    media: MediaSettings,
    states: Sequence[RenderedSceneState],
) -> GateResult:
    """Strictly validate the T7 manifest and its renderer state ledger."""
    findings: list[dict[str, object]] = []
    if set(manifest) != _RENDER_MANIFEST_FIELDS:
        findings.append(
            {
                "field": "render-manifest",
                "expected_fields": sorted(_RENDER_MANIFEST_FIELDS),
                "actual_fields": sorted(manifest),
            }
        )
    if manifest.get("schema_version") != 1:
        findings.append(
            {"field": "schema_version", "expected": 1, "actual": manifest.get("schema_version")}
        )
    source_revision = manifest.get("source_revision")
    if (
        not isinstance(source_revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", source_revision) is None
    ):
        findings.append(
            {
                "field": "source_revision",
                "reason": "expected-full-git-object-id",
                "actual": source_revision,
            }
        )
    timing = _mapping(manifest.get("project_timing"))
    expected_timing = {
        "width": media.width,
        "height": media.height,
        "fps": media.fps,
        "total_frames": media.total_frames,
    }
    for key, expected in expected_timing.items():
        if timing.get(key) != expected:
            findings.append(
                {"field": f"project_timing.{key}", "expected": expected, "actual": timing.get(key)}
            )
    records_value = timing.get("states")
    records = cast(list[object], records_value) if isinstance(records_value, list) else []
    if len(records) != len(states):
        findings.append(
            {
                "field": "project_timing.states",
                "expected_count": len(states),
                "actual_count": len(records),
            }
        )
    else:
        for index, (value, state) in enumerate(zip(records, states, strict=True)):
            record = _mapping(value)
            expected = {
                "scene_id": state.scene_id,
                "state_id": state.state_id,
                "start_frame": state.start_frame,
                "end_frame": state.end_frame,
                "frame_count": state.end_frame - state.start_frame,
                "source_sha256": state.digest,
                "references": [
                    {
                        "kind": reference.kind,
                        "path": reference.path,
                        "sha256": reference.sha256,
                        "revision": reference.revision,
                    }
                    for reference in state.references
                ],
            }
            for key, expected_value in expected.items():
                if record.get(key) != expected_value:
                    findings.append(
                        {
                            "field": f"project_timing.states[{index}].{key}",
                            "expected": expected_value,
                            "actual": record.get(key),
                        }
                    )
    outputs = _mapping(manifest.get("outputs"))
    if set(outputs) != {"narrated", "speaker"}:
        findings.append(
            {"field": "outputs", "expected": ["narrated", "speaker"], "actual": sorted(outputs)}
        )
    for name in ("narrated", "speaker"):
        output = _mapping(outputs.get(name))
        expected_inputs = (
            [
                "shared_picture",
                "captions_srt",
                "selected_narration_wav",
                "procedural_tonal_bed_and_cues",
            ]
            if name == "narrated"
            else ["shared_picture", "procedural_tonal_bed_and_cues"]
        )
        if output.get("inputs") != expected_inputs:
            findings.append(
                {
                    "field": f"outputs.{name}.inputs",
                    "expected": expected_inputs,
                    "actual": output.get("inputs"),
                }
            )
        for hash_field in ("sha256", "decoded_video_sha256", "decoded_pcm_sha256"):
            if not _is_sha256(output.get(hash_field)):
                findings.append(
                    {"field": f"outputs.{name}.{hash_field}", "reason": "invalid-sha256"}
                )
        if output.get("decoded_audio_samples_per_channel") != round(
            media.total_frames / media.fps * 48_000
        ):
            findings.append(
                {
                    "field": f"outputs.{name}.decoded_audio_samples_per_channel",
                    "expected": round(media.total_frames / media.fps * 48_000),
                    "actual": output.get("decoded_audio_samples_per_channel"),
                }
            )
    inputs = _mapping(manifest.get("inputs"))
    for input_name in ("captions_srt", "selected_narration_wav", "render_recipe"):
        record = _mapping(inputs.get(input_name))
        if not _is_sha256(record.get("sha256")):
            findings.append(
                {
                    "field": f"inputs.{input_name}.sha256",
                    "reason": "invalid-sha256",
                }
            )
    selected_narration = _mapping(inputs.get("selected_narration_wav"))
    if selected_narration.get("provider_required_for_reproduction") is not False:
        findings.append(
            {
                "field": "inputs.selected_narration_wav.provider_required_for_reproduction",
                "expected": False,
                "actual": selected_narration.get("provider_required_for_reproduction"),
            }
        )
    audio_targets = _mapping(manifest.get("audio_targets"))
    expected_targets = {
        "narrated": {"integrated_lufs": -16, "true_peak_dbtp": -1},
        "speaker": {"integrated_lufs": -28, "true_peak_dbtp": -6},
    }
    if audio_targets != expected_targets:
        findings.append(
            {
                "field": "audio_targets",
                "expected": expected_targets,
                "actual": audio_targets,
            }
        )
    toolchain = _mapping(manifest.get("toolchain"))
    if not toolchain:
        findings.append({"field": "toolchain", "reason": "missing-exact-toolchain"})
    shared_picture = _mapping(manifest.get("shared_picture"))
    if not _is_sha256(shared_picture.get("decoded_video_sha256")):
        findings.append(
            {
                "field": "shared_picture.decoded_video_sha256",
                "reason": "invalid-sha256",
            }
        )
    synthesis = _mapping(manifest.get("synthesis"))
    if synthesis.get("external_music_inputs") != []:
        findings.append(
            {
                "field": "synthesis.external_music_inputs",
                "expected": [],
                "actual": synthesis.get("external_music_inputs"),
            }
        )
    return _gate(
        "MANIFEST-render",
        not findings,
        {"states_checked": len(states), "outputs_checked": sorted(outputs), "findings": findings},
    )


def verify_asset_provenance(
    payload: Mapping[str, object],
    *,
    repository_root: Path,
) -> tuple[GateResult, frozenset[str]]:
    """Validate rights classification and byte identity for every asset."""
    assets_value = payload.get("assets")
    assets = cast(list[object], assets_value) if isinstance(assets_value, list) else []
    findings: list[dict[str, object]] = []
    classified: set[str] = set()
    if payload.get("schema_version") != 1 or not assets:
        findings.append({"field": "asset-provenance", "reason": "invalid-schema-or-empty-assets"})
    for index, value in enumerate(assets):
        record = _mapping(value)
        asset_id = record.get("id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in classified:
            findings.append({"field": f"assets[{index}].id", "reason": "missing-or-duplicate"})
            continue
        classified.add(asset_id)
        source = record.get("source")
        license_id = record.get("license_id")
        generation = record.get("generation_method")
        if (
            not isinstance(source, str)
            or not source
            or not (
                (isinstance(license_id, str) and license_id)
                or (isinstance(generation, str) and generation)
            )
        ):
            findings.append({"asset_id": asset_id, "reason": "unclassified-rights"})
        repository_path = record.get("repository_path")
        system_path = record.get("system_path")
        raw_path = repository_path if isinstance(repository_path, str) else system_path
        if not isinstance(raw_path, str) or (
            isinstance(repository_path, str) == isinstance(system_path, str)
        ):
            findings.append({"asset_id": asset_id, "reason": "invalid-path-ownership"})
            continue
        path = (
            (repository_root / raw_path).resolve()
            if isinstance(repository_path, str)
            else Path(raw_path).resolve()
        )
        actual = _file_sha256_or_none(path)
        if actual != record.get("sha256"):
            findings.append(
                {
                    "asset_id": asset_id,
                    "reason": "checksum-mismatch",
                    "expected_sha256": record.get("sha256"),
                    "actual_sha256": actual,
                }
            )
    return (
        _gate(
            "RIGHTS-provenance",
            not findings,
            {
                "asset_count": len(assets),
                "classified_asset_ids": sorted(classified),
                "findings": findings,
            },
        ),
        frozenset(classified),
    )


def verify_closed_world_provenance(
    manifest: Mapping[str, object],
    *,
    states: Sequence[RenderedSceneState],
    asset_provenance: Mapping[str, object],
    repository_root: Path,
    selected_wav: Path,
) -> GateResult:
    """Bind every renderer and audio input to one classified provenance record."""
    assets_value = asset_provenance.get("assets")
    assets = cast(list[object], assets_value) if isinstance(assets_value, list) else []
    records = {
        cast(str, record["id"]): record
        for value in assets
        if (record := _mapping(value)) and isinstance(record.get("id"), str)
    }
    required_ids = {
        *(asset_id for state in states for asset_id in state.asset_ids),
        "selected_narration_wav",
        "procedural_tonal_bed_and_cues",
    }
    missing = sorted(required_ids - set(records))
    mismatches: list[dict[str, object]] = []
    inputs = _mapping(manifest.get("inputs"))
    selected_input = _mapping(inputs.get("selected_narration_wav"))
    selected_asset = records.get("selected_narration_wav")
    selected_digest = _file_sha256_or_none(selected_wav)
    if selected_asset is not None and (
        selected_asset.get("kind") != "audio"
        or selected_asset.get("sha256") != selected_input.get("sha256")
        or selected_asset.get("sha256") != selected_digest
    ):
        mismatches.append(
            {
                "input": "selected_narration_wav",
                "reason": "path-or-checksum-not-bound-to-render-input",
            }
        )
    synthesis = _mapping(manifest.get("synthesis"))
    procedural = records.get("procedural_tonal_bed_and_cues")
    if procedural is not None and (
        procedural.get("kind") != "audio"
        or not isinstance(procedural.get("generation_method"), str)
        or not cast(str, procedural.get("generation_method", "")).strip()
        or synthesis.get("external_music_inputs") != []
    ):
        mismatches.append(
            {
                "input": "procedural_tonal_bed_and_cues",
                "reason": "procedural-generation-not-closed",
            }
        )
    toolchain = _mapping(manifest.get("toolchain"))
    fonts_value = toolchain.get("fonts")
    fonts = cast(list[object], fonts_value) if isinstance(fonts_value, list) else []
    classified_hashes = {
        record.get("sha256") for record in records.values() if record.get("kind") == "font"
    }
    for index, value in enumerate(fonts):
        font = _mapping(value)
        if font.get("sha256") not in classified_hashes:
            mismatches.append(
                {
                    "input": f"toolchain.fonts[{index}]",
                    "reason": "font-not-bound-to-classified-asset",
                }
            )
    unused = sorted(set(records) - required_ids)
    return _gate(
        "RIGHTS-closed-world",
        not missing and not mismatches and not unused,
        {
            "required_classifications": sorted(required_ids),
            "missing_classifications": missing,
            "mismatches": mismatches,
            "unconsumed_asset_ids": unused,
            "repository_root": str(repository_root.resolve()),
        },
    )


def checksum_files(files: Mapping[str, Path]) -> dict[str, str]:
    """Return deterministic SHA-256 output for every named deliverable."""
    checksums: dict[str, str] = {}
    for name, path in sorted(files.items()):
        digest = _file_sha256_or_none(path)
        if digest is None:
            raise VerificationError(f"deliverable {name!r} could not be read")
        checksums[name] = digest
    return checksums


def write_verification_report(
    path: Path,
    checksum_path: Path,
    report: VerificationReport,
) -> None:
    """Atomically write the canonical report and its independent SHA-256 record."""
    if path.resolve() == checksum_path.resolve():
        raise VerificationError("verification report and checksum paths must differ")
    path.parent.mkdir(parents=True, exist_ok=True)
    checksum_path.parent.mkdir(parents=True, exist_ok=True)
    report_temporary = path.with_name(f".{path.name}.tmp")
    checksum_temporary = checksum_path.with_name(f".{checksum_path.name}.tmp")
    report_bytes = (json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n").encode()
    checksum_bytes = (f"{hashlib.sha256(report_bytes).hexdigest()}  {path.name}\n").encode()
    try:
        report_temporary.write_bytes(report_bytes)
        checksum_temporary.write_bytes(checksum_bytes)
        report_temporary.replace(path)
        checksum_temporary.replace(checksum_path)
    finally:
        report_temporary.unlink(missing_ok=True)
        checksum_temporary.unlink(missing_ok=True)


def _gate(gate_id: str, passed: bool, evidence: Mapping[str, object]) -> GateResult:
    return GateResult(gate_id, "pass" if passed else "fail", evidence)


def _integer_or_none(value: object) -> int | None:
    try:
        return int(cast(str | int, value))
    except TypeError, ValueError:
        return None


def _float_or_none(value: object) -> float | None:
    try:
        return float(cast(str | int | float, value))
    except TypeError, ValueError:
        return None


def _reference_bytes(root: Path, path_text: str, revision: str | None) -> bytes:
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != path_text:
        raise VerificationError("reference path is not normalized and repository-relative")
    if revision is None:
        try:
            return (root / relative).read_bytes()
        except OSError as exc:
            raise VerificationError("reference could not be read") from exc
    try:
        completed = run_capture_process(
            ("git", "show", f"{revision}:{path_text}"),
            cwd=root,
            environment=build_child_environment({}),
            timeout=120,
            operation="revision-bound reference lookup",
            # The bytes are hashed, never retained in evidence; secret scanning is
            # performed over the closed delivery inventory by its dedicated gate.
            screen_output=False,
        )
    except RunnerCaptureError as exc:
        raise VerificationError("revision-bound reference lookup failed") from exc
    if completed.returncode != 0:
        raise VerificationError("reference is unavailable at its recorded revision")
    return completed.stdout.encode()


def _secret_findings(artifacts: Mapping[str, bytes | str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for artifact, content in sorted(artifacts.items()):
        text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else content
        for classification in _secret_classes(text, include_entropy=True):
            findings.append({"artifact": artifact, "classification": classification})
    return findings


def _raise_missing_diagnostic_media() -> MediaSettings:
    raise VerificationError("diagnostic candidate verification requires explicit media settings")


def _decoded_candidate_hashes(
    path: Path,
    *,
    ffmpeg: str,
    total_samples: int,
) -> dict[str, str]:
    video_digest, _ = hash_command_output(
        (
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-f",
            "framemd5",
            "-",
        ),
        "candidate decoded video hash",
        timeout_seconds=600,
        max_output_bytes=64 * 1024 * 1024,
    )
    pcm_digest, pcm_bytes = hash_command_output(
        (
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-c:a",
            "pcm_s16le",
            "-f",
            "s16le",
            "-",
        ),
        "candidate decoded PCM hash",
        timeout_seconds=600,
        max_output_bytes=total_samples * 4,
    )
    if pcm_bytes != total_samples * 4:
        raise RenderError("candidate decoded PCM did not reach the exact program boundary")
    return {
        "decoded_video_sha256": video_digest,
        "decoded_pcm_sha256": pcm_digest,
    }


def _decoded_frame_hash(
    path: Path,
    *,
    frame: int,
    width: int,
    height: int,
    ffmpeg: str,
) -> str:
    digest, byte_count = hash_command_output(
        (
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-vf",
            f"select=eq(n\\,{frame})",
            "-frames:v",
            "1",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "-",
        ),
        f"candidate frame {frame}",
        timeout_seconds=120,
        max_output_bytes=width * height * 3,
    )
    if byte_count != width * height * 3:
        raise RenderError(f"candidate frame {frame} did not decode exactly once")
    return digest


def _caption_transition_frames(
    raw: bytes,
    *,
    fps: int,
    total_frames: int,
) -> tuple[tuple[int, ...], list[dict[str, object]]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return (), [{"reason": "captions-not-utf8"}]
    matches = tuple(_SRT_TIMING.finditer(text))
    if not matches:
        return (), [{"reason": "captions-have-no-timing-records"}]
    frames: set[int] = set()
    findings: list[dict[str, object]] = []
    previous_end = 0
    for index, match in enumerate(matches):
        start = _srt_timestamp_frame(match.group("start"), fps)
        end = _srt_timestamp_frame(match.group("end"), fps)
        if start < previous_end or end <= start or end > total_frames:
            findings.append(
                {
                    "caption_index": index,
                    "reason": "invalid-or-overlapping-caption-timing",
                    "start_frame": start,
                    "end_frame": end,
                }
            )
        else:
            frames.update((start, end - 1))
        previous_end = end
    return tuple(sorted(frames)), findings


def _srt_timestamp_frame(value: str, fps: int) -> int:
    hours = int(value[0:2])
    minutes = int(value[3:5])
    seconds = int(value[6:8])
    milliseconds = int(value[9:12])
    total_milliseconds = hours * 3_600_000 + minutes * 60_000 + seconds * 1000 + milliseconds
    return (total_milliseconds * fps + 999) // 1000


def _scan_file_secret_classes(path: Path) -> tuple[str, ...]:
    try:
        include_entropy = path.suffix.lower() in {".json", ".srt", ".txt", ".sha256", ".svg"}
        classifications: set[str] = set()
        overlap = b""
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                combined = overlap + chunk
                text = combined.decode("utf-8", errors="ignore")
                classifications.update(_secret_classes(text, include_entropy=include_entropy))
                overlap = combined[-256:]
        return tuple(sorted(classifications))
    except OSError:
        return ("unreadable-required-artifact",)


def _secret_classes(text: str, *, include_entropy: bool) -> tuple[str, ...]:
    for classification, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return (classification,)
    if include_entropy:
        for match in _HIGH_ENTROPY_CANDIDATE.finditer(text):
            candidate = match.group()
            if _looks_like_digest(candidate):
                continue
            if _shannon_entropy(candidate) >= 4.5:
                return ("high-entropy-token",)
    return ()


def _looks_like_digest(value: str) -> bool:
    return len(value) in {40, 64} and re.fullmatch(r"[0-9a-fA-F]+", value) is not None


def _shannon_entropy(value: str) -> float:
    frequencies = {character: value.count(character) for character in set(value)}
    return -sum(
        (count / len(value)) * math.log2(count / len(value)) for count in frequencies.values()
    )


def _derive_packet_boundary(
    probe: Mapping[str, object],
    *,
    audio_stream_index: int,
    expected_samples: int,
) -> dict[str, object]:
    packets_value = probe.get("packets")
    packets = (
        [
            cast(dict[str, object], value)
            for value in cast(list[object], packets_value)
            if isinstance(value, dict)
            and cast(dict[str, object], value).get("stream_index") == audio_stream_index
        ]
        if isinstance(packets_value, list)
        else []
    )
    if not packets:
        return {
            "packet_after_program_boundary": True,
            "packet_final_sample_exclusive": None,
            "priming_skip_samples": None,
        }
    first_side_data = packets[0].get("side_data_list")
    side_data = (
        cast(list[dict[str, object]], first_side_data)
        if isinstance(first_side_data, list)
        and all(isinstance(value, dict) for value in cast(list[object], first_side_data))
        else []
    )
    priming = next(
        (
            _integer_or_none(value.get("skip_samples"))
            for value in side_data
            if value.get("side_data_type") == "Skip Samples"
        ),
        None,
    )
    final = packets[-1]
    pts = _integer_or_none(final.get("pts"))
    duration = _integer_or_none(final.get("duration"))
    final_side_value = final.get("side_data_list")
    final_side = (
        cast(list[dict[str, object]], final_side_value)
        if isinstance(final_side_value, list)
        and all(isinstance(value, dict) for value in cast(list[object], final_side_value))
        else []
    )
    discard_padding = next(
        (
            _integer_or_none(value.get("discard_padding"))
            for value in final_side
            if value.get("side_data_type") == "Skip Samples"
        ),
        0,
    )
    if pts is None or duration is None or discard_padding is None:
        final_sample: int | None = None
    else:
        final_sample = pts + duration - discard_padding
    return {
        "packet_after_program_boundary": final_sample is None or final_sample > expected_samples,
        "packet_final_sample_exclusive": final_sample,
        "priming_skip_samples": priming,
    }


def _rectangle_union_area(rectangles: Sequence[Rectangle]) -> int:
    if not rectangles:
        return 0
    x_edges = sorted(
        {edge for rectangle in rectangles for edge in (rectangle.x, rectangle.x + rectangle.width)}
    )
    area = 0
    for left, right in pairwise(x_edges):
        if right <= left:
            continue
        intervals = sorted(
            (rectangle.y, rectangle.y + rectangle.height)
            for rectangle in rectangles
            if rectangle.width > 0
            and rectangle.height > 0
            and rectangle.x < right
            and rectangle.x + rectangle.width > left
        )
        covered = 0
        if intervals:
            start, end = intervals[0]
            for interval_start, interval_end in intervals[1:]:
                if interval_start > end:
                    covered += end - start
                    start, end = interval_start, interval_end
                else:
                    end = max(end, interval_end)
            covered += end - start
        area += (right - left) * covered
    return area


def _json_clone(value: Mapping[str, object]) -> dict[str, object]:
    return cast(dict[str, object], json.loads(json.dumps(value)))


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _render_state_hashes(
    manifest: Mapping[str, object] | None,
) -> dict[tuple[str, str], str]:
    if manifest is None:
        return {}
    timing = _mapping(manifest.get("project_timing"))
    records_value = timing.get("states")
    records = cast(list[object], records_value) if isinstance(records_value, list) else []
    hashes: dict[tuple[str, str], str] = {}
    for value in records:
        record = _mapping(value)
        scene_id = record.get("scene_id")
        state_id = record.get("state_id")
        digest = record.get("source_sha256")
        if isinstance(scene_id, str) and isinstance(state_id, str) and _is_sha256(digest):
            hashes[(scene_id, state_id)] = cast(str, digest)
    return hashes


def _semantic_hash_evidence(manifest: Mapping[str, object]) -> dict[str, object]:
    inputs = _mapping(manifest.get("inputs"))
    captions = _mapping(inputs.get("captions_srt"))
    outputs = _mapping(manifest.get("outputs"))
    return {
        "caption_sha256": captions.get("sha256"),
        "outputs": {
            name: {
                "decoded_video_sha256": _mapping(record).get("decoded_video_sha256"),
                "decoded_pcm_sha256": _mapping(record).get("decoded_pcm_sha256"),
            }
            for name, record in sorted(outputs.items())
        },
    }


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _file_sha256_or_none(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _run_reproduction_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
    operation: str,
) -> str:
    result = run_capture_process(
        argv,
        cwd=cwd,
        environment=environment,
        timeout=timeout,
        operation=operation,
    )
    if result.returncode != 0:
        raise RunnerCaptureError(f"{operation}: exited {result.returncode}")
    return result.stdout.strip()


def _read_json_mapping(path: Path, label: str) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _actual_reproduction_semantics(checkout: Path, ffmpeg: Path) -> dict[str, object]:
    final = checkout / "dist" / "video" / "final"
    captions = checkout / "media" / "repository-explainer" / "captions.srt"
    return {
        "caption_sha256": _file_sha256_or_none(captions),
        "outputs": {
            variant: _decoded_candidate_hashes(
                final / filename,
                ffmpeg=str(ffmpeg),
                total_samples=6_480_000,
            )
            for variant, filename in (
                ("narrated", "agent-pseudocode-explainer-narrated.mp4"),
                ("speaker", "agent-pseudocode-explainer-speaker.mp4"),
            )
        },
    }


def _offline_render_main(argv: Sequence[str]) -> int:
    if os.environ.get("VIDEO_PIPELINE_OFFLINE_REPRODUCTION") != "1" or any(
        key in os.environ for key in ("OPENAI_API_KEY", "BAO_TOKEN", "BAO_ROLE_ID", "BAO_SECRET_ID")
    ):
        raise VerificationError("offline render requires the cleared network-denied runner")
    arguments = tuple(argv)
    if (
        len(arguments) != 4
        or arguments[0] != "--offline-render"
        or arguments[2] != "--selected-wav-sha256"
        or not _is_sha256(arguments[3])
    ):
        raise VerificationError("offline render arguments do not match the fixed contract")
    render_production(
        Path.cwd(),
        selected_wav=Path(arguments[1]),
        selected_wav_sha256=arguments[3],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_offline_render_main(sys.argv[1:]))
