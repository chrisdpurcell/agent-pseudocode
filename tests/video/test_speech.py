"""Contracts for bounded full-script OpenAI Speech generation."""

from __future__ import annotations

import io
import json
import threading
import time
import wave
from collections import deque
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar, cast

import pytest

from video_pipeline.captions import load_narration
from video_pipeline.manifest import load_project
from video_pipeline.models import ProjectManifest
from video_pipeline.speech import (
    HttpRequest,
    HttpResponse,
    PermissionProbe,
    ProviderUnavailableError,
    SpeechError,
    SpeechPolicy,
    SpeechTerminalError,
    SpendLimitError,
    TakeLimitError,
    TakeRejectedError,
    UrllibTransport,
    build_locked_script,
    dry_run_summary,
    generate_narration,
    run_permission_smoke,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
MEDIA_ROOT = REPOSITORY_ROOT / "media" / "repository-explainer"
PROJECT_PATH = MEDIA_ROOT / "project.json"
NARRATION_PATH = MEDIA_ROOT / "narration.json"
SECRET_SHAPED_VALUE = "".join(("s", "k", "-", "local-contract-secret"))
DENIAL_SECRET = "".join(("s", "k", "-", "denial-body-secret"))
PERMISSION_PROBES = (
    PermissionProbe("files", "GET", "/v1/files"),
    PermissionProbe("fine-tuning", "GET", "/v1/fine_tuning/jobs"),
    PermissionProbe("assistants", "GET", "/v1/assistants"),
    PermissionProbe("management", "GET", "/v1/organization/projects"),
    PermissionProbe("administration", "GET", "/v1/organization/admin_api_keys"),
)


@dataclass
class _ServerState:
    wav: bytes
    requests: list[tuple[str, str, dict[str, str], bytes]] = field(default_factory=list)


class _SpeechHandler(BaseHTTPRequestHandler):
    state: ClassVar[_ServerState]

    def do_POST(self) -> None:
        self._handle()

    def do_GET(self) -> None:
        self._handle()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        headers = {key.lower(): value for key, value in self.headers.items()}
        self.state.requests.append((self.command, self.path, headers, body))
        if self.command == "POST" and self.path == "/v1/audio/speech":
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(self.state.wav)))
            self.end_headers()
            self.wfile.write(self.state.wav)
            return
        denial = json.dumps(
            {
                "error": "denied body must never be retained",
                "token": DENIAL_SECRET,
            }
        ).encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(denial)))
        self.end_headers()
        self.wfile.write(denial)


@contextmanager
def _local_speech_server(wav_bytes: bytes) -> Generator[tuple[str, _ServerState]]:
    state = _ServerState(wav=wav_bytes)
    handler = type("SpeechHandler", (_SpeechHandler,), {"state": state})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@dataclass
class _ScriptedTransport:
    responses: deque[HttpResponse | OSError]
    requests: list[HttpRequest] = field(default_factory=list)

    def send(self, request: HttpRequest, *, timeout_seconds: float) -> HttpResponse:
        self.requests.append(request)
        response = self.responses.popleft()
        if isinstance(response, OSError):
            raise response
        return response


@dataclass
class _SlowRejectingTransport:
    response: HttpResponse
    request_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, request: HttpRequest, *, timeout_seconds: float) -> HttpResponse:
        with self._lock:
            self.request_count += 1
        time.sleep(0.05)
        return self.response


def _project() -> ProjectManifest:
    return load_project(PROJECT_PATH, repository_root=REPOSITORY_ROOT)


def _wav(segment_frames: Sequence[int], *, fps: int = 30, sample_rate: int = 12_000) -> bytes:
    samples_per_video_frame = sample_rate // fps
    tone = (12_000).to_bytes(2, "little", signed=True)
    silence = (0).to_bytes(2, "little", signed=True)
    audio = bytearray()
    for index, duration_frames in enumerate(segment_frames):
        audio.extend(tone * (duration_frames * samples_per_video_frame))
        if index + 1 < len(segment_frames):
            audio.extend(silence * (10 * samples_per_video_frame))
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(bytes(audio))
    return output.getvalue()


