"""Line-oriented validator for Pythonic Agent Pseudocode.

The validator intentionally uses tolerant structural heuristics rather than a
full executable Python parser. The pseudocode dialect is Python-shaped, but it
is allowed to contain domain actions and outcome constructors that are not real
runtime objects.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .extract import extract_snippets
from .model import Diagnostic, LintConfig, Severity, Snippet

CONTROL_KEYWORDS = {
    "and",
    "as",
    "break",
    "continue",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "if",
    "in",
    "is",
    "not",
    "or",
    "pass",
    "process",
    "return",
    "try",
    "while",
    "with",
    "yield",
}
BUILTINS = {
    "False",
    "None",
    "True",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "range",
    "set",
    "str",
    "sum",
    "tuple",
    "zip",
}
TERMINATORS = {"return", "break", "continue", "raise"}
BLOCK_HEADER_KEYWORDS = {
    "process",
    "def",
    "if",
    "elif",
    "else",
    "while",
    "for",
    "try",
    "except",
    "finally",
    "with",
}
BOUNDED_MARKERS = {
    "@bounded",
    "@external_stop_condition",
    "@explicit_stop_condition",
    "@timeout",
    "@round_cap",
    "@loop_cap",
    "@intentional_infinite_loop",
}
BRANCH_MARKERS = {"@exhaustive"}
EMPTY_BRANCH_MARKERS = {"@allow_empty_branch"}
MUTATION_VERIFIED_MARKERS = {"@verified", "@no_verification_required"}
BOUNDED_WORDS = {
    "attempt",
    "attempts",
    "budget",
    "cap",
    "counter",
    "deadline",
    "limit",
    "max",
    "maximum",
    "min",
    "remaining",
    "retry",
    "retries",
    "round",
    "rounds",
    "timeout",
    "until",
}
UNBOUNDED_CALL_ALLOW_MARKERS = {"@bounded", "@finite_collection", "@external_stop_condition"}
MUTATING_PREFIXES = (
    "apply_",
    "commit_",
    "create_",
    "delete_",
    "deploy_",
    "edit_",
    "merge_",
    "modify_",
    "publish_",
    "remove_",
    "replace_",
    "revise_",
    "save_",
    "send_",
    "update_",
    "write_",
)
VERIFYING_PREFIXES = (
    "assert_",
    "check_",
    "confirm_",
    "inspect_",
    "review_",
    "run_check",
    "run_test",
    "run_tests",
    "test_",
    "validate_",
    "verify_",
)

HEADER_RE = re.compile(r"^(?P<keyword>[A-Za-z_]\w*)\b")
PROCESS_RE = re.compile(
    r"^(process|def)\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^)]*)\)\s*(?:->\s*[^:]+)?\s*:"
)
IF_RE = re.compile(r"^(?P<kind>if|elif)\s+(?P<condition>.+?)\s*:")
ELSE_RE = re.compile(r"^else\s*:")
WHILE_RE = re.compile(r"^while\s+(?P<condition>.+?)\s*:")
FOR_RE = re.compile(r"^for\s+(?P<target>.+?)\s+in\s+(?P<iterable>.+?)\s*:")
RETURN_RE = re.compile(r"^return(?:\s+(?P<expr>.+))?$")
CALL_RE = re.compile(r"(?<![.\w])(?P<name>[A-Za-z_]\w*)\s*\(")
ASSIGN_RE = re.compile(r"(?<![=!<>])\b(?P<name>[A-Za-z_]\w*)\s*(?:[+\-*/%]?=)(?!=)")
NAME_RE = re.compile(r"\b[A-Za-z_]\w*\b")
LOWER_NORM_RE = re.compile(
    r"\b(must\s+not|should\s+not|must|should|may|required|optional)\b", re.IGNORECASE
)
SHALL_RE = re.compile(r"\b(SHALL NOT|SHALL)\b")
SNAKE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
OUTCOME_RE = re.compile(r"^(?P<name>[A-Z][A-Za-z0-9_]*)(?:\s*\(|$)")


@dataclass(frozen=True, slots=True)
class LogicalLine:
    """A line with indentation/comment information preserved."""

    index: int
    line_no: int
    text: str
    stripped: str
    indent: int
    code: str
    comment: str

    @property
    def is_blank(self) -> bool:
        return not self.stripped

    @property
    def is_comment(self) -> bool:
        return self.stripped.startswith("#")

    @property
    def is_code(self) -> bool:
        return bool(self.code.strip()) and not self.is_comment


@dataclass(frozen=True, slots=True)
class BlockRange:
    """Half-open logical-line indexes for a block body."""

    start_index: int
    end_index: int


def lint_paths(paths: Iterable[Path], config: LintConfig) -> list[Diagnostic]:
    """Lint all snippets extracted from files."""

    diagnostics: list[Diagnostic] = []
    for path in paths:
        if not path.exists():
            diagnostics.append(
                Diagnostic(path, 1, 1, "APSEUDO-IO-002", Severity.ERROR, "file does not exist")
            )
            continue
        try:
            snippets = extract_snippets(path, config)
        except UnicodeDecodeError as exc:
            diagnostics.append(
                Diagnostic(
                    path,
                    1,
                    1,
                    "APSEUDO-IO-001",
                    Severity.ERROR,
                    f"file is not valid UTF-8: {exc}",
                )
            )
            continue
        for snippet in snippets:
            diagnostics.extend(lint_snippet(snippet, config))
    return [diagnostic for diagnostic in diagnostics if diagnostic.code not in config.ignore_codes]


def lint_snippet(snippet: Snippet, config: LintConfig) -> list[Diagnostic]:
    """Lint one standalone source or Markdown fenced pseudocode block."""

    lines = _logical_lines(snippet)
    diagnostics: list[Diagnostic] = []

    if (
        config.require_process_declaration
        and not any(PROCESS_RE.match(line.code) for line in lines if line.is_code)
        and not any("@allow_missing_process" in line.text for line in lines)
    ):
        diagnostics.append(
            Diagnostic(
                snippet.path,
                snippet.start_line,
                1,
                "APSEUDO-PROC-001",
                Severity.WARNING,
                "pseudocode block has no process/def declaration",
                "Use `process name(...):` for full workflow instructions, or annotate `# @allow_missing_process`.",
                snippet.name,
            )
        )

    for line in lines:
        diagnostics.extend(_check_normative_case(snippet, line))
        if not line.is_code:
            continue
        diagnostics.extend(_check_parse_shape(snippet, lines, line))
        diagnostics.extend(_check_empty_header_body(snippet, lines, line))
        diagnostics.extend(_check_nesting(snippet, line, config))
        diagnostics.extend(_check_process(snippet, lines, line))
        diagnostics.extend(_check_while(snippet, lines, line))
        diagnostics.extend(_check_for(snippet, lines, line))
        diagnostics.extend(_check_if_chain(snippet, lines, line))
        diagnostics.extend(_check_return(snippet, line, config))
        diagnostics.extend(_check_action_names(snippet, line, config))
        if config.require_verification_after_mutation:
            diagnostics.extend(_check_mutation_verification(snippet, lines, line))

    return _filter_suppressed(diagnostics, lines)


def _logical_lines(snippet: Snippet) -> list[LogicalLine]:
    result: list[LogicalLine] = []
    for index, raw in enumerate(snippet.text.splitlines(), start=1):
        expanded = raw.expandtabs(4)
        stripped = expanded.strip()
        indent = len(expanded) - len(expanded.lstrip(" "))
        code, comment = _split_comment(expanded)
        result.append(
            LogicalLine(
                index=index - 1,
                line_no=snippet.to_source_line(index),
                text=expanded,
                stripped=stripped,
                indent=indent,
                code=code.strip(),
                comment=comment,
            )
        )
    return result


def _split_comment(line: str) -> tuple[str, str]:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char == "#":
            return line[:index], line[index:]
    return line, ""


def _diag(
    snippet: Snippet,
    line: LogicalLine,
    code: str,
    severity: Severity,
    message: str,
    hint: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        path=snippet.path,
        line=line.line_no,
        column=line.indent + 1,
        code=code,
        severity=severity,
        message=message,
        hint=hint,
        snippet_name=snippet.name,
    )


def _next_code_line(lines: list[LogicalLine], start_index: int) -> LogicalLine | None:
    for candidate in lines[start_index + 1 :]:
        if candidate.is_code:
            return candidate
    return None


def _body_range(lines: list[LogicalLine], header: LogicalLine) -> BlockRange:
    start = header.index + 1
    end = len(lines)
    for candidate in lines[start:]:
        if not candidate.is_code:
            continue
        if candidate.indent <= header.indent:
            end = candidate.index
            break
    return BlockRange(start_index=start, end_index=end)


def _body_code_lines(lines: list[LogicalLine], header: LogicalLine) -> list[LogicalLine]:
    body = _body_range(lines, header)
    return [line for line in lines[body.start_index : body.end_index] if line.is_code]


def _has_annotation_near(
    lines: list[LogicalLine], line: LogicalLine, markers: set[str] | frozenset[str]
) -> bool:
    haystacks = [line.comment.lower(), line.code.lower()]
    if line.index > 0 and lines[line.index - 1].is_comment:
        haystacks.append(lines[line.index - 1].stripped.lower())
    return any(marker in haystack for marker in markers for haystack in haystacks)


def _check_normative_case(snippet: Snippet, line: LogicalLine) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in LOWER_NORM_RE.finditer(line.text):
        value = match.group(0)
        if value != value.upper():
            diagnostics.append(
                _diag(
                    snippet,
                    line,
                    "APSEUDO-NORM-001",
                    Severity.WARNING,
                    f"normative keyword should be uppercase: {value!r}",
                    "Use MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, REQUIRED, or OPTIONAL.",
                )
            )
    if SHALL_RE.search(line.text):
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-NORM-002",
                Severity.WARNING,
                "SHALL is not part of this convention's approved normative vocabulary",
                "Use MUST/SHOULD/MAY vocabulary unless a project-specific standard requires SHALL.",
            )
        )
    return diagnostics


def _check_parse_shape(
    snippet: Snippet, lines: list[LogicalLine], line: LogicalLine
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    match = HEADER_RE.match(line.code)
    if match is None:
        return diagnostics
    keyword = match.group("keyword")
    if keyword not in BLOCK_HEADER_KEYWORDS:
        return diagnostics
    if keyword in {"if", "elif"} and IF_RE.match(line.code) is None:
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-PARSE-001",
                Severity.ERROR,
                f"{keyword} header must end with ':' and include a condition",
            )
        )
    elif keyword == "else" and ELSE_RE.match(line.code) is None:
        diagnostics.append(
            _diag(snippet, line, "APSEUDO-PARSE-001", Severity.ERROR, "else header must be `else:`")
        )
    elif keyword == "while" and WHILE_RE.match(line.code) is None:
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-PARSE-001",
                Severity.ERROR,
                "while header must end with ':' and include a condition",
            )
        )
    elif keyword == "for" and FOR_RE.match(line.code) is None:
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-PARSE-001",
                Severity.ERROR,
                "for header must follow `for item in collection:`",
            )
        )
    elif keyword in {"process", "def"} and PROCESS_RE.match(line.code) is None:
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-PARSE-001",
                Severity.ERROR,
                f"{keyword} declaration must follow `{keyword} name(...):`",
            )
        )
    elif not line.code.endswith(":"):
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-PARSE-001",
                Severity.ERROR,
                f"{keyword} block header must end with ':'",
            )
        )

    return diagnostics


def _check_empty_header_body(
    snippet: Snippet, lines: list[LogicalLine], line: LogicalLine
) -> list[Diagnostic]:
    if not _is_block_header(line):
        return []
    if _has_annotation_near(lines, line, EMPTY_BRANCH_MARKERS):
        return []
    next_line = _next_code_line(lines, line.index)
    if next_line is None or next_line.indent <= line.indent:
        return [
            _diag(
                snippet,
                line,
                "APSEUDO-PARSE-002",
                Severity.ERROR,
                "block header has no indented executable body",
            )
        ]
    body = _body_code_lines(lines, line)
    if body and all(child.code in {"pass", "..."} for child in body):
        return [
            _diag(
                snippet,
                line,
                "APSEUDO-BRANCH-002",
                Severity.WARNING,
                "block body is only a placeholder",
                "Replace placeholder bodies with an action/return, or annotate `# @allow_empty_branch`.",
            )
        ]
    return []


def _is_block_header(line: LogicalLine) -> bool:
    match = HEADER_RE.match(line.code)
    return bool(
        match and match.group("keyword") in BLOCK_HEADER_KEYWORDS and line.code.endswith(":")
    )


def _check_nesting(snippet: Snippet, line: LogicalLine, config: LintConfig) -> list[Diagnostic]:
    # Four spaces are the convention; tabs are expanded to four spaces earlier.
    nesting = line.indent // 4
    if nesting <= config.max_nesting:
        return []
    return [
        _diag(
            snippet,
            line,
            "APSEUDO-NEST-001",
            Severity.WARNING,
            f"nesting depth {nesting} exceeds configured maximum {config.max_nesting}",
            "Prefer guard clauses, helper processes, or decision tables for deep branching.",
        )
    ]


def _check_process(
    snippet: Snippet, lines: list[LogicalLine], line: LogicalLine
) -> list[Diagnostic]:
    if PROCESS_RE.match(line.code) is None:
        return []
    body = _body_code_lines(lines, line)
    returns = [child for child in body if RETURN_RE.match(child.code)]
    diagnostics: list[Diagnostic] = []
    if not returns:
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-RETURN-001",
                Severity.ERROR,
                "process has no terminal return outcome",
                "Every process should end in Accepted, Blocked, NeedsUserDecision, or another approved outcome.",
            )
        )
    terminal = _last_code_line(body)
    if terminal is not None and not _is_terminal_statement(terminal):
        diagnostics.append(
            _diag(
                snippet,
                terminal,
                "APSEUDO-RETURN-003",
                Severity.WARNING,
                "process body should end with an explicit terminal statement",
                "End the process with `return Outcome(...)`, `raise`, or an explicitly justified terminal action.",
            )
        )
    return diagnostics


def _check_while(snippet: Snippet, lines: list[LogicalLine], line: LogicalLine) -> list[Diagnostic]:
    match = WHILE_RE.match(line.code)
    if match is None:
        return []
    condition = match.group("condition").strip()
    body = _body_code_lines(lines, line)
    diagnostics: list[Diagnostic] = []
    has_bound_annotation = _has_annotation_near(lines, line, BOUNDED_MARKERS)

    if _condition_is_true(condition):
        if not has_bound_annotation:
            diagnostics.append(
                _diag(
                    snippet,
                    line,
                    "APSEUDO-WHILE-001",
                    Severity.ERROR,
                    "while True must be explicitly annotated with its stop condition",
                    "Use a bounded condition or add `# @intentional_infinite_loop` with reachable break/return.",
                )
            )
        if not _body_has_statement(body, {"break", "return", "raise"}):
            diagnostics.append(
                _diag(
                    snippet,
                    line,
                    "APSEUDO-WHILE-003",
                    Severity.ERROR,
                    "while True loop has no visible break, return, or raise",
                )
            )
        return diagnostics

    if not has_bound_annotation and not _condition_looks_bounded(condition):
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-WHILE-001",
                Severity.ERROR,
                "while loop has no obvious bounded stop condition",
                "Use a cap/deadline/max counter in the condition or annotate an external stop condition.",
            )
        )

    condition_names = _condition_names(condition)
    if condition_names and not _body_updates_condition(body, condition_names):
        diagnostics.append(
            _diag(
                snippet,
                line,
                "APSEUDO-WHILE-002",
                Severity.WARNING,
                "while loop body does not visibly update state used by the condition",
                "Update loop-control state, break/return from the loop, or annotate an external stop condition.",
            )
        )
    return diagnostics


def _check_for(snippet: Snippet, lines: list[LogicalLine], line: LogicalLine) -> list[Diagnostic]:
    match = FOR_RE.match(line.code)
    if match is None:
        return []
    iterable = match.group("iterable").strip()
    if _for_iterable_looks_bounded(iterable):
        return []
    if _has_annotation_near(lines, line, UNBOUNDED_CALL_ALLOW_MARKERS):
        return []
    return [
        _diag(
            snippet,
            line,
            "APSEUDO-FOR-001",
            Severity.WARNING,
            "for loop iterates over a call expression or unclear source without boundedness proof",
            "Prefer a named collection, `range(...)`, literal collection, or `# @bounded` annotation.",
        )
    ]


def _check_if_chain(
    snippet: Snippet, lines: list[LogicalLine], line: LogicalLine
) -> list[Diagnostic]:
    if IF_RE.match(line.code) is None or not line.code.startswith("if "):
        return []
    if _has_annotation_near(lines, line, BRANCH_MARKERS):
        return []
    chain = _same_indent_branch_chain(lines, line)
    if any(ELSE_RE.match(member.code) for member in chain):
        return []
    if _all_branch_bodies_terminal(lines, chain):
        return []
    return [
        _diag(
            snippet,
            line,
            "APSEUDO-BRANCH-001",
            Severity.WARNING,
            "if/elif chain has no explicit else fallback",
            "Add `else: return Blocked(...)` or annotate `# @exhaustive` when the conditions are complete.",
        )
    ]


def _check_return(snippet: Snippet, line: LogicalLine, config: LintConfig) -> list[Diagnostic]:
    match = RETURN_RE.match(line.code)
    if match is None:
        return []
    expr = (match.group("expr") or "").strip()
    if not expr:
        return [
            _diag(
                snippet,
                line,
                "APSEUDO-RETURN-002",
                Severity.WARNING,
                "return statement has no outcome value",
                "Prefer `return Accepted(...)`, `return Blocked(...)`, or another approved outcome.",
            )
        ]
    outcome_match = OUTCOME_RE.match(expr)
    if outcome_match is None:
        return [
            _diag(
                snippet,
                line,
                "APSEUDO-RETURN-002",
                Severity.WARNING,
                "return value is not an outcome constructor/name",
                "Prefer approved outcome names such as Accepted, Blocked, NeedsUserDecision.",
            )
        ]
    outcome = outcome_match.group("name")
    if outcome not in config.allowed_outcomes:
        return [
            _diag(
                snippet,
                line,
                "APSEUDO-OUTCOME-001",
                Severity.WARNING,
                f"unknown returned outcome {outcome!r}",
                "Add it to `.apseudo-lint.toml` if this is an intentional project outcome.",
            )
        ]
    return []


def _check_action_names(
    snippet: Snippet, line: LogicalLine, config: LintConfig
) -> list[Diagnostic]:
    if not config.require_verification_after_mutation:
        return []
    diagnostics: list[Diagnostic] = []
    for match in CALL_RE.finditer(line.code):
        name = match.group("name")
        if name in CONTROL_KEYWORDS or name in BUILTINS or name in config.allowed_outcomes:
            continue
        if name[:1].isupper():
            continue
        if not SNAKE_RE.match(name):
            diagnostics.append(
                _diag(
                    snippet,
                    line,
                    "APSEUDO-ACTION-002",
                    Severity.WARNING,
                    f"action/function name should use lower_snake_case: {name}",
                )
            )
    return diagnostics


def _check_mutation_verification(
    snippet: Snippet, lines: list[LogicalLine], line: LogicalLine
) -> list[Diagnostic]:
    if _has_annotation_near(lines, line, MUTATION_VERIFIED_MARKERS):
        return []
    mutating_names = [
        match.group("name")
        for match in CALL_RE.finditer(line.code)
        if match.group("name").startswith(MUTATING_PREFIXES)
    ]
    if not mutating_names:
        return []
    following = [
        candidate for candidate in lines[line.index + 1 : line.index + 5] if candidate.is_code
    ]
    if any(_line_verifies_or_terminates(candidate) for candidate in following):
        return []
    return [
        _diag(
            snippet,
            line,
            "APSEUDO-ACTION-001",
            Severity.WARNING,
            f"mutating action {mutating_names[0]!r} is not followed by visible verification",
            "Follow mutating actions with verify/check/test/review, a terminal return, or an annotation.",
        )
    ]


def _filter_suppressed(diagnostics: list[Diagnostic], lines: list[LogicalLine]) -> list[Diagnostic]:
    if not diagnostics:
        return diagnostics
    suppressed_next_lines = {
        line.line_no + 1 for line in lines if "apseudo-lint: disable-next-line" in line.text
    }
    suppressed_codes: dict[int, set[str]] = {}
    for line in lines:
        match = re.search(r"apseudo-lint:\s*disable(?:=|\s+)(?P<codes>[A-Z0-9_,\- ]+)", line.text)
        if match:
            codes = {
                part.strip() for part in re.split(r"[,\s]+", match.group("codes")) if part.strip()
            }
            suppressed_codes[line.line_no] = codes
    result: list[Diagnostic] = []
    for diagnostic in diagnostics:
        if diagnostic.line in suppressed_next_lines:
            continue
        codes = suppressed_codes.get(diagnostic.line)
        if codes and (diagnostic.code in codes or "all" in {code.lower() for code in codes}):
            continue
        result.append(diagnostic)
    return result


def _condition_is_true(condition: str) -> bool:
    return condition.strip() in {"True", "1", "true"}


def _condition_looks_bounded(condition: str) -> bool:
    lowered = condition.lower()
    if any(word in lowered for word in BOUNDED_WORDS) and re.search(r"[<>]=?|!=|==", condition):
        return True
    if re.search(r"\b\w+\s*[<>]=?\s*\d+\b", condition):
        return True
    if re.search(r"\b\w+\s*[<>]=?\s*max_\w+\b", lowered):
        return True
    return "deadline" in lowered or "timeout" in lowered


def _condition_names(condition: str) -> set[str]:
    names = set(NAME_RE.findall(condition))
    return {
        name
        for name in names
        if name not in CONTROL_KEYWORDS and name not in BUILTINS and not name[:1].isupper()
    }


def _body_updates_condition(body: list[LogicalLine], condition_names: set[str]) -> bool:
    if _body_has_statement(body, {"break", "return", "raise"}):
        return True
    for line in body:
        assignments = {match.group("name") for match in ASSIGN_RE.finditer(line.code)}
        if assignments & condition_names:
            return True
        for name in condition_names:
            if re.search(rf"\b{name}\.(append|clear|extend|pop|remove|update)\s*\(", line.code):
                return True
    return False


def _body_has_statement(body: list[LogicalLine], statements: set[str]) -> bool:
    return any(any(line.code.startswith(statement) for statement in statements) for line in body)


def _for_iterable_looks_bounded(iterable: str) -> bool:
    cleaned = iterable.strip()
    if cleaned.startswith("range("):
        return True
    if cleaned.startswith(("[", "(", "{", '"', "'")):
        return True
    if re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?", cleaned):
        return True
    return cleaned.startswith(("enumerate(", "sorted(", "reversed("))


def _same_indent_branch_chain(lines: list[LogicalLine], line: LogicalLine) -> list[LogicalLine]:
    chain = [line]
    body = _body_range(lines, line)
    cursor = body.end_index
    while cursor < len(lines):
        candidate = lines[cursor]
        if not candidate.is_code:
            cursor += 1
            continue
        if candidate.indent != line.indent:
            break
        if candidate.code.startswith("elif ") or candidate.code == "else:":
            chain.append(candidate)
            cursor = _body_range(lines, candidate).end_index
            continue
        break
    return chain


def _all_branch_bodies_terminal(lines: list[LogicalLine], chain: list[LogicalLine]) -> bool:
    if not chain:
        return False
    for header in chain:
        body = _body_code_lines(lines, header)
        terminal = _last_code_line(body)
        if terminal is None or not _is_terminal_statement(terminal):
            return False
    return True


def _last_code_line(lines: list[LogicalLine]) -> LogicalLine | None:
    for line in reversed(lines):
        if line.is_code:
            return line
    return None


def _is_terminal_statement(line: LogicalLine) -> bool:
    return any(
        line.code.startswith(statement) for statement in {"return", "raise", "break", "continue"}
    )


def _line_verifies_or_terminates(line: LogicalLine) -> bool:
    if _is_terminal_statement(line):
        return True
    return any(
        match.group("name").startswith(VERIFYING_PREFIXES) for match in CALL_RE.finditer(line.code)
    )
