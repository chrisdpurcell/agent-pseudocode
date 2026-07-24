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
from dataclasses import dataclass, field, replace
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
    PermissionProbe("Files", "GET", "/v1/files"),
    PermissionProbe("Fine-tuning", "GET", "/v1/fine_tuning/jobs"),
    PermissionProbe("Assistants", "GET", "/v1/assistants"),
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


@dataclass
class _ConcurrentSmokeTransport:
    speech_response: HttpResponse
    requests: list[HttpRequest] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, request: HttpRequest, *, timeout_seconds: float) -> HttpResponse:
        with self._lock:
            self.requests.append(request)
        time.sleep(0.05)
        if request.path == "/v1/audio/speech":
            return self.speech_response
        return HttpResponse(status=403, headers={}, body=b"denied")


def _project(tmp_path: Path, namespace: str) -> ProjectManifest:
    project = load_project(PROJECT_PATH, repository_root=REPOSITORY_ROOT)
    root = tmp_path / namespace / "dist" / "video"
    output = replace(
        project.output,
        root=root,
        narrated=root / "final" / project.output.narrated.name,
        speaker=root / "final" / project.output.speaker.name,
        render_manifest=root / "candidate" / project.output.render_manifest.name,
    )
    return replace(project, output=output)


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


def _only_series_manifest(project: ProjectManifest) -> Path:
    manifests = tuple((project.output.root / "work" / "narration-series").glob("*.json"))
    assert len(manifests) == 1
    return manifests[0]


