from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apseudo_lint.config import load_config
from apseudo_lint.discover import discover_changed_paths
from apseudo_lint.extract import collect_paths, extract_snippets
from apseudo_lint.lint import lint_paths
from apseudo_lint.model import LintConfig, Severity

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class APseudoLintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(explicit=ROOT / ".apseudo-lint.toml")

    def diagnostics(self, path: str):
        return lint_paths([FIXTURES / path], self.config)

    def codes(self, path: str) -> set[str]:
        return {diag.code for diag in self.diagnostics(path)}

    def test_valid_review_loop_has_no_errors(self) -> None:
        errors = [
            diag
            for diag in self.diagnostics("valid/review_loop.apseudo")
            if diag.severity == Severity.ERROR
        ]
        self.assertEqual(errors, [])

    def test_valid_guard_clauses_have_no_errors(self) -> None:
        errors = [
            diag
            for diag in self.diagnostics("valid/guard_clauses.apseudo")
            if diag.severity == Severity.ERROR
        ]
        self.assertEqual(errors, [])

    def test_markdown_fence_is_extracted_with_source_line(self) -> None:
        snippets = extract_snippets(FIXTURES / "valid/markdown_fence.md", self.config)
        self.assertEqual(len(snippets), 1)
        self.assertEqual(snippets[0].start_line, 4)

    def test_unbounded_loop_is_error(self) -> None:
        self.assertIn("APSEUDO-WHILE-001", self.codes("invalid/unbounded_loop.apseudo"))

    def test_unknown_outcome_is_warning(self) -> None:
        self.assertIn("APSEUDO-OUTCOME-001", self.codes("invalid/unbounded_loop.apseudo"))

    def test_missing_fallback_warns(self) -> None:
        self.assertIn("APSEUDO-BRANCH-001", self.codes("invalid/missing_fallback.apseudo"))

    def test_missing_return_is_error(self) -> None:
        self.assertIn("APSEUDO-RETURN-001", self.codes("invalid/no_return.apseudo"))

    def test_while_true_requires_annotation_and_exit(self) -> None:
        codes = self.codes("invalid/while_true.apseudo")
        self.assertIn("APSEUDO-WHILE-001", codes)
        self.assertIn("APSEUDO-WHILE-003", codes)

    def test_parse_error_is_error(self) -> None:
        self.assertIn("APSEUDO-PARSE-001", self.codes("invalid/parse_error.md"))

    def test_collect_paths_expands_directories(self) -> None:
        paths = collect_paths([FIXTURES / "valid"], self.config)
        self.assertTrue(any(path.name == "review_loop.apseudo" for path in paths))
        self.assertTrue(any(path.name == "fenced.md" for path in paths))

    def test_changed_path_discovery_respects_excludes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            skipped = root / "skip" / "example.md"
            kept = root / "keep" / "example.md"
            skipped.parent.mkdir()
            kept.parent.mkdir()
            skipped.write_text("# skip\n", encoding="utf-8")
            kept.write_text("# keep\n", encoding="utf-8")

            def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                del args, kwargs
                return subprocess.CompletedProcess(
                    args=["git"],
                    returncode=0,
                    stdout="skip/example.md\nkeep/example.md\n",
                    stderr="",
                )

            config = LintConfig(exclude=["skip"])
            with (
                patch("apseudo_lint.discover.git_root", return_value=root),
                patch("apseudo_lint.discover.subprocess.run", side_effect=fake_run),
            ):
                paths = discover_changed_paths(config)

        self.assertEqual(paths, [kept])

    def test_cli_json_output(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apseudo_lint",
                "--config",
                str(ROOT / ".apseudo-lint.toml"),
                "--format",
                "json",
                "tests/fixtures/valid/review_loop.apseudo",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["failures"], 0)
        self.assertEqual(payload["summary"]["error"], 0)


class APseudoFormatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(explicit=ROOT / ".apseudo-lint.toml")

    def test_formatter_normalizes_safe_whitespace(self) -> None:
        from apseudo_lint.formatting import FormatOptions, format_file

        result = format_file(FIXTURES / "format/messy.apseudo", self.config, FormatOptions())
        self.assertIn("process messy(document):", result.formatted)
        self.assertIn("# agent MUST NOT skip validation", result.formatted)
        self.assertIn("round = 1", result.formatted)
        self.assertIn("while round <= max_rounds:", result.formatted)
        self.assertIn("review = review_document(document)  # MUST check blockers", result.formatted)
        self.assertTrue(result.formatted.endswith("\n"))
        self.assertNotIn("\n\n\n", result.formatted)

    def test_formatter_formats_only_supported_markdown_fences(self) -> None:
        from apseudo_lint.formatting import FormatOptions, format_file

        result = format_file(FIXTURES / "format/messy.md", self.config, FormatOptions())
        self.assertIn("process demo(document):", result.formatted)
        self.assertIn("# agent MUST validate", result.formatted)
        self.assertIn("x=1", result.formatted)


class APseudoCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(explicit=ROOT / ".apseudo-lint.toml")

    def test_completion_specs_include_configured_outcomes(self) -> None:
        from apseudo_lint.completions import completion_specs

        labels = {item.label for item in completion_specs(self.config)}
        self.assertIn("Accepted", labels)
        self.assertIn("Blocked", labels)
        self.assertIn("review-loop", labels)

    def test_hover_token_lookup(self) -> None:
        from apseudo_lint.completions import hover_markdown, token_at_position

        text = 'return Blocked(reason="no")'
        token = token_at_position(text, 0, 10)
        self.assertEqual(token, "Blocked")
        self.assertIsNotNone(hover_markdown("Blocked", self.config))


if __name__ == "__main__":
    unittest.main()
