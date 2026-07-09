"""Completion and hover data for Agent Pseudocode."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import LintConfig
from .rules import get_rule

# LSP CompletionItemKind numeric values.
KIND_TEXT = 1
KIND_METHOD = 2
KIND_FUNCTION = 3
KIND_CONSTRUCTOR = 4
KIND_KEYWORD = 14
KIND_SNIPPET = 15
KIND_VALUE = 12
KIND_ENUM_MEMBER = 20

TOKEN_RE = re.compile(r"[A-Za-z_@][A-Za-z0-9_@.-]*")


@dataclass(frozen=True, slots=True)
class CompletionSpec:
    """Editor completion metadata independent of a specific client."""

    label: str
    insert_text: str
    detail: str
    documentation: str
    kind: int = KIND_TEXT
    is_snippet: bool = False

    def as_lsp(self) -> dict[str, object]:
        item: dict[str, object] = {
            "label": self.label,
            "kind": self.kind,
            "detail": self.detail,
            "documentation": {"kind": "markdown", "value": self.documentation},
            "insertText": self.insert_text,
        }
        if self.is_snippet:
            item["insertTextFormat"] = 2
        return item


KEYWORD_COMPLETIONS: tuple[CompletionSpec, ...] = (
    CompletionSpec("process", "process ${1:name}(${2:inputs}):\n    ${3:state} = ${4:initialize_state}(${2:inputs})\n    return ${5:Accepted}(reason=\"${6:complete}\")", "workflow declaration", "Defines an agent workflow. This is a convention extension, not executable Python.", KIND_SNIPPET, True),
    CompletionSpec("if", "if ${1:condition}:\n    ${2:action}()", "branch", "Starts a conditional branch. Prefer an explicit `else` unless the branch set is annotated exhaustive.", KIND_SNIPPET, True),
    CompletionSpec("elif", "elif ${1:condition}:\n    ${2:action}()", "branch", "Adds a mutually exclusive branch to an `if` chain.", KIND_SNIPPET, True),
    CompletionSpec("else", "else:\n    return Blocked(reason=\"${1:unhandled case}\")", "fallback branch", "Provides an explicit fallback branch.", KIND_SNIPPET, True),
    CompletionSpec("while", "attempt = 1\nwhile attempt <= ${1:max_attempts}:\n    ${2:action}()\n    attempt += 1", "bounded loop", "Repeats while a bounded condition holds. Every `while` loop must have a cap, timeout, or explicit external stop condition.", KIND_SNIPPET, True),
    CompletionSpec("for", "for ${1:item} in ${2:items}:\n    ${3:action}(${1:item})", "bounded iteration", "Iterates over a finite collection or bounded range.", KIND_SNIPPET, True),
    CompletionSpec("return", "return ${1:Accepted}(reason=\"${2:complete}\")", "terminal outcome", "Exits the process immediately with an approved outcome.", KIND_SNIPPET, True),
    CompletionSpec("continue", "continue", "loop control", "Continues the current loop.", KIND_KEYWORD),
    CompletionSpec("break", "break", "loop control", "Exits the current loop.", KIND_KEYWORD),
)

NORMATIVE_COMPLETIONS: tuple[CompletionSpec, ...] = (
    CompletionSpec("MUST", "MUST", "normative keyword", "Absolute requirement in this convention.", KIND_KEYWORD),
    CompletionSpec("MUST NOT", "MUST NOT", "normative keyword", "Absolute prohibition in this convention.", KIND_KEYWORD),
    CompletionSpec("SHOULD", "SHOULD", "normative keyword", "Recommended behavior unless there is a documented reason to differ.", KIND_KEYWORD),
    CompletionSpec("SHOULD NOT", "SHOULD NOT", "normative keyword", "Discouraged behavior unless there is a documented reason.", KIND_KEYWORD),
    CompletionSpec("MAY", "MAY", "normative keyword", "Optional behavior.", KIND_KEYWORD),
    CompletionSpec("REQUIRED", "REQUIRED", "normative keyword", "Required behavior or artifact.", KIND_KEYWORD),
    CompletionSpec("OPTIONAL", "OPTIONAL", "normative keyword", "Optional behavior or artifact.", KIND_KEYWORD),
)

ANNOTATION_COMPLETIONS: tuple[CompletionSpec, ...] = (
    CompletionSpec("@bounded", "@bounded", "loop annotation", "Marks a loop as intentionally bounded when the bound is not obvious syntactically.", KIND_ENUM_MEMBER),
    CompletionSpec("@external_stop_condition", "@external_stop_condition", "loop annotation", "Marks a loop as governed by an external stop condition.", KIND_ENUM_MEMBER),
    CompletionSpec("@explicit_stop_condition", "@explicit_stop_condition", "loop annotation", "Documents that the adjacent loop has an explicit stop condition.", KIND_ENUM_MEMBER),
    CompletionSpec("@timeout", "@timeout", "loop annotation", "Documents a timeout-based stop condition.", KIND_ENUM_MEMBER),
    CompletionSpec("@round_cap", "@round_cap", "loop annotation", "Documents a review/revision round cap.", KIND_ENUM_MEMBER),
    CompletionSpec("@finite_collection", "@finite_collection", "for-loop annotation", "Marks an iterable source as finite even when the expression is not obvious.", KIND_ENUM_MEMBER),
    CompletionSpec("@exhaustive", "@exhaustive", "branch annotation", "Marks an if/elif chain as exhaustive so an else fallback is not required.", KIND_ENUM_MEMBER),
    CompletionSpec("@allow_empty_branch", "@allow_empty_branch", "branch annotation", "Allows a placeholder branch body intentionally.", KIND_ENUM_MEMBER),
    CompletionSpec("@verified", "@verified", "action annotation", "Marks a mutating action as verified when the verification is not visible nearby.", KIND_ENUM_MEMBER),
    CompletionSpec("@no_verification_required", "@no_verification_required", "action annotation", "Documents why a mutating action does not need a verification step.", KIND_ENUM_MEMBER),
    CompletionSpec("@allow_missing_process", "@allow_missing_process", "snippet annotation", "Allows a snippet without a top-level process declaration.", KIND_ENUM_MEMBER),
)

ACTION_COMPLETIONS: tuple[CompletionSpec, ...] = (
    CompletionSpec("review_document", "review_document(${1:document})", "agent action", "Review an artifact and return review status/blockers.", KIND_FUNCTION, True),
    CompletionSpec("revise_using_blockers", "revise_using_blockers(${1:document}, ${2:blockers})", "agent action", "Revise an artifact using unresolved blockers.", KIND_FUNCTION, True),
    CompletionSpec("run_tests", "run_tests()", "verification action", "Run the relevant test suite or verification check.", KIND_FUNCTION, True),
    CompletionSpec("validate_output", "validate_output(${1:artifact})", "verification action", "Validate an output artifact against the acceptance checks.", KIND_FUNCTION, True),
    CompletionSpec("commit_changes", "commit_changes()", "mutating action", "Commit or persist a completed change. Follow with verification or a terminal outcome.", KIND_FUNCTION, True),
)

SNIPPET_COMPLETIONS: tuple[CompletionSpec, ...] = (
    CompletionSpec("review-loop", "process ${1:review_loop}(${2:document}, max_rounds=${3:5}):\n    round = 1\n    blockers = []\n\n    while round <= max_rounds:\n        review = review_document(${2:document})\n\n        if review.status == \"approved\":\n            return Accepted(reason=\"approved\")\n\n        elif review.blockers:\n            blockers = review.blockers\n            ${2:document} = revise_using_blockers(${2:document}, blockers)\n            round += 1\n            continue\n\n        else:\n            return Blocked(reason=\"ambiguous review result\")\n\n    return Blocked(reason=\"round cap reached\", unresolved_blockers=blockers)", "workflow snippet", "Bounded review/revision loop with explicit success and failure outcomes.", KIND_SNIPPET, True),
    CompletionSpec("guard-block", "if ${1:missing_required_input}:\n    return Blocked(reason=\"${2:missing required input}\")", "guard clause snippet", "Early exit for missing required input or invalid preconditions.", KIND_SNIPPET, True),
    CompletionSpec("decision-fallback", "else:\n    return Blocked(reason=\"${1:unhandled decision branch}\")", "fallback snippet", "Explicit fallback for non-exhaustive branch chains.", KIND_SNIPPET, True),
)

HOVER_TEXT: dict[str, str] = {
    "process": "Defines an agent workflow. Internal convention: `process` is Python-shaped pseudocode, not executable Python.",
    "MUST": "Absolute requirement in this convention.",
    "MUST NOT": "Absolute prohibition in this convention.",
    "SHOULD": "Recommended behavior unless there is a documented reason to differ.",
    "SHOULD NOT": "Discouraged behavior unless there is a documented reason.",
    "MAY": "Optional behavior.",
    "@bounded": "Loop annotation: use when the stop condition is real but not obvious from the condition expression.",
    "@exhaustive": "Branch annotation: use only when the branch conditions cover all possible cases.",
    "@verified": "Action annotation: use when verification occurred outside the visible nearby lines.",
    "Accepted": "Approved terminal outcome meaning the process completed successfully.",
    "Blocked": "Terminal outcome meaning the process cannot proceed without resolving a blocker.",
    "NeedsUserDecision": "Terminal outcome meaning the agent must stop and ask for a decision instead of guessing.",
}


def completion_specs(config: LintConfig) -> list[CompletionSpec]:
    """Return all completion specs, including project-configured outcomes."""

    outcomes = tuple(
        CompletionSpec(
            outcome,
            f"{outcome}(reason=\"${{1:reason}}\")",
            "approved outcome",
            "Configured terminal outcome for this project.",
            KIND_CONSTRUCTOR,
            True,
        )
        for outcome in sorted(config.allowed_outcomes)
    )
    return [
        *KEYWORD_COMPLETIONS,
        *NORMATIVE_COMPLETIONS,
        *ANNOTATION_COMPLETIONS,
        *outcomes,
        *ACTION_COMPLETIONS,
        *SNIPPET_COMPLETIONS,
    ]


def token_at_position(text: str, line: int, character: int) -> str | None:
    """Return the word-like token around a zero-based line/character position."""

    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    current = lines[line]
    character = max(0, min(character, len(current)))
    for match in TOKEN_RE.finditer(current):
        if match.start() <= character <= match.end():
            return match.group(0)
    return None


def hover_markdown(token: str, config: LintConfig) -> str | None:
    """Return hover Markdown for a token."""

    rule = get_rule(token.upper()) if token.upper().startswith("APSEUDO-") else None
    if rule is not None:
        return rule.as_markdown()
    if token in HOVER_TEXT:
        return HOVER_TEXT[token]
    if token in config.allowed_outcomes:
        return f"Configured terminal outcome `{token}`."
    return None
