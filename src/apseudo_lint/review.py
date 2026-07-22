"""Project-level review helpers for the Agent Pseudocode toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .extract import collect_paths
from .lint import lint_paths
from .model import Diagnostic, LintConfig, Severity


@dataclass(frozen=True, slots=True)
class ReviewCheck:
    """One traceability or completeness check."""

    area: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        """Return JSON-serializable check data."""

        return {"area": self.area, "status": self.status, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ProjectReview:
    """Summary of project-level pseudocode health."""

    root: Path
    files_checked: int
    diagnostics: list[Diagnostic]
    checks: list[ReviewCheck]

    @property
    def errors(self) -> int:
        """Count error diagnostics."""

        return sum(1 for diag in self.diagnostics if diag.severity == Severity.ERROR)

    @property
    def warnings(self) -> int:
        """Count warning diagnostics."""

        return sum(1 for diag in self.diagnostics if diag.severity == Severity.WARNING)

    def as_dict(self) -> dict[str, object]:
        """Return JSON-serializable review data."""

        return {
            "root": str(self.root),
            "files_checked": self.files_checked,
            "summary": {
                "diagnostics": len(self.diagnostics),
                "errors": self.errors,
                "warnings": self.warnings,
            },
            "checks": [check.as_dict() for check in self.checks],
            "diagnostics": [diag.as_dict() for diag in self.diagnostics],
        }

    def as_markdown(self) -> str:
        """Render the project review as Markdown."""

        lines = [
            "# Agent Pseudocode Project Review",
            "",
            f"- Root: `{self.root}`",
            f"- Files checked: {self.files_checked}",
            f"- Diagnostics: {len(self.diagnostics)} total, {self.errors} error(s), {self.warnings} warning(s)",
            "",
            "## Completeness checks",
            "",
            "| Area | Status | Detail |",
            "|---|---|---|",
        ]
        lines.extend(f"| {check.area} | {check.status} | {check.detail} |" for check in self.checks)
        if self.diagnostics:
            lines.extend(["", "## Diagnostics", ""])
            lines.extend(f"- `{diag.format_text()}`" for diag in self.diagnostics)
        return "\n".join(lines).rstrip() + "\n"


def review_project(root: Path, config: LintConfig | None = None) -> ProjectReview:
    """Run a lightweight project review for convention/tooling completeness."""

    actual_root = root.expanduser().resolve()
    effective = config or load_config(actual_root)
    paths = collect_paths([actual_root], effective)
    diagnostics = lint_paths(paths, effective)
    checks = [
        _check_file(
            actual_root, "Language convention", "docs/reference/PYTHONIC_PSEUDOCODE_STANDARD.md"
        ),
        _check_file(actual_root, "Token specification", "docs/reference/language/TOKEN-SPEC.md"),
        _check_file(actual_root, "VS Code extension", "products/vscode-extension/package.json"),
        _check_file(actual_root, "Kate syntax", "products/kate-integration/agent-pseudocode.xml"),
        _check_file(actual_root, "Formatter", "src/apseudo_lint/formatting.py"),
        _check_file(actual_root, "Validator", "src/apseudo_lint/lint.py"),
        _check_file(actual_root, "Language server", "src/apseudo_lint/lsp.py"),
        _check_file(actual_root, "MCP server", "src/apseudo_lint/mcp.py"),
        _check_file(actual_root, "Executable runner", "src/apseudo_lint/runner.py"),
        _check_file(actual_root, "Runner CLI", "src/apseudo_lint/runner_cli.py"),
        _check_file(actual_root, "Claude hooks", ".claude/settings.json"),
        _check_file(actual_root, "Codex hooks", ".codex/hooks.json"),
        _check_file(actual_root, "Claude skill", ".claude/skills/agent-pseudocode/SKILL.md"),
        _check_file(actual_root, "Codex skill", ".agents/skills/agent-pseudocode/SKILL.md"),
        _check_file(actual_root, "pre-commit", ".pre-commit-config.yaml"),
        _check_file(actual_root, "CI", ".github/workflows/apseudo-lint.yml"),
        _check_file(actual_root, "Agent wording", "docs/usage/AGENT-INSTRUCTIONS-WORDING.md"),
        _check_file(
            actual_root, "Traceability review", "docs/reviews/PROJECT-TRACEABILITY-REVIEW.md"
        ),
        _check_file(
            actual_root, "Executable runner spec", "docs/reference/EXECUTABLE-PSEUDOCODE-SPEC.md"
        ),
        _check_file(actual_root, "Runner usage", "docs/usage/RUNNER-USAGE.md"),
        _check_file(actual_root, "Future versions", "docs/roadmap/FUTURE-VERSIONS.md"),
    ]
    return ProjectReview(actual_root, len(paths), diagnostics, checks)


def _check_file(root: Path, area: str, relative: str) -> ReviewCheck:
    path = root / relative
    if path.exists():
        return ReviewCheck(area, "OK", f"`{relative}` present")
    return ReviewCheck(area, "MISSING", f"`{relative}` not found")
