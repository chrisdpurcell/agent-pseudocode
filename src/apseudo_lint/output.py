"""Compatibility formatting helpers for callers that want a simple function."""

from __future__ import annotations

from .model import Diagnostic


def format_issues(diagnostics: list[Diagnostic], output_format: str = "text") -> str:
    if output_format == "json":
        import json

        return json.dumps([diag.as_dict() for diag in diagnostics], indent=2, sort_keys=True)
    if output_format == "github":
        return "\n".join(diag.format_github() for diag in diagnostics)
    return "\n".join(diag.format_text() for diag in diagnostics)