def test_tc_t6_001__local_http_contract_and_permission_smoke__record_narrow_evidence(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path, "contract")
    package = load_narration(NARRATION_PATH, project)
    wav_bytes = _wav([30, 40, 50, 60, 70, 80])
    evidence_path = tmp_path / "production-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "project_key_denial_probes": {"status": "not-run", "requests": []},
                "future_stage_evidence": {"preserve": True},
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"

    with _local_speech_server(wav_bytes) as (base_url, server_state):
        transport = UrllibTransport(base_url=base_url, allow_insecure_for_tests=True)
        result = generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=output_dir,
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
        third_result = generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=output_dir,
            api_key=SECRET_SHAPED_VALUE,
            transport=transport,
            sleep=lambda _: None,
        )
        with pytest.raises(TakeLimitError, match="three-take cap"):
            generate_narration(
                narration_path=NARRATION_PATH,
                project=project,
                output_dir=output_dir,
                api_key=SECRET_SHAPED_VALUE,
                transport=transport,
                sleep=lambda _: None,
            )

    speech_requests = [
        request for request in server_state.requests if request[0:2] == ("POST", "/v1/audio/speech")
    ]
    assert len(speech_requests) == 3
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
    assert result.take_count == 1
    assert result.manifest_path.parent == project.output.root / "work" / "narration-series"
    assert result.manifest_path.name == f"{result.series_hash}.json"
    assert third_result.take_count == 3
    assert json.loads(result.manifest_path.read_text(encoding="utf-8"))["take_count"] == 3
    assert smoke["status"] == "pass"
    smoke_requests = cast(list[dict[str, object]], smoke["requests"])
    assert [entry["dashboard_permission"] for entry in smoke_requests] == [
        "Files",
        "Fine-tuning",
        "Assistants",
    ]
    assert all(
        set(entry) == {"dashboard_permission", "date", "status", "pass"} for entry in smoke_requests
    )
    denial_requests = [request for request in server_state.requests if request[0] == "GET"]
    assert [(method, path) for method, path, _, _ in denial_requests] == [
        ("GET", "/v1/files"),
        ("GET", "/v1/fine_tuning/jobs"),
        ("GET", "/v1/assistants"),
    ]
    for _, _, headers, body in denial_requests:
        assert headers["authorization"] == f"Bearer {SECRET_SHAPED_VALUE}"
        assert body == b""
    assert "openai-beta" not in denial_requests[0][2]
    assert "openai-beta" not in denial_requests[1][2]
    assert denial_requests[2][2]["openai-beta"] == "assistants=v2"
    assert denial_requests[2][2]["content-type"] == "application/json"
    assert all(not path.startswith("/v1/organization/") for _, path, _, _ in denial_requests)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    dashboard_bundle = cast(dict[str, object], evidence["dashboard_bundle"])
    assert evidence["future_stage_evidence"] == {"preserve": True}
    assert dashboard_bundle["scope"] == "Restricted"
    assert dashboard_bundle["speech_permitting_bundle"] == (
        "provider-bundled model capabilities: Request"
    )
    assert dashboard_bundle["independently_denied_bundled_model_capabilities"] is False
    assert dashboard_bundle["project_key_probe_targets"] == [
        "Files",
        "Fine-tuning",
        "Assistants",
    ]
    assert "project_key_verified_denials" not in dashboard_bundle
    assert dashboard_bundle["dashboard_only_denials"] == [
        "Management",
        "Administration",
    ]
    assert cast(dict[str, object], evidence["project_key_denial_probes"]) == smoke
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
            project=_project(tmp_path, "incomplete"),
            evidence_path=tmp_path / "incomplete-evidence.json",
            api_key="test-key",
            transport=incomplete_smoke,
            checked_date="2026-07-23",
            probes=(),
            mode="permission-smoke",
        )

    mislabeled_probes = (
        PermissionProbe("Files", "GET", "/v1/models"),
        *PERMISSION_PROBES[1:],
    )
    with pytest.raises(SpeechTerminalError, match="exact method and path"):
        run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=_project(tmp_path, "mislabeled"),
            evidence_path=tmp_path / "mislabeled-evidence.json",
            api_key="test-key",
            transport=_ScriptedTransport(deque()),
            checked_date="2026-07-23",
            probes=mislabeled_probes,
            mode="permission-smoke",
        )

    exact_probe_transport = _ScriptedTransport(
        deque(
            (
                _speech_response(wav_bytes),
                *(HttpResponse(status=403, headers={}, body=b"denied") for _ in range(3)),
            )
        )
    )
    run_permission_smoke(
        narration_path=NARRATION_PATH,
        project=_project(tmp_path, "exact-probe-contract"),
        evidence_path=tmp_path / "exact-probe-evidence.json",
        api_key="test-key",
        transport=exact_probe_transport,
        checked_date="2026-07-23",
        probes=PERMISSION_PROBES,
        mode="permission-smoke",
    )
    assert [
        (request.method, request.path, dict(request.headers), request.body)
        for request in exact_probe_transport.requests[1:]
    ] == [
        (
            "GET",
            "/v1/files",
            {"Authorization": "Bearer test-key"},
            b"",
        ),
        (
            "GET",
            "/v1/fine_tuning/jobs",
            {"Authorization": "Bearer test-key"},
            b"",
        ),
        (
            "GET",
            "/v1/assistants",
            {
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2",
            },
            b"",
        ),
    ]

    failed_smoke_path = tmp_path / "failed-evidence.json"
    failed_smoke_transport = _ScriptedTransport(
        deque(
            (
                HttpResponse(status=403, headers={}, body=b"denied"),
                *(HttpResponse(status=403, headers={}, body=b"denied") for _ in range(3)),
            )
        )
    )
    failed_smoke_project = _project(tmp_path, "failed-smoke")
    with pytest.raises(SpeechTerminalError, match="permission smoke failed"):
        run_permission_smoke(
            narration_path=NARRATION_PATH,
            project=failed_smoke_project,
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
            project=failed_smoke_project,
            evidence_path=tmp_path / "alternate-failed-evidence.json",
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
            project=_project(tmp_path, "unlocked"),
            output_dir=tmp_path / "unlocked-output",
            api_key="test-key",
            transport=_ScriptedTransport(deque()),
            sleep=lambda _: None,
        )

    with pytest.raises(SpeechTerminalError, match="canonical narration state path"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=_project(tmp_path, "override"),
            output_dir=tmp_path / "override-output",
            manifest_path=tmp_path / "caller-selected" / "take-series.json",
            api_key="test-key",
            transport=_ScriptedTransport(deque()),
            sleep=lambda _: None,
        )