def _wav_with_realistic_pauses(*, sample_rate: int = 12_000, fps: int = 30) -> bytes:
    samples_per_video_frame = sample_rate // fps
    tone = (120).to_bytes(2, "little", signed=True)
    silence = (0).to_bytes(2, "little", signed=True)
    # The first scene contains a long punctuation pause; paragraph gaps vary
    # below and above 250 ms, as a real full-script take can.
    runs = (
        (tone, 12),
        (silence, 12),
        (tone, 18),
        (silence, 4),
        (tone, 40),
        (silence, 6),
        (tone, 50),
        (silence, 3),
        (tone, 60),
        (silence, 8),
        (tone, 70),
        (silence, 5),
        (tone, 80),
    )
    audio = b"".join(sample * (frames * samples_per_video_frame) for sample, frames in runs)
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(audio)
    return output.getvalue()


def _speech_response(wav_bytes: bytes, *, status: int = 200) -> HttpResponse:
    return HttpResponse(status=status, headers={"content-type": "audio/wav"}, body=wav_bytes)


def test_tc_t6_001__local_http_contract_and_permission_smoke__record_narrow_evidence(
    tmp_path: Path,
) -> None:
    project = _project()
    package = load_narration(NARRATION_PATH, project)
    wav_bytes = _wav([30, 40, 50, 60, 70, 80])
    evidence_path = tmp_path / "production-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "permission_smoke": {"status": "not-run"},
                "future_stage_evidence": {"preserve": True},
            }
        ),
        encoding="utf-8",
    )
    take_manifest = tmp_path / "work" / "take-series.json"
    output_dir = tmp_path / "output"

    with _local_speech_server(wav_bytes) as (base_url, server_state):
        transport = UrllibTransport(base_url=base_url, allow_insecure_for_tests=True)
        result = generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=output_dir,
            manifest_path=take_manifest,
            api_key=SECRET_SHAPED_VALUE,
            transport=transport,
            sleep=lambda _: None,
        )
        smoke = run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=project,
            evidence_path=evidence_path,
            api_key=SECRET_SHAPED_VALUE,
            transport=transport,
            checked_date="2026-07-23",
            probes=PERMISSION_PROBES,
            mode="permission-smoke",
        )

    speech_requests = [
        request for request in server_state.requests if request[0:2] == ("POST", "/v1/audio/speech")
    ]
    assert len(speech_requests) == 2
    production_payload = json.loads(speech_requests[0][3])
    assert production_payload == {
        "input": build_locked_script(package),
        "instructions": package.instructions,
        "model": "gpt-4o-mini-tts",
        "response_format": "wav",
        "voice": "marin",
    }
    assert speech_requests[0][2]["authorization"] == f"Bearer {SECRET_SHAPED_VALUE}"
    assert result.selected_wav.read_bytes() == wav_bytes
    assert len(result.segment_wavs) == len(package.segments)
    assert smoke["status"] == "pass"
    smoke_requests = cast(list[dict[str, object]], smoke["requests"])
    assert [entry["request_class"] for entry in smoke_requests] == [
        "speech",
        "files",
        "fine-tuning",
        "assistants",
        "management",
        "administration",
    ]
    assert all(
        set(entry) == {"request_class", "date", "status", "pass"} for entry in smoke_requests
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    permission_bundle = cast(dict[str, object], evidence["permission_bundle"])
    assert evidence["future_stage_evidence"] == {"preserve": True}
    assert permission_bundle["scope"] == "Restricted"
    assert permission_bundle["speech_permitting_bundle"] == (
        "provider-bundled model capabilities: Request"
    )
    assert permission_bundle["separately_denied"] == [
        "management",
        "files",
        "fine-tuning",
        "assistants",
        "administration",
    ]
    with pytest.raises(SpeechTerminalError, match="only run in permission-smoke mode"):
        run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=project,
            evidence_path=evidence_path,
            api_key="unused",
            transport=_ScriptedTransport(deque()),
            checked_date="2026-07-23",
            probes=(),
            mode="narrate",  # type: ignore[arg-type] - runtime rejection is the contract under test
        )

    incomplete_smoke = _ScriptedTransport(deque((_speech_response(wav_bytes),)))
    with pytest.raises(SpeechTerminalError, match="every separately denied resource class"):
        run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=project,
            evidence_path=tmp_path / "incomplete-evidence.json",
            api_key="test-key",
            transport=incomplete_smoke,
            checked_date="2026-07-23",
            probes=(),
            mode="permission-smoke",
        )

    mislabeled_probes = (
        PermissionProbe("files", "GET", "/v1/models"),
        *PERMISSION_PROBES[1:],
    )
    with pytest.raises(SpeechTerminalError, match="exact method and path"):
        run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=project,
            evidence_path=tmp_path / "mislabeled-evidence.json",
            api_key="test-key",
            transport=_ScriptedTransport(deque()),
            checked_date="2026-07-23",
            probes=mislabeled_probes,
            mode="permission-smoke",
        )

    failed_smoke_path = tmp_path / "failed-evidence.json"
    failed_smoke_transport = _ScriptedTransport(
        deque(
            (
                HttpResponse(status=403, headers={}, body=b"denied"),
                *(HttpResponse(status=403, headers={}, body=b"denied") for _ in range(5)),
            )
        )
    )
    with pytest.raises(SpeechTerminalError, match="permission smoke failed"):
        run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=project,
            evidence_path=failed_smoke_path,
            api_key="test-key",
            transport=failed_smoke_transport,
            checked_date="2026-07-23",
            probes=PERMISSION_PROBES,
            mode="permission-smoke",
        )
    requests_after_failure = len(failed_smoke_transport.requests)
    with pytest.raises(SpeechTerminalError, match="already attempted"):
        run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=project,
            evidence_path=failed_smoke_path,
            api_key="test-key",
            transport=failed_smoke_transport,
            checked_date="2026-07-23",
            probes=PERMISSION_PROBES,
            mode="permission-smoke",
        )
    assert len(failed_smoke_transport.requests) == requests_after_failure

    unlocked_payload = json.loads(NARRATION_PATH.read_text(encoding="utf-8"))
    unlocked_delivery = cast(dict[str, object], unlocked_payload["delivery"])
    unlocked_delivery["instructions"] = "Use an excited sales pitch."
    unlocked_path = tmp_path / "unlocked-narration.json"
    unlocked_path.write_text(json.dumps(unlocked_payload), encoding="utf-8")
    with pytest.raises(SpeechTerminalError, match="calm, precise technical delivery"):
        generate_narration(
            narration_path=unlocked_path,
            project=project,
            output_dir=tmp_path / "unlocked-output",
            manifest_path=tmp_path / "unlocked-work" / "take-series.json",
            api_key="test-key",
            transport=_ScriptedTransport(deque()),
            sleep=lambda _: None,
        )


