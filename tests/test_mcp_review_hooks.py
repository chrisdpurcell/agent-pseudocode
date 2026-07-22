from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from apseudo_lint.mcp import APseudoMCPServer
from apseudo_lint.review import review_project
from apseudo_lint.rules import get_rule

ROOT = Path(__file__).resolve().parents[1]


def test_rule_catalog_explains_known_rule() -> None:
    rule = get_rule("APSEUDO-WHILE-001")
    assert rule is not None
    assert "bounded" in rule.as_markdown().lower()


def test_mcp_initialize_and_validate_text() -> None:
    server = APseudoMCPServer(root=ROOT)
    init = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init is not None
    assert init["result"]["serverInfo"]["name"] == "agent-pseudocode"

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "validate_text",
                "arguments": {"text": "process demo():\n    while ready:\n        do_work()\n"},
            },
        }
    )
    assert response is not None
    text = response["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["summary"]["diagnostics"] > 0


def test_mcp_template_tool_returns_body() -> None:
    server = APseudoMCPServer(root=ROOT)
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "generate_template",
                "arguments": {"name": "bounded-review-loop"},
            },
        }
    )
    assert response is not None
    assert "process review_until_accepted" in response["result"]["content"][0]["text"]


def test_review_project_reports_expected_tooling() -> None:
    review = review_project(ROOT)
    areas = {check.area: check.status for check in review.checks}
    assert areas["Validator"] == "OK"
    assert areas["MCP server"] == "OK"
    assert areas["Claude skill"] == "OK"
    assert areas["Codex skill"] == "OK"


def test_hook_blocks_no_verify_command() -> None:
    payload = {
        "cwd": str(ROOT),
        "tool_name": "Bash",
        "tool_input": {"command": "git commit --no-verify"},
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "integrations/agent-hooks" / "apseudo-hook.py"),
            "--host",
            "codex",
            "--event",
            "pre-tool-use",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--no-verify" in result.stderr