def test_tc_t6_002__full_wav_guards__bound_takes_retries_and_spend(tmp_path: Path) -> None:
    project = _project(tmp_path, "retry")
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

    realistic_project = _project(tmp_path, "realistic")
    realistic_result = generate_narration(
        narration_path=NARRATION_PATH,
        project=realistic_project,
        output_dir=tmp_path / "realistic-output",
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
            project=_project(tmp_path, "terminal"),
            output_dir=tmp_path / "terminal-output",
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
    unavailable_project = _project(tmp_path, "unavailable")
    with pytest.raises(ProviderUnavailableError, match=r"AW-004.*blocked"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=unavailable_project,
            output_dir=tmp_path / "unavailable-output",
            api_key="test-key",
            transport=unavailable,
            sleep=lambda _: None,
        )
    assert json.loads(_only_series_manifest(unavailable_project).read_text(encoding="utf-8"))[
        "outcome"
    ] == ("AW-004: blocked")

    package = load_narration(NARRATION_PATH, project)
    first_budget = package.segments[0].end_frame - package.segments[0].start_frame
    overlong_wav = _wav([first_budget + 1, 40, 50, 60, 70, 80])
    cap_transport = _ScriptedTransport(deque(_speech_response(overlong_wav) for _ in range(3)))
    cap_project = _project(tmp_path, "cap")
    for _ in range(3):
        with pytest.raises(TakeRejectedError, match=r"fixed .*frame budget"):
            generate_narration(
                narration_path=NARRATION_PATH,
                project=cap_project,
                output_dir=tmp_path / "cap-output",
                api_key="test-key",
                transport=cap_transport,
                sleep=lambda _: None,
            )
    with pytest.raises(TakeLimitError, match="three-take cap"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=cap_project,
            output_dir=tmp_path / "cap-output",
            api_key="test-key",
            transport=cap_transport,
            sleep=lambda _: None,
        )
    assert len(cap_transport.requests) == 3

    concurrent_project = _project(tmp_path, "concurrent")
    concurrent_transport = _SlowRejectingTransport(_speech_response(overlong_wav))
    exceptions: list[SpeechError] = []
    exception_lock = threading.Lock()
    start = threading.Barrier(4)

    def generate_concurrently() -> None:
        start.wait()
        try:
            generate_narration(
                narration_path=NARRATION_PATH,
                project=concurrent_project,
                output_dir=tmp_path / "concurrent-output",
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

    mixed_project = _project(tmp_path, "mixed-concurrent")
    mixed_transport = _ConcurrentSmokeTransport(_speech_response(overlong_wav))
    mixed_exceptions: list[SpeechError] = []
    mixed_exception_lock = threading.Lock()
    mixed_start = threading.Barrier(4)

    def generate_in_mixed_race() -> None:
        mixed_start.wait()
        try:
            generate_narration(
                narration_path=NARRATION_PATH,
                project=mixed_project,
                output_dir=tmp_path / "mixed-output",
                api_key="test-key",
                transport=mixed_transport,
                sleep=lambda _: None,
            )
        except SpeechError as exc:
            with mixed_exception_lock:
                mixed_exceptions.append(exc)

    def smoke_in_mixed_race() -> None:
        mixed_start.wait()
        try:
            run_permission_smoke(
                narration_path=NARRATION_PATH,
                project=mixed_project,
                evidence_path=tmp_path / "mixed-evidence.json",
                api_key="test-key",
                transport=mixed_transport,
                checked_date="2026-07-23",
                probes=PERMISSION_PROBES,
                mode="permission-smoke",
            )
        except SpeechError as exc:
            with mixed_exception_lock:
                mixed_exceptions.append(exc)

    mixed_threads = [
        threading.Thread(target=generate_in_mixed_race),
        threading.Thread(target=generate_in_mixed_race),
        threading.Thread(target=generate_in_mixed_race),
        threading.Thread(target=smoke_in_mixed_race),
    ]
    for thread in mixed_threads:
        thread.start()
    for thread in mixed_threads:
        thread.join(timeout=5)
    assert all(not thread.is_alive() for thread in mixed_threads)
    assert sum(request.path == "/v1/audio/speech" for request in mixed_transport.requests) == 3
    assert (
        json.loads(_only_series_manifest(mixed_project).read_text(encoding="utf-8"))["take_count"]
        == 3
    )
    assert len(mixed_exceptions) in {3, 4}

    with pytest.raises(SpendLimitError, match="USD 1"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=_project(tmp_path, "spend"),
            output_dir=tmp_path / "spend-output",
            api_key="test-key",
            transport=_ScriptedTransport(deque((_speech_response(accepted_wav),))),
            policy=SpeechPolicy(projected_cost_per_take_usd=Decimal("0.34")),
            sleep=lambda _: None,
        )


def test_tc_t6_003__evidence_and_dry_run__exclude_secrets_and_itemized_billing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    project = _project(tmp_path, "evidence")
    secret = "".join(("s", "k", "-", "proj-super-secret-shaped-value"))
    denial = json.dumps({"error": "denied", "credential": DENIAL_SECRET})
    transport = _ScriptedTransport(
        deque((HttpResponse(status=403, headers={}, body=denial.encode()),))
    )
    with pytest.raises(SpeechTerminalError, match="permission"):
        generate_narration(
            narration_path=NARRATION_PATH,
            project=project,
            output_dir=tmp_path / "output",
            api_key=secret,
            transport=transport,
            sleep=lambda _: None,
        )

    manifest_text = _only_series_manifest(project).read_text(encoding="utf-8")
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
