"""Minimal MCP stdio server for Pythonic Agent Pseudocode.

The server intentionally implements the small, interoperable subset needed by
Claude Code and Codex: tools, resources, prompts, and initialization
instructions over newline-delimited JSON-RPC. It writes only JSON-RPC messages
to stdout and sends logs to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from . import __version__
from .config import load_config
from .executable import RunMode, parse_executable_file
from .extract import extract_markdown_fences
from .formatting import FormatOptions, format_file, format_text
from .lint import lint_paths, lint_snippet
from .mermaid import render_path, render_text
from .model import Diagnostic, LintConfig, Snippet
from .review import review_project
from .rules import get_rule, list_rules
from .runner import RunnerOptions, load_invocation, render_prompt, validate_script
from .templates import get_template, list_templates

Json = dict[str, Any]

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "agent-pseudocode"

MCP_INSTRUCTIONS = """Use this server whenever you create, edit, validate, explain, or repair Pythonic Agent Pseudocode. Treat apseudo.validate_text and apseudo.validate_file as the source of truth. Do not declare pseudocode work complete until validation is clean or unresolved APSEUDO-* diagnostics are explicitly surfaced. Use templates for new workflows, format_text before finalizing generated pseudocode, and explain_rule when a diagnostic is unclear.""".strip()


def main(argv: list[str] | None = None) -> int:
    """Run the MCP stdio server."""

    args = _build_parser().parse_args(argv)
    server = APseudoMCPServer(root=args.root.resolve(), trace=args.trace)
    return server.serve()


class APseudoMCPServer:
    """Small synchronous MCP server."""

    def __init__(self, *, root: Path, trace: bool = False) -> None:
        self.root = root
        self.trace = trace

    def serve(self) -> int:
        """Run the newline-delimited JSON-RPC loop."""

        for raw_line in sys.stdin.buffer:
            if not raw_line.strip():
                continue
            try:
                message = json.loads(raw_line.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._log(f"invalid JSON-RPC message: {exc}")
                continue
            response = self.handle_message(cast(Json, message))
            if response is not None:
                self._write(response)
        return 0

    def handle_message(self, message: Json) -> Json | None:
        """Handle one JSON-RPC request or notification."""

        method = cast(str | None, message.get("method"))
        request_id = message.get("id")
        params = _as_dict(message.get("params"))
        if self.trace:
            self._log(f"<- {method or 'response'}")
        if method is None or request_id is None:
            return None
        try:
            result = self._handle_request(method, params)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:  # pragma: no cover - defensive protocol boundary
            self._log(f"unhandled error for {method}: {exc!r}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    def _handle_request(self, method: str, params: Json) -> Any:
        if method == "initialize":
            return self._initialize()
        if method == "tools/list":
            return {"tools": _tool_definitions()}
        if method == "tools/call":
            return self._call_tool(params)
        if method == "resources/list":
            return {"resources": _resource_definitions()}
        if method == "resources/read":
            return self._read_resource(params)
        if method == "prompts/list":
            return {"prompts": _prompt_definitions()}
        if method == "prompts/get":
            return self._get_prompt(params)
        if method == "ping":
            return {}
        if method == "shutdown":
            return None
        raise ValueError(f"unsupported MCP method: {method}")

    def _initialize(self) -> Json:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {"name": SERVER_NAME, "version": __version__},
            "instructions": MCP_INSTRUCTIONS,
        }

    def _call_tool(self, params: Json) -> Json:
        name = cast(str, params.get("name", ""))
        arguments = _as_dict(params.get("arguments"))
        handlers = {
            "validate_text": self._tool_validate_text,
            "validate_file": self._tool_validate_file,
            "format_text": self._tool_format_text,
            "format_file": self._tool_format_file,
            "explain_rule": self._tool_explain_rule,
            "list_rules": self._tool_list_rules,
            "generate_template": self._tool_generate_template,
            "render_mermaid": self._tool_render_mermaid,
            "review_project": self._tool_review_project,
            "runner_check": self._tool_runner_check,
            "runner_render_prompt": self._tool_runner_render_prompt,
        }
        handler = handlers.get(name)
        if handler is None:
            return _tool_error(f"unknown tool: {name}")
        return handler(arguments)

    def _tool_validate_text(self, arguments: Json) -> Json:
        text = _string_arg(arguments, "text")
        filename = _string_arg(arguments, "filename", default="snippet.apseudo")
        path = Path(filename)
        config = self._config_for_path(path)
        diagnostics = self._lint_text(path, text, config)
        payload = _diagnostic_payload(diagnostics)
        return _tool_json(payload, is_error=payload["summary"]["errors"] > 0)

    def _tool_validate_file(self, arguments: Json) -> Json:
        path = self._resolve_path(_string_arg(arguments, "path"))
        config = self._config_for_path(path)
        diagnostics = lint_paths([path], config)
        payload = _diagnostic_payload(diagnostics)
        payload["path"] = str(path)
        return _tool_json(payload, is_error=payload["summary"]["errors"] > 0)

    def _tool_format_text(self, arguments: Json) -> Json:
        text = _string_arg(arguments, "text")
        filename = _string_arg(arguments, "filename", default="snippet.apseudo")
        path = Path(filename)
        formatted = format_text(
            text,
            path=path,
            config=self._config_for_path(path),
            options=FormatOptions(
                round_indentation=bool(arguments.get("round_indentation", False))
            ),
        ).formatted
        return _tool_text(formatted)

    def _tool_format_file(self, arguments: Json) -> Json:
        path = self._resolve_path(_string_arg(arguments, "path"))
        write = bool(arguments.get("write", False))
        config = self._config_for_path(path)
        result = format_file(path, config)
        if write and result.changed:
            path.write_text(result.formatted, encoding="utf-8")
        payload = {
            "path": str(path),
            "changed": result.changed,
            "written": bool(write and result.changed),
            "formatted": result.formatted if not write else "",
        }
        return _tool_json(payload)

    def _tool_explain_rule(self, arguments: Json) -> Json:
        code = _string_arg(arguments, "code").upper()
        rule = get_rule(code)
        if rule is None:
            return _tool_error(f"unknown rule code: {code}")
        return _tool_text(rule.as_markdown())

    def _tool_list_rules(self, _arguments: Json) -> Json:
        return _tool_json([asdict(rule) for rule in list_rules()])

    def _tool_generate_template(self, arguments: Json) -> Json:
        name = _string_arg(arguments, "name", default="bounded-review-loop")
        template = get_template(name)
        if template is None:
            return _tool_error(f"unknown template: {name}")
        return _tool_text(template.body)

    def _tool_render_mermaid(self, arguments: Json) -> Json:
        if "path" in arguments:
            path = self._resolve_path(_string_arg(arguments, "path"))
            result = render_path(path, config=self._config_for_path(path))
        else:
            result = render_text(_string_arg(arguments, "text"), name="mcp")
        body = "```mermaid\n" + result.source + "```\n"
        if result.warning:
            body += f"\nNote: {result.warning}\n"
        return _tool_text(body)

    def _tool_review_project(self, arguments: Json) -> Json:
        root_raw = _string_arg(arguments, "root", default=str(self.root))
        review = review_project(self._resolve_path(root_raw))
        if bool(arguments.get("json", False)):
            return _tool_json(review.as_dict(), is_error=review.errors > 0)
        return _tool_text(review.as_markdown(), is_error=review.errors > 0)

    def _tool_runner_check(self, arguments: Json) -> Json:
        path = self._resolve_path(_string_arg(arguments, "path"))
        script = parse_executable_file(path)
        validation = validate_script(script)
        payload = validation.as_dict()
        return _tool_json(payload, is_error=validation.failed)

    def _tool_runner_render_prompt(self, arguments: Json) -> Json:
        path = self._resolve_path(_string_arg(arguments, "path"))
        agent_raw = _string_arg(arguments, "agent", default="codex")
        mode_raw = _string_arg(arguments, "mode", default="plan")
        raw_args = arguments.get("args", {})
        script_args: list[str] = []
        if isinstance(raw_args, dict):
            typed_args = cast(dict[str, object], raw_args)
            script_args = [f"{key}={value}" for key, value in typed_args.items()]
        options = RunnerOptions(
            agent="claude" if agent_raw == "claude" else "codex",
            mode=_runner_mode_arg(mode_raw),
            workspace=self.root,
        )
        invocation = load_invocation(path, options=options, raw_script_args=script_args)
        return _tool_text(render_prompt(invocation))

    def _read_resource(self, params: Json) -> Json:
        uri = _string_arg(params, "uri")
        resource_map = {
            "apseudo://standard": self.root / "docs" / "PYTHONIC_PSEUDOCODE_STANDARD.md",
            "apseudo://rules": self.root / "docs" / "reference" / "RULES.md",
            "apseudo://agent-instructions": self.root / "docs" / "AGENT-INSTRUCTIONS-WORDING.md",
            "apseudo://feature-gap-analysis": self.root / "docs" / "FEATURE-GAP-ANALYSIS.md",
            "apseudo://traceability-review": self.root / "docs" / "PROJECT-TRACEABILITY-REVIEW.md",
        }
        path = resource_map.get(uri)
        if path is None:
            raise ValueError(f"unknown resource URI: {uri}")
        text = (
            path.read_text(encoding="utf-8")
            if path.exists()
            else f"Resource file not found: {path}\n"
        )
        return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]}

    def _get_prompt(self, params: Json) -> Json:
        name = _string_arg(params, "name")
        prompts = _prompts()
        prompt = prompts.get(name)
        if prompt is None:
            raise ValueError(f"unknown prompt: {name}")
        return {
            "description": prompt["description"],
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": prompt["text"]},
                }
            ],
        }

    def _lint_text(self, path: Path, text: str, config: LintConfig) -> list[Diagnostic]:
        if path.suffix.lower() in config.markdown_extensions:
            diagnostics: list[Diagnostic] = []
            for snippet in extract_markdown_fences(path, text, config):
                diagnostics.extend(lint_snippet(snippet, config))
            return diagnostics
        return lint_snippet(Snippet(path=path, text=text, start_line=1, name=path.name), config)

    def _config_for_path(self, path: Path) -> LintConfig:
        start = path if path.is_absolute() else self.root / path
        try:
            return load_config(start=start)
        except Exception:
            return LintConfig()

    def _resolve_path(self, raw: str) -> Path:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = self.root / path
        return path.resolve()

    def _write(self, payload: Json) -> None:
        sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
        sys.stdout.flush()
        if self.trace:
            self._log(f"-> {payload.get('id', 'notification')}")

    def _log(self, message: str) -> None:
        print(f"apseudo-mcp: {message}", file=sys.stderr, flush=True)


def _tool_definitions() -> list[Json]:
    return [
        _tool_schema(
            "validate_text",
            "Validate pseudocode text or Markdown apseudo fences.",
            {"text": {"type": "string"}, "filename": {"type": "string"}},
            ["text"],
        ),
        _tool_schema(
            "validate_file",
            "Validate one pseudocode or Markdown file.",
            {"path": {"type": "string"}},
            ["path"],
        ),
        _tool_schema(
            "format_text",
            "Format pseudocode text or Markdown apseudo fences.",
            {
                "text": {"type": "string"},
                "filename": {"type": "string"},
                "round_indentation": {"type": "boolean"},
            },
            ["text"],
        ),
        _tool_schema(
            "format_file",
            "Format one file; writes only when write=true.",
            {"path": {"type": "string"}, "write": {"type": "boolean"}},
            ["path"],
        ),
        _tool_schema(
            "explain_rule",
            "Explain an APSEUDO-* rule.",
            {"code": {"type": "string"}},
            ["code"],
        ),
        _tool_schema("list_rules", "List all APSEUDO-* rules.", {}, []),
        _tool_schema(
            "generate_template",
            "Generate a named pseudocode template.",
            {"name": {"type": "string", "enum": [template.name for template in list_templates()]}},
            [],
        ),
        _tool_schema(
            "render_mermaid",
            "Render pseudocode to a Mermaid visualization aid.",
            {"path": {"type": "string"}, "text": {"type": "string"}},
            [],
        ),
        _tool_schema(
            "review_project",
            "Review project-level pseudocode/tooling completeness.",
            {"root": {"type": "string"}, "json": {"type": "boolean"}},
            [],
        ),
        _tool_schema(
            "runner_check",
            "Validate an executable .apseudo runner script body.",
            {"path": {"type": "string"}},
            ["path"],
        ),
        _tool_schema(
            "runner_render_prompt",
            "Render the prompt an executable .apseudo script would feed to an agent.",
            {
                "path": {"type": "string"},
                "agent": {"type": "string", "enum": ["claude", "codex"]},
                "mode": {"type": "string", "enum": ["plan", "review", "apply", "danger"]},
                "args": {"type": "object"},
            },
            ["path"],
        ),
    ]


def _tool_schema(name: str, description: str, properties: Json, required: list[str]) -> Json:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


def _resource_definitions() -> list[Json]:
    return [
        {
            "uri": "apseudo://standard",
            "name": "Pythonic Agent Pseudocode Standard",
            "mimeType": "text/markdown",
        },
        {"uri": "apseudo://rules", "name": "APSEUDO rule catalog", "mimeType": "text/markdown"},
        {
            "uri": "apseudo://agent-instructions",
            "name": "Repository agent instruction wording",
            "mimeType": "text/markdown",
        },
        {
            "uri": "apseudo://feature-gap-analysis",
            "name": "Feature gap analysis",
            "mimeType": "text/markdown",
        },
        {
            "uri": "apseudo://traceability-review",
            "name": "Traceability review",
            "mimeType": "text/markdown",
        },
    ]


def _prompt_definitions() -> list[Json]:
    return [
        {"name": name, "description": value["description"], "arguments": []}
        for name, value in _prompts().items()
    ]


def _prompts() -> dict[str, dict[str, str]]:
    return {
        "write-process": {
            "description": "Draft a compliant Pythonic Agent Pseudocode process.",
            "text": "Draft the workflow using Pythonic Agent Pseudocode. Use process name(...):, explicit inputs, bounded loops, explicit else fallbacks, and approved terminal outcomes. Validate with apseudo.validate_text before finalizing.",
        },
        "fix-diagnostics": {
            "description": "Repair APSEUDO-* diagnostics without weakening the standard.",
            "text": "Use apseudo.validate_file to collect diagnostics, apseudo.explain_rule for unclear rules, then repair the source. Do not suppress or bypass a diagnostic unless the standard explicitly allows an annotation with rationale.",
        },
        "review-pseudocode": {
            "description": "Review a repository for pseudocode convention/tooling completeness.",
            "text": "Run apseudo.review_project and summarize missing enforcement or traceability. Separate implemented features, remaining gaps, and risks.",
        },
    }


def _diagnostic_payload(diagnostics: list[Diagnostic]) -> Json:
    errors = sum(1 for diag in diagnostics if diag.severity.value == "error")
    warnings = sum(1 for diag in diagnostics if diag.severity.value == "warning")
    return {
        "summary": {
            "diagnostics": len(diagnostics),
            "errors": errors,
            "warnings": warnings,
            "infos": sum(1 for diag in diagnostics if diag.severity.value == "info"),
        },
        "diagnostics": [diag.as_dict() for diag in diagnostics],
    }


def _tool_text(text: str, *, is_error: bool = False) -> Json:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _tool_json(payload: Any, *, is_error: bool = False) -> Json:
    return _tool_text(json.dumps(payload, indent=2, sort_keys=True), is_error=is_error)


def _tool_error(message: str) -> Json:
    return _tool_text(message, is_error=True)


def _string_arg(arguments: Json, name: str, *, default: str | None = None) -> str:
    value = arguments.get(name, default)
    if isinstance(value, str):
        return value
    if default is not None:
        return default
    raise ValueError(f"missing required string argument: {name}")


def _as_dict(value: Any) -> Json:
    return cast(Json, value if isinstance(value, dict) else {})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apseudo-mcp", description="Agent Pseudocode MCP stdio server."
    )
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Repository root for relative paths."
    )
    parser.add_argument("--trace", action="store_true", help="Log MCP message flow to stderr.")
    parser.add_argument("--version", action="version", version=f"apseudo-mcp {__version__}")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())


def _runner_mode_arg(value: str) -> RunMode:
    if value in {"plan", "review", "apply", "danger"}:
        return cast(RunMode, value)
    return "plan"
