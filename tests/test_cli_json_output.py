"""Regression tests for the `--json` output paths of the explain and template CLIs.

Both once serialized slots dataclasses via `__dict__`, which raises AttributeError
because `@dataclass(slots=True)` gives instances no attribute dict. Neither path
had a test, so `apseudo-explain --json` and `apseudo-template --json` crashed on
every invocation. See docs/handoff/bugs/006.
"""

from __future__ import annotations

import json

import pytest

from apseudo_lint import explain_cli, template_cli


def test_explain_json_lists_every_rule(capsys: pytest.CaptureFixture[str]) -> None:
    assert explain_cli.main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload, "rule catalog must not be empty"
    assert {"code", "title", "severity", "summary"} <= set(payload[0])
    assert all(rule["code"].startswith("APSEUDO-") for rule in payload)


def test_explain_json_for_a_single_rule(capsys: pytest.CaptureFixture[str]) -> None:
    assert explain_cli.main(["--json", "APSEUDO-WHILE-001"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [rule["code"] for rule in payload] == ["APSEUDO-WHILE-001"]


def test_explain_unknown_rule_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert explain_cli.main(["--json", "APSEUDO-NOPE-999"]) == 2
    assert "unknown rule code" in capsys.readouterr().err


def test_template_list_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert template_cli.main(["--list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload, "template catalog must not be empty"
    assert {"name", "title", "description", "body"} <= set(payload[0])


def test_template_default_listing_json(capsys: pytest.CaptureFixture[str]) -> None:
    """No template name and no --list still takes the listing branch."""
    assert template_cli.main(["--json"]) == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)


def test_template_single_json_emits_an_object(capsys: pytest.CaptureFixture[str]) -> None:
    assert template_cli.main(["bounded-review-loop", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "bounded-review-loop"
    assert payload["body"].strip()


def test_template_unknown_name_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert template_cli.main(["no-such-template", "--json"]) == 2
    assert "unknown template" in capsys.readouterr().err
