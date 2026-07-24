"""Generate one bounded full-script narration take through OpenAI Speech.

Only the locked narration text and delivery instructions cross the provider
boundary. Provider responses are split and measured locally, while a durable
series ledger enforces the three-request cap even across process restarts.
Credential values and provider denial bodies never enter logs or evidence.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from itertools import pairwise
from pathlib import Path
from typing import Literal, Protocol, cast

from .captions import NarrationPackage, load_narration, validate_take_durations
from .models import ProjectManifest

MODEL = "gpt-4o-mini-tts"
VOICE = "marin"
RESPONSE_FORMAT = "wav"
SPEECH_PATH = "/v1/audio/speech"
API_BASE_URL = "https://api.openai.com"
MAX_INPUT_CHARACTERS = 4096
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
MAX_TAKES = 3
SPEND_CAP_USD = Decimal("1.00")
PROJECTED_COST_PER_TAKE_USD = Decimal("0.045")
MIN_BOUNDARY_GAP_SECONDS = Decimal("0.05")
LOCK_WAIT_SECONDS = 5.0
TRANSIENT_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
PERMISSION_DENIAL_STATUSES = frozenset({401, 403})
PROJECT_KEY_DENIAL_CLASSES = ("Files", "Fine-tuning", "Assistants")
PERMISSION_PROBE_CONTRACT = (
    ("Files", "GET", "/v1/files"),
    ("Fine-tuning", "GET", "/v1/fine_tuning/jobs"),
    ("Assistants", "GET", "/v1/assistants"),
)
PRODUCTION_EVIDENCE_SCHEMA_VERSION = 1
TAKE_MANIFEST_SCHEMA_VERSION = 1


class SpeechError(RuntimeError):
    """Base class for safe, caller-actionable narration failures."""


class SpeechTerminalError(SpeechError):
    """Raised for a request or provider response that retry cannot repair."""


class ProviderUnavailableError(SpeechError):
    """Raise the explicit AW-004 blocked outcome after bounded transient attempts."""


class TakeLimitError(SpeechError):
    """Raised before a fourth provider request for an unchanged take series."""


class SpendLimitError(SpeechError):
    """Raised before a take series could exceed the approved USD 1 ceiling."""


class TakeRejectedError(SpeechTerminalError):
    """Raised when a complete provider take is malformed or exceeds a scene budget."""


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """One provider-bound HTTP request at the injected transport boundary."""

    method: str
    path: str
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """One complete HTTP response returned by a speech transport."""

    status: int
    headers: Mapping[str, str]
    body: bytes


class SpeechTransport(Protocol):
    """Send one complete provider request without retaining authorization data."""

    def send(self, request: HttpRequest, *, timeout_seconds: float) -> HttpResponse: ...


@dataclass(frozen=True, slots=True)
class SpeechPolicy:
    """Fixed request, retry, and aggregate spend limits for one production series."""

    projected_cost_per_take_usd: Decimal = PROJECTED_COST_PER_TAKE_USD
    spend_cap_usd: Decimal = SPEND_CAP_USD
    max_takes: int = MAX_TAKES
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_takes != MAX_TAKES:
            raise ValueError("speech policy must retain the global three-take cap")
        if self.projected_cost_per_take_usd <= 0:
            raise ValueError("projected_cost_per_take_usd must be positive")
        if self.spend_cap_usd <= 0 or self.spend_cap_usd > SPEND_CAP_USD:
            raise ValueError("spend_cap_usd must be positive and no greater than USD 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


DEFAULT_SPEECH_POLICY = SpeechPolicy()


@dataclass(frozen=True, slots=True)
class PermissionProbe:
    """One project-key resource mapped to its exact dashboard permission name."""

    request_class: str
    method: str
    path: str


@dataclass(frozen=True, slots=True)
class NarrationResult:
    """Accepted full narration and locally extracted WAV segment paths."""

    series_hash: str
    take_count: int
    selected_wav: Path
    segment_wavs: tuple[Path, ...]
    measured_segment_frames: Mapping[str, int]
    manifest_path: Path


@dataclass(frozen=True, slots=True)
class _DecodedWav:
    channels: int
    sample_width: int
    sample_rate: int
    frame_count: int
    frames: bytes


@dataclass(frozen=True, slots=True)
class _SilenceGap:
    start: int
    end: int


class UrllibTransport:
    """Use standard-library urllib for production HTTPS and explicit local tests."""

    def __init__(
        self, *, base_url: str = API_BASE_URL, allow_insecure_for_tests: bool = False
    ) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "https" and not (
            allow_insecure_for_tests
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError("Speech transport requires HTTPS outside an explicit loopback test")
        if parsed.query or parsed.fragment or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) origin")
        self._base_url = base_url.rstrip("/")

    def send(self, request: HttpRequest, *, timeout_seconds: float) -> HttpResponse:
        """Send one bounded request and return status, headers, and body in full."""
        if not request.path.startswith("/v1/"):
            raise ValueError("provider request path must stay below /v1/")
        provider_request = urllib.request.Request(
            f"{self._base_url}{request.path}",
            data=request.body or None,
            headers=dict(request.headers),
            method=request.method,
        )
        try:
            with urllib.request.urlopen(provider_request, timeout=timeout_seconds) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                headers = {key.lower(): value for key, value in response.headers.items()}
                return HttpResponse(status=response.status, headers=headers, body=body)
        except urllib.error.HTTPError as exc:
            # The caller classifies status only. The body is returned in memory so
            # urllib can close the response, but is never logged or persisted.
            with exc:
                body = exc.read(MAX_RESPONSE_BYTES + 1)
                headers = {key.lower(): value for key, value in exc.headers.items()}
            return HttpResponse(status=exc.code, headers=headers, body=body)
        except urllib.error.URLError as exc:
            raise OSError("Speech provider transport unavailable") from exc


def build_locked_script(package: NarrationPackage) -> str:
    """Return every approved narration line in source order as one provider input."""
    normalized_instructions = package.instructions.casefold()
    if not all(
        required_word in normalized_instructions
        for required_word in ("calm", "precise", "technical")
    ):
        raise SpeechTerminalError(
            "delivery instructions must require a calm, precise technical delivery"
        )
    script = "\n\n".join(segment.narration for segment in package.segments)
    if not script or len(script) > MAX_INPUT_CHARACTERS:
        raise SpeechTerminalError(
            f"locked narration must contain 1-{MAX_INPUT_CHARACTERS} characters"
        )
    return script


def dry_run_summary(
    narration_path: Path,
    project: ProjectManifest,
    *,
    policy: SpeechPolicy = DEFAULT_SPEECH_POLICY,
) -> str:
    """Return the deliberately minimal, secret-free preflight JSON line."""
    package = load_narration(narration_path, project)
    build_locked_script(package)
    projected_bound = _projected_series_bound(policy)
    _enforce_spend_bound(projected_bound, policy)
    return json.dumps(
        {
            "model": package.model,
            "projected_bound_usd": _money(projected_bound),
            "segment_count": len(package.segments),
            "voice": package.voice,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def generate_narration(
    *,
    narration_path: Path,
    project: ProjectManifest,
    output_dir: Path,
    api_key: str,
    transport: SpeechTransport,
    manifest_path: Path | None = None,
    policy: SpeechPolicy = DEFAULT_SPEECH_POLICY,
    sleep: Callable[[float], None] = time.sleep,
) -> NarrationResult:
    """Serialize one unchanged-series reservation and its bounded provider call."""
    package = load_narration(narration_path, project)
    script = build_locked_script(package)
    series_hash = _series_hash(script, package)
    canonical_manifest = _canonical_take_manifest(project, series_hash)
    if manifest_path is not None and manifest_path != canonical_manifest:
        raise SpeechTerminalError(
            "caller-supplied manifest_path must equal the canonical narration state path"
        )
    with _exclusive_file_lock(canonical_manifest):
        return _generate_narration_locked(
            narration_path=narration_path,
            project=project,
            output_dir=output_dir,
            manifest_path=canonical_manifest,
            api_key=api_key,
            transport=transport,
            package=package,
            script=script,
            series_hash=series_hash,
            policy=policy,
            sleep=sleep,
        )


def _generate_narration_locked(
    *,
    narration_path: Path,
    project: ProjectManifest,
    output_dir: Path,
    manifest_path: Path,
    api_key: str,
    transport: SpeechTransport,
    package: NarrationPackage,
    script: str,
    series_hash: str,
    policy: SpeechPolicy = DEFAULT_SPEECH_POLICY,
    sleep: Callable[[float], None] = time.sleep,
) -> NarrationResult:
    """Generate and validate at most three provider takes for one locked input series.

    Only transport unavailability and HTTP 429/5xx responses retry. Authentication,
    permission, policy, malformed WAV, fixed-budget, and spend failures return
    immediately. Every attempted provider request consumes the unchanged-series cap.
    """
    _validate_api_key(api_key)
    projected_bound = _projected_series_bound(policy)
    _enforce_spend_bound(projected_bound, policy)
    ledger = _load_take_ledger(manifest_path)
    take_count = _series_take_count(ledger, series_hash)
    request = _speech_request(script, package, api_key)

    while take_count < policy.max_takes:
        take_count += 1
        _update_ledger(
            ledger,
            series_hash=series_hash,
            take_count=take_count,
            package=package,
            policy=policy,
            status="requested",
            failure_class=None,
            outcome=None,
        )
        _atomic_write_json(manifest_path, ledger)
        try:
            response = transport.send(request, timeout_seconds=policy.timeout_seconds)
        except (ConnectionError, TimeoutError, OSError) as exc:
            _record_failure(
                ledger,
                manifest_path,
                series_hash=series_hash,
                take_count=take_count,
                package=package,
                policy=policy,
                failure_class="provider-unavailable",
                transient=True,
            )
            if take_count >= policy.max_takes:
                raise ProviderUnavailableError(
                    "AW-004: blocked — Speech provider unavailable after three bounded takes"
                ) from exc
            sleep(float(2 ** (take_count - 1)))
            continue

        if response.status in TRANSIENT_HTTP_STATUSES:
            _record_failure(
                ledger,
                manifest_path,
                series_hash=series_hash,
                take_count=take_count,
                package=package,
                policy=policy,
                failure_class="provider-unavailable",
                transient=True,
            )
            if take_count >= policy.max_takes:
                raise ProviderUnavailableError(
                    "AW-004: blocked — Speech provider unavailable after three bounded takes"
                )
            sleep(float(2 ** (take_count - 1)))
            continue
        if response.status != 200:
            failure_class, message = _terminal_http_failure(response.status)
            _record_failure(
                ledger,
                manifest_path,
                series_hash=series_hash,
                take_count=take_count,
                package=package,
                policy=policy,
                failure_class=failure_class,
                transient=False,
            )
            raise SpeechTerminalError(message)

        try:
            decoded = _decode_wav(response.body)
            segment_ranges = _split_speech_ranges(decoded, package)
            measured_frames = _measure_segment_frames(
                decoded, segment_ranges, package, project.media.fps
            )
            validate_take_durations(narration_path, project, measured_frames)
        except SpeechTerminalError:
            _record_failure(
                ledger,
                manifest_path,
                series_hash=series_hash,
                take_count=take_count,
                package=package,
                policy=policy,
                failure_class="malformed-audio",
                transient=False,
            )
            raise
        except ValueError as exc:
            _record_failure(
                ledger,
                manifest_path,
                series_hash=series_hash,
                take_count=take_count,
                package=package,
                policy=policy,
                failure_class="fixed-budget-overrun",
                transient=False,
            )
            raise TakeRejectedError(str(exc)) from exc

        selected_wav, segment_wavs = _write_accepted_wavs(
            output_dir, response.body, decoded, segment_ranges, package
        )
        _update_ledger(
            ledger,
            series_hash=series_hash,
            take_count=take_count,
            package=package,
            policy=policy,
            status="accepted",
            failure_class=None,
            outcome="accepted",
            measured_frames=measured_frames,
            selected_wav=selected_wav,
        )
        _atomic_write_json(manifest_path, ledger)
        return NarrationResult(
            series_hash=series_hash,
            take_count=take_count,
            selected_wav=selected_wav,
            segment_wavs=segment_wavs,
            measured_segment_frames=measured_frames,
            manifest_path=manifest_path,
        )

    raise TakeLimitError("unchanged narration series reached the global three-take cap")


def run_permission_smoke(
    *,
    narration_path: Path,
    project: ProjectManifest,
    evidence_path: Path,
    api_key: str,
    transport: SpeechTransport,
    checked_date: str,
    probes: Sequence[PermissionProbe],
    mode: Literal["permission-smoke"],
    timeout_seconds: float = 60.0,
) -> dict[str, object]:
    """Serialize and durably reserve the one permitted permission-smoke attempt."""
    if mode != "permission-smoke":
        raise SpeechTerminalError("permission smoke may only run in permission-smoke mode")
    _validate_checked_date(checked_date)
    _validate_api_key(api_key)
    _validate_permission_probe_set(probes)
    package = load_narration(narration_path, project)
    script = build_locked_script(package)
    series_hash = _series_hash(script, package)
    smoke_state_path = _canonical_smoke_state(project, series_hash)
    with _exclusive_file_lock(smoke_state_path):
        return _run_permission_smoke_locked(
            narration_path=narration_path,
            project=project,
            evidence_path=evidence_path,
            api_key=api_key,
            transport=transport,
            checked_date=checked_date,
            probes=probes,
            mode=mode,
            timeout_seconds=timeout_seconds,
            package=package,
            script=script,
            series_hash=series_hash,
            smoke_state_path=smoke_state_path,
        )


def _run_permission_smoke_locked(
    *,
    narration_path: Path,
    project: ProjectManifest,
    evidence_path: Path,
    api_key: str,
    transport: SpeechTransport,
    checked_date: str,
    probes: Sequence[PermissionProbe],
    mode: Literal["permission-smoke"],
    timeout_seconds: float = 60.0,
    package: NarrationPackage,
    script: str,
    series_hash: str,
    smoke_state_path: Path,
) -> dict[str, object]:
    """Run the one-time Speech success and denied-resource permission check.

    The canonical state files retain only request class, date, status, and
    pass/fail. Response bodies and authorization headers stay outside the
    durable record.
    """
    smoke_state = _load_smoke_state(smoke_state_path)
    if smoke_state.get("status") != "not-run":
        raise SpeechTerminalError("permission smoke was already attempted and is one-time")
    _atomic_write_json(
        smoke_state_path,
        {
            "schema_version": 1,
            "series_hash": series_hash,
            "status": "running",
            "checked_date": checked_date,
        },
    )

    existing = _load_production_evidence(evidence_path)
    baseline = _base_production_evidence(checked_date)
    evidence = dict(existing)
    for key, value in baseline.items():
        evidence[key] = value
    denial_records: list[dict[str, object]] = []
    speech_record = _smoke_record("Speech", checked_date, "reserved", False)
    _persist_smoke_evidence(
        evidence_path,
        evidence,
        denial_records,
        speech_record=speech_record,
        status="running",
    )

    manifest_path = _canonical_take_manifest(project, series_hash)
    with _exclusive_file_lock(manifest_path):
        ledger = _load_take_ledger(manifest_path)
        take_count = _series_take_count(ledger, series_hash)
        if take_count >= MAX_TAKES:
            _finish_smoke_state(smoke_state_path, "fail")
            raise TakeLimitError("unchanged narration series reached the global three-take cap")
        take_count += 1
        _update_ledger(
            ledger,
            series_hash=series_hash,
            take_count=take_count,
            package=package,
            policy=DEFAULT_SPEECH_POLICY,
            status="permission-smoke-requested",
            failure_class=None,
            outcome=None,
        )
        _atomic_write_json(manifest_path, ledger)
        try:
            speech_response = _send_smoke_request(
                transport,
                _speech_request(script, package, api_key),
                timeout_seconds=timeout_seconds,
            )
        except ProviderUnavailableError:
            speech_record = _smoke_record("Speech", checked_date, "transport-unavailable", False)
            _record_failure(
                ledger,
                manifest_path,
                series_hash=series_hash,
                take_count=take_count,
                package=package,
                policy=DEFAULT_SPEECH_POLICY,
                failure_class="provider-unavailable",
                transient=False,
            )
            _persist_smoke_evidence(
                evidence_path,
                evidence,
                denial_records,
                speech_record=speech_record,
                status="fail",
            )
            _finish_smoke_state(smoke_state_path, "fail")
            raise

        speech_passed = speech_response.status == 200
        if speech_passed:
            try:
                _decode_wav(speech_response.body)
            except SpeechTerminalError:
                speech_passed = False
        speech_record = _smoke_record("Speech", checked_date, speech_response.status, speech_passed)
        _update_ledger(
            ledger,
            series_hash=series_hash,
            take_count=take_count,
            package=package,
            policy=DEFAULT_SPEECH_POLICY,
            status="permission-smoke-complete" if speech_passed else "rejected",
            failure_class=None if speech_passed else "permission-smoke-speech",
            outcome="permission-smoke" if speech_passed else "rejected",
        )
        _atomic_write_json(manifest_path, ledger)
    _persist_smoke_evidence(
        evidence_path,
        evidence,
        denial_records,
        speech_record=speech_record,
        status="running",
    )

    for probe in probes:
        try:
            response = _send_smoke_request(
                transport,
                HttpRequest(
                    method=probe.method,
                    path=probe.path,
                    headers=_permission_probe_headers(probe, api_key),
                    body=b"",
                ),
                timeout_seconds=timeout_seconds,
            )
        except ProviderUnavailableError:
            denial_records.append(
                _denial_probe_record(
                    probe.request_class,
                    checked_date,
                    "transport-unavailable",
                    False,
                )
            )
            _persist_smoke_evidence(
                evidence_path,
                evidence,
                denial_records,
                speech_record=speech_record,
                status="fail",
            )
            _finish_smoke_state(smoke_state_path, "fail")
            raise
        denial_records.append(
            _denial_probe_record(
                probe.request_class,
                checked_date,
                response.status,
                response.status in PERMISSION_DENIAL_STATUSES,
            )
        )
        _persist_smoke_evidence(
            evidence_path,
            evidence,
            denial_records,
            speech_record=speech_record,
            status="running",
        )

    passed = speech_passed and all(cast(bool, record["pass"]) for record in denial_records)
    status = "pass" if passed else "fail"
    _persist_smoke_evidence(
        evidence_path,
        evidence,
        denial_records,
        speech_record=speech_record,
        status=status,
    )
    _finish_smoke_state(smoke_state_path, status)
    if not passed:
        raise SpeechTerminalError("permission smoke failed; production Speech remains blocked")
    return cast(dict[str, object], evidence["project_key_denial_probes"])


def _speech_request(script: str, package: NarrationPackage, api_key: str) -> HttpRequest:
    payload = json.dumps(
        {
            "input": script,
            "instructions": package.instructions,
            "model": MODEL,
            "response_format": RESPONSE_FORMAT,
            "voice": VOICE,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return HttpRequest(
        method="POST",
        path=SPEECH_PATH,
        headers={
            **_authorization_headers(api_key),
            "Accept": "audio/wav",
            "Content-Type": "application/json",
        },
        body=payload,
    )


def _authorization_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _validate_api_key(api_key: str) -> None:
    if (
        not api_key
        or api_key.strip() != api_key
        or any(character.isspace() for character in api_key)
    ):
        raise SpeechTerminalError("OPENAI_API_KEY is missing or malformed")


def _series_hash(script: str, package: NarrationPackage) -> str:
    canonical = json.dumps(
        {
            "instructions": package.instructions,
            "model": package.model,
            "script": script,
            "voice": package.voice,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _canonical_take_manifest(project: ProjectManifest, series_hash: str) -> Path:
    """Return the repository-owned ledger path for one immutable request series."""
    return project.output.root / "work" / "narration-series" / f"{series_hash}.json"


def _canonical_smoke_state(project: ProjectManifest, series_hash: str) -> Path:
    """Return the repository-owned one-shot permission-smoke state path."""
    return project.output.root / "work" / "permission-smoke" / f"{series_hash}.json"


def _projected_series_bound(policy: SpeechPolicy) -> Decimal:
    return (policy.projected_cost_per_take_usd * policy.max_takes).quantize(
        Decimal("0.01"), rounding=ROUND_CEILING
    )


def _generated_spend_bound(policy: SpeechPolicy, take_count: int) -> Decimal:
    return (policy.projected_cost_per_take_usd * take_count).quantize(
        Decimal("0.01"), rounding=ROUND_CEILING
    )


def _enforce_spend_bound(projected_bound: Decimal, policy: SpeechPolicy) -> None:
    if projected_bound > policy.spend_cap_usd:
        raise SpendLimitError("projected unchanged-series spend exceeds the approved USD 1 bound")


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _load_take_ledger(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "schema_version": TAKE_MANIFEST_SCHEMA_VERSION,
            "series_counts": {},
        }
    try:
        decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpeechTerminalError("take manifest could not be read as valid JSON") from exc
    if not isinstance(decoded, dict):
        raise SpeechTerminalError("take manifest must be a JSON object")
    ledger = cast(dict[str, object], decoded)
    if ledger.get("schema_version") != TAKE_MANIFEST_SCHEMA_VERSION:
        raise SpeechTerminalError("take manifest schema_version is unsupported")
    if not isinstance(ledger.get("series_counts"), dict):
        raise SpeechTerminalError("take manifest series_counts must be an object")
    return ledger


def _series_take_count(ledger: dict[str, object], series_hash: str) -> int:
    counts = cast(dict[str, object], ledger["series_counts"])
    value = counts.get(series_hash, 0)
    if type(value) is not int or not 0 <= value <= MAX_TAKES:
        raise SpeechTerminalError("take manifest contains an invalid series count")
    return value


def _update_ledger(
    ledger: dict[str, object],
    *,
    series_hash: str,
    take_count: int,
    package: NarrationPackage,
    policy: SpeechPolicy,
    status: str,
    failure_class: str | None,
    outcome: str | None,
    measured_frames: Mapping[str, int] | None = None,
    selected_wav: Path | None = None,
) -> None:
    counts = cast(dict[str, object], ledger["series_counts"])
    counts[series_hash] = take_count
    ledger.update(
        {
            "series_hash": series_hash,
            "model": package.model,
            "voice": package.voice,
            "response_format": RESPONSE_FORMAT,
            "endpoint": f"POST {SPEECH_PATH}",
            "segment_count": len(package.segments),
            "take_count": take_count,
            "max_takes": policy.max_takes,
            "projected_series_spend_bound_usd": _money(_projected_series_bound(policy)),
            "generated_spend_bound_usd": _money(_generated_spend_bound(policy, take_count)),
            "approved_spend_cap_usd": _money(policy.spend_cap_usd),
            "spend_bound_status": "pass",
            "billing_evidence": "non-itemized bounds only",
            "status": status,
        }
    )
    for optional_key in ("failure_class", "outcome", "measured_segment_frames", "selected_wav"):
        ledger.pop(optional_key, None)
    if failure_class is not None:
        ledger["failure_class"] = failure_class
    if outcome is not None:
        ledger["outcome"] = outcome
    if measured_frames is not None:
        ledger["measured_segment_frames"] = dict(measured_frames)
    if selected_wav is not None:
        ledger["selected_wav"] = str(selected_wav)


def _record_failure(
    ledger: dict[str, object],
    manifest_path: Path,
    *,
    series_hash: str,
    take_count: int,
    package: NarrationPackage,
    policy: SpeechPolicy,
    failure_class: str,
    transient: bool,
) -> None:
    outcome = "AW-004: blocked" if transient and take_count >= policy.max_takes else "rejected"
    _update_ledger(
        ledger,
        series_hash=series_hash,
        take_count=take_count,
        package=package,
        policy=policy,
        status="blocked" if outcome == "AW-004: blocked" else "rejected",
        failure_class=failure_class,
        outcome=outcome,
    )
    _atomic_write_json(manifest_path, ledger)


def _terminal_http_failure(status: int) -> tuple[str, str]:
    if status == 401:
        return "authentication", "Speech authentication failed; retry is not permitted"
    if status == 403:
        return "permission", "Speech permission or policy denied; retry is not permitted"
    return "request-policy", f"Speech request failed with terminal HTTP status {status}"


def _decode_wav(content: bytes) -> _DecodedWav:
    if len(content) > MAX_RESPONSE_BYTES:
        raise TakeRejectedError("Speech response exceeded the bounded WAV size")
    try:
        with wave.open(io.BytesIO(content), "rb") as stream:
            channels = stream.getnchannels()
            sample_width = stream.getsampwidth()
            sample_rate = stream.getframerate()
            frame_count = stream.getnframes()
            compression = stream.getcomptype()
            frames = stream.readframes(frame_count)
    except (EOFError, wave.Error) as exc:
        raise TakeRejectedError("Speech response is not a well-formed WAV") from exc
    if channels not in {1, 2}:
        raise TakeRejectedError("Speech WAV must contain one or two channels")
    if sample_width not in {1, 2, 3, 4}:
        raise TakeRejectedError("Speech WAV sample width is unsupported")
    if not 8_000 <= sample_rate <= 192_000:
        raise TakeRejectedError("Speech WAV sample rate is outside the accepted range")
    if frame_count <= 0 or compression != "NONE":
        raise TakeRejectedError("Speech WAV must contain uncompressed PCM audio")
    expected_bytes = frame_count * channels * sample_width
    if len(frames) != expected_bytes:
        raise TakeRejectedError("Speech WAV contains truncated PCM frames")
    return _DecodedWav(
        channels=channels,
        sample_width=sample_width,
        sample_rate=sample_rate,
        frame_count=frame_count,
        frames=frames,
    )


def _split_speech_ranges(
    decoded: _DecodedWav, package: NarrationPackage
) -> tuple[tuple[int, int], ...]:
    peak = max(_frame_magnitude(decoded, index) for index in range(decoded.frame_count))
    threshold = max(1, peak // 100)
    minimum_gap = max(
        1,
        int(
            (Decimal(decoded.sample_rate) * MIN_BOUNDARY_GAP_SECONDS).to_integral_value(
                rounding=ROUND_CEILING
            )
        ),
    )
    gaps: list[_SilenceGap] = []
    first_active: int | None = None
    last_active: int | None = None
    gap_start: int | None = None
    for frame_index in range(decoded.frame_count):
        active = _frame_magnitude(decoded, frame_index) > threshold
        if active:
            if first_active is None:
                first_active = frame_index
            if (
                gap_start is not None
                and last_active is not None
                and frame_index - gap_start >= minimum_gap
            ):
                gaps.append(_SilenceGap(start=gap_start, end=frame_index))
            gap_start = None
            last_active = frame_index
            continue
        if first_active is not None and gap_start is None:
            gap_start = frame_index
    if first_active is None or last_active is None:
        raise TakeRejectedError("Speech WAV contains no measurable narration")

    boundary_count = len(package.segments) - 1
    if len(gaps) < boundary_count:
        raise TakeRejectedError(
            "Speech WAV does not contain enough measurable paragraph boundaries"
        )
    selected = _select_aligned_gaps(
        gaps,
        package,
        first_active=first_active,
        last_active=last_active,
    )
    ranges = [(first_active, selected[0].start)]
    ranges.extend((previous.end, following.start) for previous, following in pairwise(selected))
    ranges.append((selected[-1].end, last_active + 1))
    if any(end <= start for start, end in ranges):
        raise TakeRejectedError("Speech WAV paragraph boundaries produce an empty segment")
    return tuple(ranges)


def _frame_magnitude(decoded: _DecodedWav, frame_index: int) -> int:
    bytes_per_frame = decoded.channels * decoded.sample_width
    offset = frame_index * bytes_per_frame
    return max(
        _sample_magnitude(
            decoded.frames[
                offset + channel * decoded.sample_width : offset
                + (channel + 1) * decoded.sample_width
            ],
            decoded.sample_width,
        )
        for channel in range(decoded.channels)
    )


def _select_aligned_gaps(
    gaps: Sequence[_SilenceGap],
    package: NarrationPackage,
    *,
    first_active: int,
    last_active: int,
) -> tuple[_SilenceGap, ...]:
    weights = tuple(max(1, len(segment.narration.split())) for segment in package.segments)
    total_weight = sum(weights)
    active_span = last_active + 1 - first_active
    cumulative = 0
    expected_positions: list[float] = []
    for weight in weights[:-1]:
        cumulative += weight
        expected_positions.append(first_active + active_span * cumulative / total_weight)

    previous_states: list[tuple[float, tuple[int, ...]] | None] = [
        (
            abs((gap.start + gap.end) / 2 - expected_positions[0]),
            (index,),
        )
        for index, gap in enumerate(gaps)
    ]
    for boundary_index, expected in enumerate(expected_positions[1:], start=1):
        states: list[tuple[float, tuple[int, ...]] | None] = [None] * len(gaps)
        best_previous: tuple[float, tuple[int, ...]] | None = None
        for gap_index, gap in enumerate(gaps):
            if gap_index > 0:
                candidate = previous_states[gap_index - 1]
                if candidate is not None and (
                    best_previous is None or candidate[0] < best_previous[0]
                ):
                    best_previous = candidate
            remaining_boundaries = len(expected_positions) - boundary_index - 1
            if best_previous is None or len(gaps) - gap_index - 1 < remaining_boundaries:
                continue
            position_cost = abs((gap.start + gap.end) / 2 - expected)
            states[gap_index] = (
                best_previous[0] + position_cost,
                (*best_previous[1], gap_index),
            )
        previous_states = states

    best = min(
        (state for state in previous_states if state is not None),
        key=lambda state: state[0],
        default=None,
    )
    if best is None:
        raise TakeRejectedError("Speech WAV paragraph boundaries could not be aligned")
    return tuple(gaps[index] for index in best[1])


def _sample_magnitude(sample: bytes, sample_width: int) -> int:
    if sample_width == 1:
        return abs(sample[0] - 128)
    return abs(int.from_bytes(sample, "little", signed=True))


def _measure_segment_frames(
    decoded: _DecodedWav,
    ranges: tuple[tuple[int, int], ...],
    package: NarrationPackage,
    fps: int,
) -> dict[str, int]:
    return {
        segment.scene_id: _ceiling_division((end - start) * fps, decoded.sample_rate)
        for segment, (start, end) in zip(package.segments, ranges, strict=True)
    }


def _write_accepted_wavs(
    output_dir: Path,
    full_wav: bytes,
    decoded: _DecodedWav,
    ranges: tuple[tuple[int, int], ...],
    package: NarrationPackage,
) -> tuple[Path, tuple[Path, ...]]:
    selected_wav = output_dir / "selected-narration.wav"
    segment_payloads = tuple(_encode_segment_wav(decoded, start, end) for start, end in ranges)
    segment_wavs = tuple(
        output_dir / "segments" / f"{index:02}-{segment.scene_id}.wav"
        for index, segment in enumerate(package.segments, start=1)
    )
    _atomic_write_bytes(selected_wav, full_wav)
    for path, payload in zip(segment_wavs, segment_payloads, strict=True):
        _atomic_write_bytes(path, payload)
    return selected_wav, segment_wavs


def _encode_segment_wav(decoded: _DecodedWav, start: int, end: int) -> bytes:
    bytes_per_frame = decoded.channels * decoded.sample_width
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(decoded.channels)
        stream.setsampwidth(decoded.sample_width)
        stream.setframerate(decoded.sample_rate)
        stream.writeframes(decoded.frames[start * bytes_per_frame : end * bytes_per_frame])
    return output.getvalue()


def _ceiling_division(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def _send_smoke_request(
    transport: SpeechTransport, request: HttpRequest, *, timeout_seconds: float
) -> HttpResponse:
    try:
        return transport.send(request, timeout_seconds=timeout_seconds)
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise ProviderUnavailableError(
            "AW-004: blocked — permission smoke provider unavailable"
        ) from exc


def _validate_permission_probe_set(probes: Sequence[PermissionProbe]) -> None:
    actual = tuple((probe.request_class, probe.method, probe.path) for probe in probes)
    if actual != PERMISSION_PROBE_CONTRACT:
        raise SpeechTerminalError(
            "permission smoke must test every separately denied resource class "
            "with its exact method and path"
        )


def _permission_probe_headers(probe: PermissionProbe, api_key: str) -> Mapping[str, str]:
    headers = _authorization_headers(api_key)
    if probe.request_class == "Assistants":
        headers.update(
            {
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2",
            }
        )
    return headers


def _smoke_record(
    request_class: str, checked_date: str, status: int | str, passed: bool
) -> dict[str, object]:
    return {
        "request_class": request_class,
        "date": checked_date,
        "status": status,
        "pass": passed,
    }


def _denial_probe_record(
    dashboard_permission: str,
    checked_date: str,
    status: int | str,
    passed: bool,
) -> dict[str, object]:
    return {
        "dashboard_permission": dashboard_permission,
        "date": checked_date,
        "status": status,
        "pass": passed,
    }


def _persist_smoke_evidence(
    evidence_path: Path,
    evidence: dict[str, object],
    records: list[dict[str, object]],
    *,
    speech_record: dict[str, object],
    status: str,
) -> None:
    evidence["speech_smoke"] = {
        "mode": "permission-smoke",
        "status": status,
        "request": speech_record,
    }
    evidence["project_key_denial_probes"] = {
        "status": status,
        "requests": records,
    }
    _atomic_write_json(evidence_path, evidence)


def _load_smoke_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"schema_version": 1, "status": "not-run"}
    try:
        decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpeechTerminalError("permission smoke state could not be read as valid JSON") from exc
    if not isinstance(decoded, dict):
        raise SpeechTerminalError("permission smoke state is invalid")
    state = cast(dict[str, object], decoded)
    if state.get("schema_version") != 1:
        raise SpeechTerminalError("permission smoke state is invalid")
    return state


def _finish_smoke_state(path: Path, status: str) -> None:
    state = _load_smoke_state(path)
    state["status"] = status
    _atomic_write_json(path, state)


def _validate_checked_date(checked_date: str) -> None:
    try:
        time.strptime(checked_date, "%Y-%m-%d")
    except ValueError as exc:
        raise SpeechTerminalError("permission evidence date must be YYYY-MM-DD") from exc


def _load_production_evidence(path: Path) -> dict[str, object]:
    if not path.exists():
        return _base_production_evidence("2026-07-23")
    try:
        decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SpeechTerminalError("production evidence could not be read as valid JSON") from exc
    if not isinstance(decoded, dict):
        raise SpeechTerminalError("production evidence must be a JSON object")
    evidence = cast(dict[str, object], decoded)
    denial_probes = evidence.get("project_key_denial_probes")
    if denial_probes is not None and not isinstance(denial_probes, dict):
        raise SpeechTerminalError("production evidence project_key_denial_probes must be an object")
    return evidence


def _base_production_evidence(checked_date: str) -> dict[str, object]:
    return {
        "schema_version": PRODUCTION_EVIDENCE_SCHEMA_VERSION,
        "provider_contract": {
            "checked_date": checked_date,
            "documentation": (
                "https://developers.openai.com/api/reference/resources/audio/"
                "subresources/speech/methods/create"
            ),
            "pricing_documentation": "https://developers.openai.com/api/docs/pricing",
            "method": "POST",
            "path": SPEECH_PATH,
            "model": MODEL,
            "voice": VOICE,
            "response_format": RESPONSE_FORMAT,
            "maximum_input_characters": MAX_INPUT_CHARACTERS,
        },
        "dashboard_bundle": {
            "checked_date": checked_date,
            "source": "OpenAI project API key dashboard",
            "scope": "Restricted",
            "speech_permitting_bundle": "provider-bundled model capabilities: Request",
            "independently_denied_bundled_model_capabilities": False,
            "project_key_probe_targets": list(PROJECT_KEY_DENIAL_CLASSES),
            "dashboard_only_denials": ["Management", "Administration"],
            "containment": "Production code permits only POST /v1/audio/speech.",
        },
        "credential_reference": {
            "environment_variable": "OPENAI_API_KEY",
            "openbao_path": "secret/api-keys/ai/openai-tts",
        },
        "speech_smoke": {
            "mode": "permission-smoke",
            "status": "not-run",
            "request": None,
        },
        "project_key_denial_probes": {
            "status": "not-run",
            "requests": [],
        },
        "spend_evidence": {
            "approved_cap_usd": _money(SPEND_CAP_USD),
            "recording": "non-itemized projected and generated bounds only",
        },
    }


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    serialized = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write_bytes(path, serialized)


@contextmanager
def _exclusive_file_lock(path: Path) -> Generator[None]:
    """Serialize a provider series without weakening the cap after a crash.

    The atomic directory reservation is cross-process and cross-platform. A stale
    lock blocks new provider calls until reviewed instead of risking an extra paid
    call after uncertain state.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while True:
        try:
            lock_path.mkdir()
            break
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise SpeechTerminalError(
                    "exclusive narration state lock is unavailable; no provider call was made"
                ) from exc
            time.sleep(0.05)
    try:
        yield
    finally:
        lock_path.rmdir()


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        with suppress(FileNotFoundError):
            temporary_path.unlink()
        raise