def test_tc_t6_002__full_wav_guards__bound_takes_retries_and_spend(tmp_path: Path) -> None:
    project = _project()
    accepted_wav = _wav([30, 40, 50, 60, 70, 80])
    transient_then_ok = _ScriptedTransport(
        deque(
            (
                HttpResponse(status=503, headers={}, body=b"provider detail"),
                _speech_response(accepted_wav),
            )
        )
    )
    result = generate_narration(
        narration_path=NARRATION_PATH,
        project=project,
        output_dir=tmp_path / "retry-output",
        manifest_path=tmp_path / "retry-work" / "take-series.json",
        api_key="test-key",
        transport=transient_then_ok,
        sleep=lambda _: None,
    )
    assert result.take_count == 2
    assert len(transient_then_ok.requests) == 2
    assert result.measured_segment_frames == {
        "problem": 30,
        "visible-workflow": 40,
        "caught-defect": 50,
        "shared-policy": 60,
        "guarded-execution": 70,
        "promise": 80,
    }

    realistic_result = generate_narration(
        narration_path=NARRATION_PATH,
        project=project,
        output_dir=tmp_path / "realistic-output",
        manifest_path=tmp_path / "realistic-work" / "take-series.json",
        api_key="test-key",
        transport=_ScriptedTransport(deque((_speech_response(_wav_with_realistic_pauses()),))),
        sleep=lambda _: None,
    )
    assert len(realistic_result.segment_wavs) == 6

    terminal = _ScriptedTransport(
        deque(
            (
                HttpResponse(
                    status=401,
                    headers={},
                    body=SECRET_SHAPED_VALUE.encode("utf-8"),
                ),
            )
        )
    )
    with pytest.raises(SpeechTerminalError, match="authentication"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=tmp_path / "terminal-output",
            manifest_path=tmp_path / "terminal-work" / "take-series.json",
            api_key="test-key",
            transport=terminal,
            sleep=lambda _: None,
        )
    assert len(terminal.requests) == 1

    unavailable = _ScriptedTransport(
        deque(
            (
                OSError("offline"),
                HttpResponse(status=503, headers={}, body=b"retry"),
                HttpResponse(status=429, headers={}, body=b"retry"),
            )
        )
    )
    unavailable_manifest = tmp_path / "unavailable-work" / "take-series.json"
    with pytest.raises(ProviderUnavailableError, match=r"AW-004.*blocked"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=tmp_path / "unavailable-output",
            manifest_path=unavailable_manifest,
            api_key="test-key",
            transport=unavailable,
            sleep=lambda _: None,
        )
    assert json.loads(unavailable_manifest.read_text(encoding="utf-8"))["outcome"] == (
        "AW-004: blocked"
    )

    package = load_narration(NARRATION_PATH, project)
    first_budget = package.segments[0].end_frame - package.segments[0].start_frame
    overlong_wav = _wav([first_budget + 1, 40, 50, 60, 70, 80])
    cap_transport = _ScriptedTransport(deque(_speech_response(overlong_wav) for _ in range(3)))
    cap_manifest = tmp_path / "cap-work" / "take-series.json"
    for _ in range(3):
        with pytest.raises(TakeRejectedError, match=r"fixed .*frame budget"):
            generate_narration(
                narration_path=NARRATION_PATH,
                project=project,
                output_dir=tmp_path / "cap-output",
                manifest_path=cap_manifest,
                api_key="test-key",
                transport=cap_transport,
                sleep=lambda _: None,
            )
    with pytest.raises(TakeLimitError, match="three-take cap"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=tmp_path / "cap-output",
            manifest_path=cap_manifest,
            api_key="test-key",
            transport=cap_transport,
            sleep=lambda _: None,
        )
    assert len(cap_transport.requests) == 3

    concurrent_manifest = tmp_path / "concurrent-work" / "take-series.json"
    concurrent_transport = _SlowRejectingTransport(_speech_response(overlong_wav))
    exceptions: list[SpeechError] = []
    exception_lock = threading.Lock()
    start = threading.Barrier(4)

    def generate_concurrently() -> None:
        start.wait()
        try:
            generate_narration(
                narration_path=NARRATION_PATH,
                project=project,
                output_dir=tmp_path / "concurrent-output",
                manifest_path=concurrent_manifest,
                api_key="test-key",
                transport=concurrent_transport,
                sleep=lambda _: None,
            )
        except SpeechError as exc:
            with exception_lock:
                exceptions.append(exc)

    threads = [threading.Thread(target=generate_concurrently) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert all(not thread.is_alive() for thread in threads)
    assert concurrent_transport.request_count == 3
    assert sum(isinstance(exc, TakeRejectedError) for exc in exceptions) == 3
    assert sum(isinstance(exc, TakeLimitError) for exc in exceptions) == 1

    with pytest.raises(SpendLimitError, match="USD 1"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=tmp_path / "spend-output",
            manifest_path=tmp_path / "spend-work" / "take-series.json",
            api_key="test-key",
            transport=_ScriptedTransport(deque((_speech_response(accepted_wav),))),
            policy=SpeechPolicy(projected_cost_per_take_usd=Decimal("0.34")),
            sleep=lambda _: None,
        )


def test_tc_t6_003__evidence_and_dry_run__exclude_secrets_and_itemized_billing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    project = _project()
    secret = "".join(("s", "k", "-", "proj-super-secret-shaped-value"))
    denial = json.dumps({"error": "denied", "credential": DENIAL_SECRET})
    transport = _ScriptedTransport(
        deque((HttpResponse(status=403, headers={}, body=denial.encode()),))
    )
    manifest_path = tmp_path / "work" / "take-series.json"
    with pytest.raises(SpeechTerminalError, match="permission"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=tmp_path / "output",
            manifest_path=manifest_path,
            api_key=secret,
            transport=transport,
            sleep=lambda _: None,
        )

    manifest_text = manifest_path.read_text(encoding="utf-8")
    summary = dry_run_summary(NARRATION_PATH, project)
    combined = "\n".join((manifest_text, caplog.text, summary))
    assert json.loads(summary) == {
        "model": "gpt-4o-mini-tts",
        "projected_bound_usd": "0.14",
        "segment_count": 6,
        "voice": "marin",
    }
    assert secret not in combined
    assert DENIAL_SECRET not in combined
    assert "authorization" not in combined.lower()
    assert "invoice" not in combined.lower()
    assert "line_item" not in combined.lower()
    assert "billing_export" not in combined.lower()
