"""Minimal Language Server Protocol implementation for Agent Pseudocode.

This module intentionally avoids external runtime dependencies. It implements a
small JSON-RPC/LSP subset over stdio and keeps all semantic checks delegated to
the same formatter/linter used by CLI, hooks, CI, and MCP.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

from . import __version__
from .completions import completion_specs, hover_markdown, token_at_position
from .config import load_config
from .extract import extract_markdown_fences
from .formatting import FormatOptions, format_text
from .lint import lint_snippet
from .model import Diagnostic, LintConfig, Severity, Snippet
from .rules import get_rule
from .symbols import (
    Symbol,
    definition_for_token,
    document_symbols,
    markdown_document_symbols,
    occurrences,
    token_range_at_position,
)

Json = dict[str, Any]

TEXT_DOCUMENT_SYNC_FULL = 1
DIAGNOSTIC_SEVERITY = {
    Severity.ERROR: 1,
    Severity.WARNING: 2,
    Severity.INFO: 3,
}
SYMBOL_KIND_FUNCTION = 12
SYMBOL_KIND_METHOD = 6
SYMBOL_KIND_EVENT = 24

NORMATIVE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bshall\s+not\b", re.IGNORECASE), "MUST NOT"),
    (re.compile(r"\bshall\b", re.IGNORECASE), "MUST"),
    (re.compile(r"\bmust\s+not\b", re.IGNORECASE), "MUST NOT"),
    (re.compile(r"\bshould\s+not\b", re.IGNORECASE), "SHOULD NOT"),
    (re.compile(r"\bmust\b", re.IGNORECASE), "MUST"),
    (re.compile(r"\bshould\b", re.IGNORECASE), "SHOULD"),
    (re.compile(r"\bmay\b", re.IGNORECASE), "MAY"),
    (re.compile(r"\brequired\b", re.IGNORECASE), "REQUIRED"),
    (re.compile(r"\boptional\b", re.IGNORECASE), "OPTIONAL"),
)
BLOCK_HEADER_RE = re.compile(r"^\s*(?:process|def|if|elif|else|while|for|try|except|finally|with)\b.*:\s*(?:#.*)?$")
PROCESS_RE = re.compile(r"^\s*(?:process|def)\s+[A-Za-z_]\w*\s*\(")


@dataclass(slots=True)
class Document:
    """Open text document tracked by the LSP server."""

    uri: str
    language_id: str
    version: int | None
    text: str
    path: Path | None = None


@dataclass(slots=True)
class APseudoLanguageServer:
    """Small synchronous LSP server."""

    root: Path = field(default_factory=Path.cwd)
    documents: dict[str, Document] = field(default_factory=lambda: cast(dict[str, Document], {}))
    shutdown_requested: bool = False
    trace: bool = False

    def serve(self) -> int:
        """Run the stdio JSON-RPC loop."""

        while True:
            message = self._read_message()
            if message is None:
                return 0
            try:
                should_exit = self._handle_message(message)
            except Exception as exc:  # pragma: no cover - defensive protocol boundary
                self._log(f"unhandled server error: {exc!r}")
                should_exit = False
            if should_exit:
                return 0 if self.shutdown_requested else 1

    def _read_message(self) -> Json | None:
        headers: dict[str, str] = {}
        while True:
            raw = sys.stdin.buffer.readline()
            if not raw:
                return None
            line = raw.decode("ascii", errors="replace").strip()
            if not line:
                break
            key, _, value = line.partition(":")
            headers[key.lower()] = value.strip()
        length_raw = headers.get("content-length")
        if length_raw is None:
            return None
        body = sys.stdin.buffer.read(int(length_raw))
        payload = json.loads(body.decode("utf-8"))
        return cast(Json, payload)

    def _handle_message(self, message: Json) -> bool:
        method = cast(str | None, message.get("method"))
        request_id = message.get("id")
        params = _as_dict(message.get("params"))
        if self.trace:
            self._log(f"<- {method or 'response'}")

        if method is None:
            return False
        if request_id is not None:
            result = self._handle_request(method, params)
            self._send_response(request_id, result)
            return False
        return self._handle_notification(method, params)

    def _handle_request(self, method: str, params: Json) -> Any:
        if method == "initialize":
            return self._initialize(params)
        if method == "shutdown":
            self.shutdown_requested = True
            return None
        if method == "textDocument/completion":
            return self._completion(params)
        if method == "textDocument/hover":
            return self._hover(params)
        if method == "textDocument/formatting":
            return self._formatting(params)
        if method == "textDocument/codeAction":
            return self._code_action(params)
        if method == "textDocument/documentSymbol":
            return self._document_symbol(params)
        if method == "textDocument/foldingRange":
            return self._folding_range(params)
        if method == "textDocument/definition":
            return self._definition(params)
        if method == "textDocument/references":
            return self._references(params)
        if method == "workspace/symbol":
            return self._workspace_symbol(params)
        return None

    def _handle_notification(self, method: str, params: Json) -> bool:
        if method == "exit":
            return True
        if method == "initialized":
            return False
        if method == "textDocument/didOpen":
            self._did_open(params)
            return False
        if method == "textDocument/didChange":
            self._did_change(params)
            return False
        if method == "textDocument/didSave":
            doc = self._document_from_params(params)
            if doc is not None:
                self._publish_diagnostics(doc)
            return False
        if method == "textDocument/didClose":
            self._did_close(params)
            return False
        if method == "workspace/didChangeConfiguration":
            for doc in self.documents.values():
                self._publish_diagnostics(doc)
            return False
        return False

    def _initialize(self, params: Json) -> Json:
        root_uri = cast(str | None, params.get("rootUri"))
        root_path = _path_from_uri(root_uri) if root_uri else None
        if root_path is not None:
            self.root = root_path
        return {
            "capabilities": {
                "textDocumentSync": TEXT_DOCUMENT_SYNC_FULL,
                "completionProvider": {
                    "resolveProvider": False,
                    "triggerCharacters": ["@", "(", " ", "."],
                },
                "hoverProvider": True,
                "documentFormattingProvider": True,
                "codeActionProvider": {
                    "codeActionKinds": ["quickfix", "source.fixAll.apseudo", "source.formatDocument"]
                },
                "documentSymbolProvider": True,
                "foldingRangeProvider": True,
                "definitionProvider": True,
                "referencesProvider": True,
                "workspaceSymbolProvider": True,
            },
            "serverInfo": {"name": "apseudo-lsp", "version": __version__},
        }

    def _did_open(self, params: Json) -> None:
        doc_raw = _as_dict(params.get("textDocument"))
        uri = cast(str, doc_raw.get("uri", ""))
        document = Document(
            uri=uri,
            language_id=cast(str, doc_raw.get("languageId", "")),
            version=_optional_int(doc_raw.get("version")),
            text=cast(str, doc_raw.get("text", "")),
            path=_path_from_uri(uri),
        )
        self.documents[uri] = document
        self._publish_diagnostics(document)

    def _did_change(self, params: Json) -> None:
        doc = self._document_from_params(params)
        if doc is None:
            return
        changes = cast(list[Any], params.get("contentChanges", []))
        if not changes:
            return
        last = _as_dict(changes[-1])
        text = cast(str | None, last.get("text"))
        if text is None:
            return
        version = _optional_int(_as_dict(params.get("textDocument")).get("version"))
        updated = Document(doc.uri, doc.language_id, version, text, doc.path)
        self.documents[doc.uri] = updated
        self._publish_diagnostics(updated)

    def _did_close(self, params: Json) -> None:
        doc_raw = _as_dict(params.get("textDocument"))
        uri = cast(str, doc_raw.get("uri", ""))
        self.documents.pop(uri, None)
        self._send_notification("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []})

    def _document_from_params(self, params: Json) -> Document | None:
        doc_raw = _as_dict(params.get("textDocument"))
        uri = cast(str, doc_raw.get("uri", ""))
        return self.documents.get(uri)

    def _completion(self, params: Json) -> Json:
        doc = self._document_from_params(params)
        if doc is None or not self._position_is_supported_context(doc, params):
            return {"isIncomplete": False, "items": []}
        config = self._config_for(doc)
        return {"isIncomplete": False, "items": [item.as_lsp() for item in completion_specs(config)]}

    def _hover(self, params: Json) -> Json | None:
        doc = self._document_from_params(params)
        if doc is None or not self._position_is_supported_context(doc, params):
            return None
        position = _as_dict(params.get("position"))
        token = token_at_position(
            doc.text,
            _int_or_zero(position.get("line")),
            _int_or_zero(position.get("character")),
        )
        if token is None:
            return None
        rule = get_rule(token.upper()) if token.upper().startswith("APSEUDO-") else None
        contents = rule.as_markdown() if rule is not None else hover_markdown(token, self._config_for(doc))
        if contents is None:
            return None
        return {"contents": {"kind": "markdown", "value": contents}}

    def _formatting(self, params: Json) -> list[Json]:
        doc = self._document_from_params(params)
        if doc is None:
            return []
        options_raw = _as_dict(params.get("options"))
        tab_size = _int_or_default(options_raw.get("tabSize"), 4)
        formatted = format_text(
            doc.text,
            path=doc.path,
            config=self._config_for(doc),
            options=FormatOptions(indent_size=max(1, tab_size)),
        ).formatted
        if formatted == doc.text:
            return []
        return [{"range": _full_document_range(doc.text), "newText": formatted}]

    def _code_action(self, params: Json) -> list[Json]:
        doc = self._document_from_params(params)
        if doc is None:
            return []
        context = _as_dict(params.get("context"))
        diagnostics = cast(list[Json], context.get("diagnostics", []))
        only = cast(list[str], context.get("only", []))
        actions: list[Json] = []
        if not only or "source.fixAll.apseudo" in only:
            formatted = format_text(doc.text, path=doc.path, config=self._config_for(doc)).formatted
            if formatted != doc.text:
                actions.append(
                    {
                        "title": "Format Agent Pseudocode document",
                        "kind": "source.fixAll.apseudo",
                        "edit": {"changes": {doc.uri: [{"range": _full_document_range(doc.text), "newText": formatted}]}},
                    }
                )
        for diagnostic in diagnostics:
            action = _quickfix_for_diagnostic(doc, diagnostic)
            if action is not None:
                actions.append(action)
        return actions

    def _document_symbol(self, params: Json) -> list[Json]:
        doc = self._document_from_params(params)
        if doc is None:
            return []
        config = self._config_for(doc)
        symbols = (
            markdown_document_symbols(doc.path or Path("untitled.md"), doc.text, config)
            if self._is_markdown_document(doc)
            else document_symbols(doc.text)
        )
        return [_symbol_to_lsp(symbol) for symbol in symbols]

    def _folding_range(self, params: Json) -> list[Json]:
        doc = self._document_from_params(params)
        if doc is None:
            return []
        return _folding_ranges_for_text(doc.text)

    def _definition(self, params: Json) -> Json | None:
        doc = self._document_from_params(params)
        if doc is None or not self._position_is_supported_context(doc, params):
            return None
        position = _as_dict(params.get("position"))
        occurrence = token_range_at_position(
            doc.text,
            _int_or_zero(position.get("line")),
            _int_or_zero(position.get("character")),
        )
        if occurrence is None:
            return None
        symbol = definition_for_token(doc.text, occurrence.name)
        if symbol is None:
            return None
        return {"uri": doc.uri, "range": symbol.selection_range.as_lsp()}

    def _references(self, params: Json) -> list[Json]:
        doc = self._document_from_params(params)
        if doc is None or not self._position_is_supported_context(doc, params):
            return []
        position = _as_dict(params.get("position"))
        occurrence = token_range_at_position(
            doc.text,
            _int_or_zero(position.get("line")),
            _int_or_zero(position.get("character")),
        )
        if occurrence is None:
            return []
        return [{"uri": doc.uri, "range": item.range.as_lsp()} for item in occurrences(doc.text, occurrence.name)]

    def _workspace_symbol(self, params: Json) -> list[Json]:
        query = cast(str, params.get("query", "")).lower()
        result: list[Json] = []
        for doc in self.documents.values():
            symbols = document_symbols(doc.text)
            for symbol in symbols:
                if query and query not in symbol.name.lower():
                    continue
                result.append(
                    {
                        "name": symbol.name,
                        "kind": SYMBOL_KIND_FUNCTION,
                        "location": {"uri": doc.uri, "range": symbol.selection_range.as_lsp()},
                    }
                )
        return result

    def _publish_diagnostics(self, doc: Document) -> None:
        diagnostics = self._lint_document(doc)
        self._send_notification(
            "textDocument/publishDiagnostics",
            {
                "uri": doc.uri,
                "diagnostics": [_diagnostic_to_lsp(diag, doc.text) for diag in diagnostics],
            },
        )

    def _lint_document(self, doc: Document) -> list[Diagnostic]:
        config = self._config_for(doc)
        path = doc.path or Path("untitled.apseudo")
        if self._is_markdown_document(doc):
            diagnostics: list[Diagnostic] = []
            for snippet in extract_markdown_fences(path, doc.text, config):
                diagnostics.extend(lint_snippet(snippet, config))
            return diagnostics
        return lint_snippet(Snippet(path=path, text=doc.text, start_line=1, name=path.name), config)

    def _config_for(self, doc: Document) -> LintConfig:
        start = doc.path if doc.path is not None else self.root
        try:
            return load_config(start=start)
        except Exception as exc:  # pragma: no cover - filesystem/config defensive path
            self._log(f"failed to load config for {start}: {exc!r}")
            return LintConfig()

    def _is_markdown_document(self, doc: Document) -> bool:
        if doc.language_id.lower() == "markdown":
            return True
        if doc.path is None:
            return False
        return doc.path.suffix.lower() in LintConfig().markdown_extensions

    def _position_is_supported_context(self, doc: Document, params: Json) -> bool:
        if not self._is_markdown_document(doc):
            return True
        position = _as_dict(params.get("position"))
        return _line_is_inside_supported_fence(
            doc.text,
            _int_or_zero(position.get("line")),
            self._config_for(doc),
        )

    def _send_response(self, request_id: Any, result: Any) -> None:
        payload: Json = {"jsonrpc": "2.0", "id": request_id, "result": result}
        self._write(payload)

    def _send_notification(self, method: str, params: Json) -> None:
        payload: Json = {"jsonrpc": "2.0", "method": method, "params": params}
        self._write(payload)

    def _write(self, payload: Json) -> None:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        if self.trace:
            method = payload.get("method", "response")
            self._log(f"-> {method}")

    def _log(self, message: str) -> None:
        print(f"apseudo-lsp: {message}", file=sys.stderr, flush=True)


def _quickfix_for_diagnostic(doc: Document, diagnostic: Json) -> Json | None:
    code = cast(str, diagnostic.get("code", ""))
    range_raw = _as_dict(diagnostic.get("range"))
    start = _as_dict(range_raw.get("start"))
    line_index = _int_or_zero(start.get("line"))
    line_text = _line_at(doc.text, line_index)
    if line_text is None:
        return None

    if code in {"APSEUDO-NORM-001", "APSEUDO-NORM-002"}:
        new_text = _normalize_normative_line(line_text)
        if new_text != line_text:
            return _edit_action(
                doc,
                diagnostic,
                "Normalize normative keywords",
                {"range": _line_range(doc.text, line_index), "newText": new_text},
            )

    if code == "APSEUDO-BRANCH-001":
        indent = _leading_space(line_text)
        insert_line = _block_end_line(doc.text, line_index) + 1
        new_text = f"{indent}else:\n{indent}    return Blocked(reason=\"unhandled condition\")\n"
        return _edit_action(
            doc,
            diagnostic,
            "Add explicit else fallback",
            {"range": _empty_range(insert_line, 0), "newText": new_text},
        )

    if code in {"APSEUDO-RETURN-001", "APSEUDO-RETURN-003"}:
        insert_line = _block_end_line(doc.text, line_index) + 1
        indent = "    " if PROCESS_RE.match(line_text) else _leading_space(line_text)
        new_text = f"{indent}return Blocked(reason=\"terminal outcome required\")\n"
        return _edit_action(
            doc,
            diagnostic,
            "Add terminal Blocked outcome",
            {"range": _empty_range(insert_line, 0), "newText": new_text},
        )

    if code == "APSEUDO-WHILE-001":
        indent = _leading_space(line_text)
        new_text = f"{indent}# @bounded TODO: replace with a real cap, timeout, or external stop-condition rationale\n"
        return _edit_action(
            doc,
            diagnostic,
            "Insert bounded-loop annotation placeholder",
            {"range": _empty_range(line_index, 0), "newText": new_text},
        )

    if code == "APSEUDO-FOR-001":
        indent = _leading_space(line_text)
        new_text = f"{indent}# @finite_collection TODO: name or bound the collection before iterating\n"
        return _edit_action(
            doc,
            diagnostic,
            "Insert finite-collection annotation placeholder",
            {"range": _empty_range(line_index, 0), "newText": new_text},
        )

    if code == "APSEUDO-WHILE-002":
        indent = _leading_space(line_text) + "    "
        new_text = f"{indent}# TODO: update loop-control state visibly or return/break from the loop\n"
        return _edit_action(
            doc,
            diagnostic,
            "Insert loop-control update reminder",
            {"range": _empty_range(line_index + 1, 0), "newText": new_text},
        )

    rule = get_rule(code)
    if rule is None:
        return None
    return {
        "title": f"Explain {code}",
        "kind": "quickfix",
        "diagnostics": [diagnostic],
        "command": {
            "title": f"Explain {code}",
            "command": "agentPseudocode.explainRule",
            "arguments": [code],
        },
    }


def _edit_action(doc: Document, diagnostic: Json, title: str, edit: Json) -> Json:
    return {
        "title": title,
        "kind": "quickfix",
        "diagnostics": [diagnostic],
        "edit": {"changes": {doc.uri: [edit]}},
    }


def _diagnostic_to_lsp(diag: Diagnostic, text: str) -> Json:
    line_index = max(0, diag.line - 1)
    lines = text.splitlines()
    line_text = lines[line_index] if line_index < len(lines) else ""
    start_character = max(0, diag.column - 1)
    end_character = max(start_character + 1, len(line_text))
    message = f"{diag.code}: {diag.message}"
    if diag.hint:
        message += f"\n{diag.hint}"
    return {
        "range": {
            "start": {"line": line_index, "character": start_character},
            "end": {"line": line_index, "character": end_character},
        },
        "severity": DIAGNOSTIC_SEVERITY.get(diag.severity, 3),
        "code": diag.code,
        "source": "apseudo-lint",
        "message": message,
    }


def _symbol_to_lsp(symbol: Symbol) -> Json:
    return {
        "name": symbol.name,
        "kind": SYMBOL_KIND_FUNCTION if symbol.kind == "process" else SYMBOL_KIND_METHOD,
        "range": symbol.range.as_lsp(),
        "selectionRange": symbol.selection_range.as_lsp(),
    }


def _folding_ranges_for_text(text: str) -> list[Json]:
    ranges: list[Json] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not BLOCK_HEADER_RE.match(line):
            continue
        end = _block_end_line(text, index)
        if end > index:
            ranges.append({"startLine": index, "endLine": end, "kind": "region"})
    return ranges


def _block_end_line(text: str, header_line: int) -> int:
    lines = text.splitlines()
    if header_line < 0 or header_line >= len(lines):
        return header_line
    header = lines[header_line]
    header_indent = len(header) - len(header.lstrip(" "))
    end = header_line
    for index in range(header_line + 1, len(lines)):
        candidate = lines[index]
        if not candidate.strip():
            end = index
            continue
        indent = len(candidate) - len(candidate.lstrip(" "))
        if indent <= header_indent:
            break
        end = index
    return end


def _full_document_range(text: str) -> Json:
    lines = text.split("\n")
    if len(lines) == 1 and lines[0] == "":
        end_line = 0
        end_character = 0
    else:
        end_line = len(lines) - 1
        end_character = len(lines[-1])
    return {
        "start": {"line": 0, "character": 0},
        "end": {"line": end_line, "character": end_character},
    }


def diagnostic_to_lsp(diagnostic: Diagnostic, text: str) -> Json:
    """Public wrapper for converting a linter diagnostic to an LSP diagnostic."""

    return _diagnostic_to_lsp(diagnostic, text)


def full_document_range(text: str) -> Json:
    """Public wrapper for the whole-document LSP range used by formatting."""

    return _full_document_range(text)


def folding_ranges_for_text(text: str) -> list[Json]:
    """Public helper used by tests and clients."""

    return _folding_ranges_for_text(text)


def _normalize_normative_line(line: str) -> str:
    result = line
    for pattern, replacement in NORMATIVE_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    return result


def _line_at(text: str, line_index: int) -> str | None:
    lines = text.splitlines()
    if line_index < 0 or line_index >= len(lines):
        return None
    return lines[line_index]


def _line_range(text: str, line_index: int) -> Json:
    line = _line_at(text, line_index) or ""
    return {
        "start": {"line": line_index, "character": 0},
        "end": {"line": line_index, "character": len(line)},
    }


def _empty_range(line: int, character: int) -> Json:
    return {"start": {"line": line, "character": character}, "end": {"line": line, "character": character}}


def _leading_space(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" "))]


def _line_is_inside_supported_fence(text: str, zero_based_line: int, config: LintConfig) -> bool:
    lines = text.splitlines()
    in_fence = False
    marker = ""
    supported = False
    for index, line in enumerate(lines):
        stripped = line.rstrip("\r")
        if not in_fence:
            match = _fence_match(stripped)
            if match is None:
                continue
            in_fence = True
            marker = match["fence"]
            supported = match["language"] in config.markdown_fence_languages
            continue
        closing_prefix = marker[0] * len(marker)
        if stripped.lstrip().startswith(closing_prefix):
            in_fence = False
            marker = ""
            supported = False
            continue
        if index == zero_based_line:
            return supported
    return False


def _fence_match(line: str) -> dict[str, str] | None:
    match = re.match(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$", line)
    if match is None:
        return None
    info = match.group("info").strip()
    language = ""
    if info:
        first = info.split(maxsplit=1)[0].strip("{}")
        language = first[1:].lower() if first.startswith(".") else first.lower()
    return {"fence": match.group("fence"), "language": language}


def _path_from_uri(uri: str | None) -> Path | None:
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    path = unquote(parsed.path)
    if parsed.netloc:
        path = f"//{parsed.netloc}{path}"
    return Path(path)


def _as_dict(value: Any) -> Json:
    return cast(Json, value if isinstance(value, dict) else {})


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _int_or_zero(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _int_or_default(value: Any, default: int) -> int:
    return value if isinstance(value, int) else default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apseudo-lsp", description="Agent Pseudocode language server.")
    parser.add_argument("--stdio", action="store_true", help="Run over stdio. This is the default and exists for editor-client compatibility.")
    parser.add_argument("--trace", action="store_true", help="Log LSP message flow to stderr.")
    parser.add_argument("--version", action="version", version=f"apseudo-lsp {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return APseudoLanguageServer(trace=args.trace).serve()


if __name__ == "__main__":
    raise SystemExit(main())
