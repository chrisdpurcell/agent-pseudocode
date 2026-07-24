"""Run the basic media and delivery checks required for the quick demo.

Production expectations are fixed here so a short diagnostic fixture cannot be
mistaken for an accepted 135-second delivery. Verification reads only the named
delivery files, tracked explainer text, and explicitly listed evidence text; it
never reads environment values or analyzes media content beyond FFprobe and EBU
R128.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Literal, cast

from .captions import AI_NARRATION_DISCLOSURE

DELIVERY_FILES: dict[str, str] = {
    "narrated": "agent-pseudocode-explainer-narrated.mp4",
    "speaker": "agent-pseudocode-explainer-speaker.mp4",
    "captions": "agent-pseudocode-explainer-captions.srt",
    "delivery": "delivery.json",
}
REPORT_NAME = "verification-report.json"
_TEXT_SUFFIXES = frozenset(
    {
        ".apseudo",
        ".json",
        ".jsonc",
        ".md",
        ".mmd",
        ".py",
        ".srt",
        ".svg",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
_CREDENTIAL_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    re.compile(
        r"""(?ix)
        \b(?:authorization|api[_-]?key|password|private[_-]?key|secret|token)\b
        \s*["']?\s*[:=]\s*["']?(?:bearer\s+)?
        [A-Za-z0-9+/=_-]{8,}
        """
    ),
)


class VerificationError(RuntimeError):
    """Report an invalid invocation or an unavailable verification tool."""


@dataclass(frozen=True, slots=True)
class VariantAudioExpectation:
    """Expected integrated loudness and maximum true peak for one variant."""

    integrated_lufs: float
    tolerance_lu: float
    maximum_true_peak_dbtp: float


@dataclass(frozen=True, slots=True)
class VerificationExpectations:
    """Media expectations for production or an explicitly diagnostic fixture."""

    mode: Literal["production", "diagnostic"]
    width: int
    height: int
    fps: int
    frames: int
    duration_seconds: float
    narrated: VariantAudioExpectation
    speaker: VariantAudioExpectation

    @classmethod
    def production(cls) -> VerificationExpectations:
        """Return the immutable quick-demo production contract."""
        return cls(
            mode="production",
            width=1920,
            height=1080,
            fps=30,
            frames=4050,
            duration_seconds=135.0,
            narrated=VariantAudioExpectation(-16.0, 1.0, -1.0),
            speaker=VariantAudioExpectation(-28.0, 2.0, -6.0),
        )

    @classmethod
    def diagnostic(
        cls,
        *,
        width: int,
        height: int,
        fps: int,
        frames: int,
        duration_seconds: float,
        narrated_lufs: float,
        narrated_lufs_tolerance: float,
        narrated_peak_dbtp: float,
        speaker_lufs: float,
        speaker_lufs_tolerance: float,
        speaker_peak_dbtp: float,
    ) -> VerificationExpectations:
        """Return visibly non-production expectations for a short local fixture."""
        return cls(
            mode="diagnostic",
            width=width,
            height=height,
            fps=fps,
            frames=frames,
            duration_seconds=duration_seconds,
            narrated=VariantAudioExpectation(
                narrated_lufs,
                narrated_lufs_tolerance,
                narrated_peak_dbtp,
            ),
            speaker=VariantAudioExpectation(
                speaker_lufs,
                speaker_lufs_tolerance,
                speaker_peak_dbtp,
            ),
        )

    def validate(self) -> None:
        """Reject altered production values and nonsensical diagnostic values."""
        if self.mode == "production" and self != self.production():
            raise VerificationError("production expectations must use the exact quick-demo values")
        if min(self.width, self.height, self.fps, self.frames) <= 0:
            raise VerificationError(
                "verification dimensions, rate, and frame count must be positive"
            )
        if self.duration_seconds <= 0:
            raise VerificationError("verification duration must be positive")
        if self.narrated.tolerance_lu < 0 or self.speaker.tolerance_lu < 0:
            raise VerificationError("loudness tolerances must be nonnegative")


@dataclass(frozen=True, slots=True)
class MediaFacts:
    """Direct FFprobe facts for one MP4."""

    container: str
    duration_seconds: float
    video_codec: str
    width: int
    height: int
    progressive: bool
    fps: float
    frames: int
    audio_codec: str
    audio_channels: int
    audio_layout: str


@dataclass(frozen=True, slots=True)
class LoudnessFacts:
    """Integrated EBU R128 loudness and true peak."""

    integrated_lufs: float
    true_peak_dbtp: float


@dataclass(frozen=True, slots=True)
class VerificationCheck:
    """One concise, actionable verification result."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Simple JSON-serializable result for one delivery directory."""

    mode: Literal["production", "diagnostic"]
    passed: bool
    production_accepted: bool
    checks: tuple[VerificationCheck, ...]
    sha256: Mapping[str, str]
    report_path: Path


def parse_probe(payload: Mapping[str, object]) -> MediaFacts:
    """Parse one FFprobe JSON document with exactly one video and one audio stream."""
    format_record = _mapping(payload.get("format"), "ffprobe.format")
    streams = _sequence(payload.get("streams"), "ffprobe.streams")
    stream_records = [
        _mapping(stream, f"ffprobe.streams[{index}]") for index, stream in enumerate(streams)
    ]
    video_streams = [stream for stream in stream_records if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in stream_records if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1 or len(audio_streams) != 1:
        raise VerificationError("FFprobe must report exactly one video and one audio stream")
    video = video_streams[0]
    audio = audio_streams[0]
    format_name = _string(format_record.get("format_name"), "ffprobe.format.format_name")
    try:
        fps = float(Fraction(_string(video.get("avg_frame_rate"), "video.avg_frame_rate")))
        duration = float(_string(format_record.get("duration"), "ffprobe.format.duration"))
    except (ValueError, ZeroDivisionError) as exc:
        raise VerificationError("FFprobe reported an invalid frame rate or duration") from exc
    return MediaFacts(
        container="mp4" if "mp4" in format_name.split(",") else format_name,
        duration_seconds=duration,
        video_codec=_string(video.get("codec_name"), "video.codec_name"),
        width=_integer(video.get("width"), "video.width"),
        height=_integer(video.get("height"), "video.height"),
        progressive=video.get("field_order") == "progressive",
        fps=fps,
        frames=_integer_string(video.get("nb_read_frames"), "video.nb_read_frames"),
        audio_codec=_string(audio.get("codec_name"), "audio.codec_name"),
        audio_channels=_integer(audio.get("channels"), "audio.channels"),
        audio_layout=_string(audio.get("channel_layout"), "audio.channel_layout"),
    )


def parse_loudness(stderr: str) -> LoudnessFacts:
    """Parse the final integrated-loudness and true-peak values from EBU R128 output."""
    integrated = re.findall(r"\bI:\s*(-?\d+(?:\.\d+)?)\s+LUFS\b", stderr)
    peaks = re.findall(r"\bPeak:\s*(-?\d+(?:\.\d+)?)\s+dBFS\b", stderr)
    if not integrated or not peaks:
        raise VerificationError("FFmpeg EBU R128 summary is missing loudness or true peak")
    return LoudnessFacts(
        integrated_lufs=float(integrated[-1]),
        true_peak_dbtp=float(peaks[-1]),
    )


def verify_delivery(
    *,
    repository_root: Path,
    delivery_root: Path,
    expectations: VerificationExpectations | None = None,
    credential_scan_paths: Sequence[Path] | None = None,
) -> VerificationReport:
    """Verify a quick-demo delivery and write its JSON report.

    Passing diagnostic expectations proves only that the verifier works against
    a short fixture. Only the exact production contract can set
    ``production_accepted``.
    """
    selected = expectations or VerificationExpectations.production()
    selected.validate()
    root = repository_root.resolve()
    delivery = delivery_root.resolve()
    if not delivery.is_dir():
        raise VerificationError(f"delivery directory does not exist: {delivery}")
    destination = delivery / REPORT_NAME
    checks: list[VerificationCheck] = []
    paths = {role: delivery / filename for role, filename in DELIVERY_FILES.items()}

    for role, path in paths.items():
        checks.append(
            VerificationCheck(
                name=f"{role}_file",
                passed=path.is_file() and path.stat().st_size > 0,
                detail="present and nonempty"
                if path.is_file() and path.stat().st_size > 0
                else "missing or empty",
            )
        )

    delivery_payload = _read_delivery(paths["delivery"], checks)
    checks.append(_check_delivery_metadata(delivery_payload))

    for variant in ("narrated", "speaker"):
        media_path = paths[variant]
        if not media_path.is_file():
            continue
        try:
            facts = _probe_media(media_path)
            checks.append(check_media(variant, facts, selected))
        except VerificationError as exc:
            checks.append(VerificationCheck(f"{variant}_media", False, str(exc)))
        try:
            loudness = _measure_loudness(media_path)
            audio_expected = selected.narrated if variant == "narrated" else selected.speaker
            checks.append(check_loudness(variant, loudness, audio_expected))
        except VerificationError as exc:
            checks.append(VerificationCheck(f"{variant}_loudness", False, str(exc)))

    scan_paths = _tracked_media_text_paths(root) + _declared_evidence_paths(root, delivery_payload)
    if credential_scan_paths is not None:
        scan_paths += tuple(path.resolve() for path in credential_scan_paths)
    if paths["delivery"].is_file():
        scan_paths += (paths["delivery"],)
    checks.append(_check_credentials(root, scan_paths))

    hashes = {
        path.name: _sha256(path)
        for path in paths.values()
        if path.is_file() and path.stat().st_size > 0
    }
    checks.append(
        VerificationCheck(
            "sha256_inventory",
            set(hashes) == set(DELIVERY_FILES.values()),
            f"{len(hashes)}/{len(DELIVERY_FILES)} required files hashed",
        )
    )
    passed = all(check.passed for check in checks)
    report = VerificationReport(
        mode=selected.mode,
        passed=passed,
        production_accepted=passed and selected.mode == "production",
        checks=tuple(checks),
        sha256=hashes,
        report_path=destination,
    )
    _write_report(report)
    return report


def _probe_media(path: Path) -> MediaFacts:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise VerificationError("FFprobe is unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise VerificationError("FFprobe timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise VerificationError("FFprobe rejected the media file") from exc
    try:
        decoded: object = cast(object, json.loads(completed.stdout))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("FFprobe returned invalid JSON") from exc
    return parse_probe(_mapping(decoded, "ffprobe"))


def _measure_loudness(path: Path) -> LoudnessFacts:
    try:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-nostdin",
                "-i",
                str(path),
                "-filter_complex",
                "ebur128=peak=true",
                "-f",
                "null",
                "-",
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=180,
        )
    except FileNotFoundError as exc:
        raise VerificationError("FFmpeg is unavailable for EBU R128 analysis") from exc
    except subprocess.TimeoutExpired as exc:
        raise VerificationError("FFmpeg EBU R128 analysis timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise VerificationError("FFmpeg could not analyze media loudness") from exc
    return parse_loudness(completed.stderr.decode("utf-8", errors="replace"))


def check_media(
    variant: str,
    facts: MediaFacts,
    expected: VerificationExpectations,
) -> VerificationCheck:
    failures: list[str] = []
    if facts.container != "mp4":
        failures.append("container")
    if facts.video_codec != "h264":
        failures.append("video codec")
    if (facts.width, facts.height) != (expected.width, expected.height):
        failures.append("dimensions")
    if not facts.progressive:
        failures.append("progressive scan")
    if abs(facts.fps - expected.fps) > 0.001:
        failures.append("frame rate")
    if facts.frames != expected.frames:
        failures.append("frame count")
    if abs(facts.duration_seconds - expected.duration_seconds) > (1 / expected.fps) + 1e-6:
        failures.append("duration")
    if facts.audio_codec != "aac":
        failures.append("audio codec")
    if facts.audio_channels != 2 or facts.audio_layout != "stereo":
        failures.append("stereo audio")
    return VerificationCheck(
        f"{variant}_media",
        not failures,
        "media contract passed" if not failures else "failed: " + ", ".join(failures),
    )


def check_loudness(
    variant: str,
    facts: LoudnessFacts,
    expected: VariantAudioExpectation,
) -> VerificationCheck:
    loudness_ok = abs(facts.integrated_lufs - expected.integrated_lufs) <= expected.tolerance_lu
    peak_ok = facts.true_peak_dbtp <= expected.maximum_true_peak_dbtp
    return VerificationCheck(
        f"{variant}_loudness",
        loudness_ok and peak_ok,
        (
            f"{facts.integrated_lufs:.1f} LUFS, {facts.true_peak_dbtp:.1f} dBTP"
            if loudness_ok and peak_ok
            else "loudness or true peak is outside the required range"
        ),
    )


def _read_delivery(path: Path, checks: list[VerificationCheck]) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        decoded: object = cast(object, json.loads(path.read_text(encoding="utf-8")))
        return _mapping(decoded, "delivery.json")
    except OSError, UnicodeDecodeError, json.JSONDecodeError, VerificationError:
        checks.append(VerificationCheck("delivery_json", False, "invalid UTF-8 JSON object"))
        return {}


def _check_delivery_metadata(payload: Mapping[str, object]) -> VerificationCheck:
    expected_inventory = {
        "narrated": DELIVERY_FILES["narrated"],
        "speaker": DELIVERY_FILES["speaker"],
        "captions": DELIVERY_FILES["captions"],
    }
    inventory = payload.get("files")
    captioned = payload.get("narration_captioned_variants")
    actual_inventory = (
        _mapping(cast(object, inventory), "delivery.files") if isinstance(inventory, dict) else {}
    )
    passed = (
        payload.get("ai_narration_disclosure") == AI_NARRATION_DISCLOSURE
        and actual_inventory == expected_inventory
        and captioned == ["narrated"]
    )
    return VerificationCheck(
        "delivery_metadata",
        passed,
        "disclosure and narrated-only caption inventory passed"
        if passed
        else "delivery.json must disclose narration and assign captions only to narrated",
    )


def _tracked_media_text_paths(repository_root: Path) -> tuple[Path, ...]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--", "media/repository-explainer"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise VerificationError("Git could not enumerate tracked explainer text") from exc
    paths = (repository_root / raw.decode("utf-8") for raw in completed.stdout.split(b"\0") if raw)
    return tuple(path.resolve() for path in paths if path.suffix.casefold() in _TEXT_SUFFIXES)


def _declared_evidence_paths(
    repository_root: Path,
    delivery: Mapping[str, object],
) -> tuple[Path, ...]:
    value = delivery.get("evidence_text_files", [])
    if not isinstance(value, list):
        raise VerificationError("delivery.json evidence_text_files must be a string array")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise VerificationError("delivery.json evidence_text_files must be a string array")
    resolved: list[Path] = []
    for raw_item in items:
        if not isinstance(raw_item, str):
            raise VerificationError("delivery.json evidence_text_files must be a string array")
        item = raw_item
        candidate = Path(item)
        if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
            raise VerificationError("delivery.json evidence text path must be repository-relative")
        path = (repository_root / candidate).resolve()
        if not path.is_relative_to(repository_root):
            raise VerificationError("delivery.json evidence text path escapes the repository")
        resolved.append(path)
    return tuple(resolved)


def _check_credentials(repository_root: Path, paths: Sequence[Path]) -> VerificationCheck:
    findings: list[str] = []
    for path in dict.fromkeys(paths):
        if not path.is_file():
            findings.append(_display_path(repository_root, path))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            findings.append(_display_path(repository_root, path))
            continue
        if any(pattern.search(text) is not None for pattern in _CREDENTIAL_PATTERNS):
            findings.append(_display_path(repository_root, path))
    return VerificationCheck(
        "credential_scan",
        not findings,
        "targeted text scan passed"
        if not findings
        else "credential-like content or unreadable text: " + ", ".join(sorted(findings)),
    )


def _write_report(report: VerificationReport) -> None:
    payload = {
        "mode": report.mode,
        "passed": report.passed,
        "production_accepted": report.production_accepted,
        "checks": [
            {"name": check.name, "passed": check.passed, "detail": check.detail}
            for check in report.checks
        ],
        "sha256": dict(sorted(report.sha256.items())),
    }
    report.report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(repository_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repository_root).as_posix()
    except ValueError:
        return path.name


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise VerificationError(f"{field}: expected an object")
    return cast(dict[str, object], value)


def _sequence(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise VerificationError(f"{field}: expected an array")
    return cast(list[object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{field}: expected a nonempty string")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VerificationError(f"{field}: expected an integer")
    return value


def _integer_string(value: object, field: str) -> int:
    text = _string(value, field)
    try:
        return int(text)
    except ValueError as exc:
        raise VerificationError(f"{field}: expected an integer string") from exc
