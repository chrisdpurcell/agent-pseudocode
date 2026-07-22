"""Mermaid flowchart rendering for Agent Pseudocode.

This renderer is intentionally simple: it creates a readable flowchart view from
Python-shaped pseudocode. It is a visualization aid, not the source of truth and
not a substitute for validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .extract import extract_markdown_fences
from .model import LintConfig, Snippet

PROCESS_RE = re.compile(r"^(?:process|def)\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^)]*)\).*:")
HEADER_RE = re.compile(r"^(?P<kind>if|elif|else|while|for)\b(?P<body>.*):$")
RETURN_RE = re.compile(r"^return\s+(?P<expr>.+)$")
COMMENT_RE = re.compile(r"^\s*#")


@dataclass(frozen=True, slots=True)
class MermaidRenderResult:
    """Mermaid source and metadata."""

    source: str
    warning: str | None = None


def render_path(path: Path, config: LintConfig | None = None) -> MermaidRenderResult:
    """Render a supported file to Mermaid flowchart text."""

    effective = config or load_config(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in effective.markdown_extensions:
        snippets = extract_markdown_fences(path, text, effective)
        if not snippets:
            return MermaidRenderResult("flowchart TD\n", "No supported pseudocode fences found.")
        blocks = [render_snippet(snippet).source for snippet in snippets]
        return MermaidRenderResult("\n\n".join(blocks))
    return render_text(text, name=path.stem)


def render_text(text: str, *, name: str = "pseudocode") -> MermaidRenderResult:
    """Render raw pseudocode text to a Mermaid flowchart."""

    return render_snippet(Snippet(path=Path(f"{name}.apseudo"), text=text, name=name))


def render_snippet(snippet: Snippet) -> MermaidRenderResult:
    """Render one snippet to Mermaid flowchart source."""

    nodes: list[str] = ["flowchart TD"]
    edges: list[str] = []
    previous_node: str | None = None
    process_name = snippet.name or snippet.path.stem
    node_count = 0

    def add_node(label: str, *, shape: str = "rect") -> str:
        nonlocal node_count
        node_count += 1
        node_id = f"N{node_count}"
        safe_label = _escape_label(label)
        if shape == "diamond":
            nodes.append(f"    {node_id}{{{safe_label}}}")
        elif shape == "terminal":
            nodes.append(f"    {node_id}([{safe_label}])")
        else:
            nodes.append(f"    {node_id}[{safe_label}]")
        return node_id

    start = add_node(f"Start: {process_name}", shape="terminal")
    previous_node = start
    has_executable = False

    for raw_line in snippet.text.splitlines():
        stripped = raw_line.strip()
        if not stripped or COMMENT_RE.match(stripped):
            continue
        has_executable = True
        process_match = PROCESS_RE.match(stripped)
        if process_match is not None:
            process_name = process_match.group("name")
            node_id = add_node(f"process {process_name}(...)")
        else:
            return_match = RETURN_RE.match(stripped)
            if return_match is not None:
                node_id = add_node(f"return {return_match.group('expr')}", shape="terminal")
            else:
                header_match = HEADER_RE.match(stripped)
                if header_match is not None:
                    kind = header_match.group("kind")
                    body = header_match.group("body").strip()
                    label = kind if not body else f"{kind} {body}"
                    node_id = add_node(label, shape="diamond")
                else:
                    node_id = add_node(stripped)
        edges.append(f"    {previous_node} --> {node_id}")
        previous_node = node_id

    if not has_executable:
        end = add_node("No executable pseudocode found", shape="terminal")
        edges.append(f"    {start} --> {end}")

    warning = (
        "Mermaid output is a visualization aid; linted pseudocode remains the source of truth."
    )
    return MermaidRenderResult("\n".join([*nodes, *edges]) + "\n", warning)


def _escape_label(label: str) -> str:
    escaped = label.replace('"', "'").replace("[", "(").replace("]", ")")
    escaped = escaped.replace("{", "(").replace("}", ")")
    return f'"{escaped}"'
