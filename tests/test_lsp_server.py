from __future__ import annotations

from pathlib import Path

from apseudo_lint.lsp import APseudoLanguageServer, Document, full_document_range


def test_lsp_lints_open_text() -> None:
    server = APseudoLanguageServer()
    document = Document(
        uri="file:///tmp/demo.apseudo",
        path=Path("/tmp/demo.apseudo"),
        language_id="agent-pseudocode",
        version=1,
        text="process demo():\n    while True:\n        do_work()\n    return Accepted(reason=\"done\")\n",
    )

    diagnostics = server._lint_document(document)

    assert any(diag.code == "APSEUDO-WHILE-001" for diag in diagnostics)


def test_lsp_initialize_advertises_expected_capabilities() -> None:
    server = APseudoLanguageServer()
    result = server._initialize({"rootUri": "file:///tmp"})

    capabilities = result["capabilities"]
    assert capabilities["completionProvider"]
    assert capabilities["hoverProvider"] is True
    assert capabilities["documentFormattingProvider"] is True


def test_lsp_completion_returns_configured_outcomes() -> None:
    server = APseudoLanguageServer()
    uri = "file:///tmp/demo.apseudo"
    server.documents[uri] = Document(
        uri=uri,
        path=Path("/tmp/demo.apseudo"),
        language_id="agent-pseudocode",
        version=1,
        text="process demo():\n    return ",
    )

    result = server._completion(
        {
            "textDocument": {"uri": uri},
            "position": {"line": 1, "character": 11},
        }
    )

    labels = {item["label"] for item in result["items"]}
    assert "Accepted" in labels
    assert "Blocked" in labels


def test_lsp_formatting_returns_whole_document_edit() -> None:
    server = APseudoLanguageServer()
    uri = "file:///tmp/demo.apseudo"
    server.documents[uri] = Document(
        uri=uri,
        path=Path("/tmp/demo.apseudo"),
        language_id="agent-pseudocode",
        version=1,
        text="PROCESS demo( a,b ) :\n    return Accepted(reason=\"ok\")\n",
    )

    edits = server._formatting({"textDocument": {"uri": uri}, "options": {"tabSize": 4}})

    assert edits
    assert edits[0]["newText"].startswith("process demo(a, b):")


def test_full_document_range_handles_trailing_newline() -> None:
    assert full_document_range("a\nb\n") == {
        "start": {"line": 0, "character": 0},
        "end": {"line": 2, "character": 0},
    }


def test_lsp_code_action_adds_else_fallback() -> None:
    server = APseudoLanguageServer()
    uri = "file:///tmp/demo.apseudo"
    text = "process demo():\n    if approved:\n        return Accepted(reason=\"ok\")\n    return Blocked(reason=\"done\")\n"
    server.documents[uri] = Document(
        uri=uri,
        path=Path("/tmp/demo.apseudo"),
        language_id="agent-pseudocode",
        version=1,
        text=text,
    )
    actions = server._code_action(
        {
            "textDocument": {"uri": uri},
            "context": {
                "diagnostics": [
                    {
                        "code": "APSEUDO-BRANCH-001",
                        "range": {"start": {"line": 1, "character": 4}, "end": {"line": 1, "character": 16}},
                    }
                ]
            },
        }
    )
    assert any(action["title"] == "Add explicit else fallback" for action in actions)


def test_lsp_symbols_folding_definition_and_references() -> None:
    server = APseudoLanguageServer()
    uri = "file:///tmp/demo.apseudo"
    text = "process demo():\n    result = helper()\n    return Accepted(reason=\"ok\")\n\nprocess helper():\n    return Accepted(reason=\"ok\")\n"
    server.documents[uri] = Document(
        uri=uri,
        path=Path("/tmp/demo.apseudo"),
        language_id="agent-pseudocode",
        version=1,
        text=text,
    )

    symbols = server._document_symbol({"textDocument": {"uri": uri}})
    folds = server._folding_range({"textDocument": {"uri": uri}})
    definition = server._definition(
        {"textDocument": {"uri": uri}, "position": {"line": 1, "character": 14}}
    )
    references = server._references(
        {"textDocument": {"uri": uri}, "position": {"line": 1, "character": 14}}
    )

    assert {symbol["name"] for symbol in symbols} == {"demo", "helper"}
    assert folds
    assert definition is not None
    assert len(references) >= 2
