from __future__ import annotations

from pathlib import Path

from apseudo_lint.formatting import FormatOptions, format_pseudocode_source, format_text
from apseudo_lint.model import LintConfig


def test_format_pseudocode_normalizes_spacing_keywords_and_comments() -> None:
    source = "PROCESS demo( a,b ) :  \n    IF count<max_rounds : # agent must continue\n    return Accepted(reason=\"ok\")\n\n\n"

    formatted = format_pseudocode_source(source)

    assert formatted == (
        "process demo(a, b):\n"
        "    if count < max_rounds:  # agent MUST continue\n"
        "    return Accepted(reason=\"ok\")\n"
    )


def test_format_markdown_only_changes_pseudocode_fences() -> None:
    source = (
        "# Demo  \n\n"
        "```apseudo\n"
        "PROCESS demo( a,b ) :\n"
        "    return Accepted(reason=\"ok\")\n"
        "```\n\n"
        "```python\n"
        "x=1\n"
        "```\n"
    )

    result = format_text(source, path=Path("demo.md"), config=LintConfig())

    assert "# Demo  \n" in result.formatted
    assert "process demo(a, b):\n" in result.formatted
    assert "    return Accepted(reason=\"ok\")\n" in result.formatted
    assert "x=1\n" in result.formatted


def test_format_options_can_leave_normative_case_alone() -> None:
    formatted = format_pseudocode_source(
        "# agent must review\n",
        options=FormatOptions(uppercase_normative=False),
    )

    assert formatted == "# agent must review\n"


def test_round_indentation_option_is_explicit() -> None:
    formatted = format_pseudocode_source(
        "  return Accepted(reason=\"ok\")\n",
        options=FormatOptions(round_indentation=True),
    )

    assert formatted == "    return Accepted(reason=\"ok\")\n"
