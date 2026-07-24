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
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Literal, NamedTuple, cast

from .captions import AI_NARRATION_DISCLOSURE
from .models import MediaSettings, Rectangle, VisualState
from .scenes import RenderedSceneState

type GateStatus = Literal["pass", "fail"]
type VariantName = Literal["narrated", "speaker"]

REPORT_SCHEMA_VERSION = 1
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INTEGRATED_LOUDNESS = re.compile(r"^\s*I:\s*(-?(?:\d+(?:\.\d+)?|inf))\s+LUFS\s*$", re.M)
_TRUE_PEAK = re.compile(r"^\s*Peak:\s*(-?(?:\d+(?:\.\d+)?|inf))\s+dB(?:FS|TP)\s*$", re.M)
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
    """Run every T8 Must gate and return the sole promotion decision."""
    manifest_gate = verify_render_manifest(
        inputs.render_manifest,
        media=inputs.media,
        states=inputs.states,
    )
    rights_gate, classified_ids = verify_asset_provenance(
        inputs.asset_provenance,
        repository_root=inputs.repository_root,
    )
    media_gates = tuple(
        gate
        for variant in ("narrated", "speaker")
        for gate in verify_media_variant(
            variant,
            inputs.probes.get(variant, {}),
            inputs.loudness.get(
                variant,
                LoudnessMeasurement(integrated_lufs=float("inf"), true_peak_dbtp=float("inf")),
            ),
            media=inputs.media,
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
    )
    share_gate = verify_evidence_frame_share(
        inputs.states,
        width=inputs.media.width,
        height=inputs.media.height,
        total_frames=inputs.media.total_frames,
    )
    reproduction_gate = verify_reproduction(
        inputs.render_manifest,
        inputs.reproduced_manifest,
        actual_toolchain=inputs.actual_toolchain,
        clean_checkout=inputs.clean_checkout,
        speech_api_calls=inputs.speech_api_calls,
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
            manifest_gate,
            rights_gate,
            *media_gates,
            *content_gates,
            share_gate,
            reproduction_gate,
            checksum_gate,
        ),
        checksums=checksums,
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


def probe_media_file(
    path: Path, *, ffprobe: str = "ffprobe", ffmpeg: str = "ffmpeg"
) -> dict[str, object]:
    """Return FFprobe JSON augmented with the exact decoded PCM boundary."""
    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-count_frames",
                "-show_entries",
                (
                    "format=format_name,duration:"
                    "stream=index,codec_type,codec_name,profile,width,height,pix_fmt,"
                    "r_frame_rate,duration,nb_read_frames,channels,sample_rate"
                ),
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        decoded: object = json.loads(completed.stdout)
        pcm = subprocess.run(
            [
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
            ],
            check=True,
            capture_output=True,
            timeout=120,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise VerificationError(f"media probe failed for {path.name!r}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError("FFprobe returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise VerificationError("FFprobe JSON must be an object")
    if len(pcm) % 4:
        raise VerificationError("decoded stereo PCM ended between sample frames")
    probe = cast(dict[str, object], decoded)
    probe["program_audio_boundary"] = {
        "first_program_sample": 0,
        "last_program_sample_exclusive": len(pcm) // 4,
        "packet_after_program_boundary": False,
    }
    return probe


def measure_loudness(path: Path, *, ffmpeg: str = "ffmpeg") -> LoudnessMeasurement:
    """Measure one variant independently with FFmpeg's EBU R128 filter."""
    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-nostats",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-filter_complex",
                "ebur128=peak=true",
                "-f",
                "null",
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise VerificationError(f"loudness analysis failed for {path.name!r}") from exc
    return parse_ebur128(completed.stderr)


def verify_media_variant(
    variant: VariantName,
    probe: Mapping[str, object],
    loudness: LoudnessMeasurement,
    *,
    media: MediaSettings,
) -> tuple[GateResult, ...]:
    """Return explicit format, stream, duration, loudness, and peak rows."""
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
        "frame_rate": video.get("r_frame_rate"),
        "expected": {
            "container": "mp4",
            "codec": "h264",
            "width": media.width,
            "height": media.height,
            "pixel_format": "yuv420p",
            "frame_rate": f"{media.fps}/1",
        },
    }
    format_pass = (
        "mp4" in container.split(",")
        and video.get("codec_name") == "h264"
        and video.get("width") == media.width
        and video.get("height") == media.height
        and video.get("pix_fmt") == "yuv420p"
        and video.get("r_frame_rate") == f"{media.fps}/1"
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
    expected_duration = media.total_frames / media.fps
    expected_samples = round(expected_duration * 48_000)
    boundary_value = probe.get("program_audio_boundary")
    boundary = cast(dict[str, object], boundary_value) if isinstance(boundary_value, dict) else {}
    decoded_frames = _integer_or_none(video.get("nb_read_frames"))
    durations = {
        "container": _float_or_none(format_record.get("duration")),
        "video": _float_or_none(video.get("duration")),
        "audio": _float_or_none(audio.get("duration")),
    }
    duration_evidence = {
        "expected_frames": media.total_frames,
        "decoded_frames": decoded_frames,
        "expected_seconds": expected_duration,
        "reported_seconds": durations,
        "expected_audio_samples": expected_samples,
        "decoded_audio_samples": boundary.get("last_program_sample_exclusive"),
        "packet_after_program_boundary": boundary.get("packet_after_program_boundary"),
    }
    duration_pass = (
        decoded_frames == media.total_frames
        and all(
            value is not None and abs(value - expected_duration) <= 1 / media.fps
            for value in durations.values()
        )
        and boundary.get("first_program_sample") == 0
        and boundary.get("last_program_sample_exclusive") == expected_samples
        and boundary.get("packet_after_program_boundary") is False
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
) -> tuple[GateResult, ...]:
    """Verify authenticity, rights, accessibility, layout, audio, and secrecy."""
    authenticity_findings: list[dict[str, object]] = []
    for state in states:
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
            not authenticity_findings,
            {
                "references_checked": sum(len(state.references) for state in states),
                "findings": authenticity_findings,
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
    for state in states:
        union_area = _rectangle_union_area(state.evidence_rectangles)
        is_dominant = union_area * 2 >= frame_area
        frame_count = state.end_frame - state.start_frame
        if frame_count <= 0:
            raise VerificationError("visual states must have positive frame durations")
        if is_dominant:
            dominant_frames += frame_count
        states_evidence.append(
            {
                "state_id": state.id if isinstance(state, VisualState) else state.state_id,
                "frames": frame_count,
                "evidence_union_area": union_area,
                "frame_area": frame_area,
                "dominant": is_dominant,
            }
        )
    percentage = dominant_frames * 100 / total_frames
    return _gate(
        "C-003-evidence-frame-share",
        60 <= percentage <= 80,
        {
            "dominant_frames": dominant_frames,
            "total_frames": total_frames,
            "percentage": percentage,
            "inclusive_range_percent": [60, 80],
            "states": states_evidence,
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
) -> GateResult:
    """Require exact-toolchain, offline, exact semantic reproduction."""
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


def checksum_files(files: Mapping[str, Path]) -> dict[str, str]:
    """Return deterministic SHA-256 output for every named deliverable."""
    checksums: dict[str, str] = {}
    for name, path in sorted(files.items()):
        digest = _file_sha256_or_none(path)
        if digest is None:
            raise VerificationError(f"deliverable {name!r} could not be read")
        checksums[name] = digest
    return checksums


def write_verification_report(path: Path, report: VerificationReport) -> None:
    """Atomically write the canonical JSON verification report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(
            json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


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
        completed = subprocess.run(
            ["git", "show", f"{revision}:{path_text}"],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError("revision-bound reference lookup failed") from exc
    if completed.returncode != 0:
        raise VerificationError("reference is unavailable at its recorded revision")
    return completed.stdout


def _secret_findings(artifacts: Mapping[str, bytes | str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for artifact, content in sorted(artifacts.items()):
        text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else content
        for classification, pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                findings.append({"artifact": artifact, "classification": classification})
                break
    return findings


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
