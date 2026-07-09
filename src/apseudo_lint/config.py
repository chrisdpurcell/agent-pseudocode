"""Configuration loading for apseudo-lint."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from .model import LintConfig

CONFIG_FILENAMES = (".apseudo-lint.toml", "apseudo.toml", "pyproject.toml")


def load_config(start: Path | None = None, explicit: Path | None = None) -> LintConfig:
    """Load linter configuration from an explicit file or nearest project config."""

    if explicit is not None:
        return _config_from_file(explicit)

    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in [current, *current.parents]:
        for name in CONFIG_FILENAMES:
            path = directory / name
            if path.exists():
                return _config_from_file(path)
        if (directory / ".git").exists():
            break

    return LintConfig()


def _config_from_file(path: Path) -> LintConfig:
    parsed: Any = tomllib.loads(path.read_text(encoding="utf-8"))
    data = cast(dict[str, Any], parsed if isinstance(parsed, dict) else {})

    raw_config: Any
    if path.name == "pyproject.toml":
        tool_raw = data.get("tool", {})
        tool = cast(dict[str, Any], tool_raw if isinstance(tool_raw, dict) else {})
        raw_config = tool.get("apseudo_lint", {})
    else:
        raw_config = data.get("apseudo_lint", data)

    if not isinstance(raw_config, dict):
        return LintConfig()

    raw = cast(dict[str, Any], raw_config)
    config = LintConfig()
    _set_scalar(config, raw, "max_nesting", int)
    _set_scalar(config, raw, "strict", bool)
    _set_scalar(config, raw, "fail_on_warning", bool)
    _set_scalar(config, raw, "require_process_declaration", bool)
    _set_scalar(config, raw, "require_verification_after_mutation", bool)
    _set_set(config, raw, "allowed_outcomes")
    _set_set(config, raw, "approved_outcomes", target="allowed_outcomes")
    _set_set(config, raw, "markdown_fence_languages")
    _set_set(config, raw, "file_extensions")
    _set_set(config, raw, "source_extensions", target="file_extensions")
    _set_set(config, raw, "markdown_extensions")
    _set_set(config, raw, "ignore_codes")
    _set_set(config, raw, "disabled_rules", target="ignore_codes")
    _set_list(config, raw, "exclude")
    _set_list(config, raw, "excluded_dirs", target="exclude")
    return config


def _set_scalar(
    config: LintConfig, raw: dict[str, Any], name: str, expected_type: type[object]
) -> None:
    value = raw.get(name)
    if isinstance(value, expected_type):
        setattr(config, name, value)


def _set_set(
    config: LintConfig, raw: dict[str, Any], name: str, *, target: str | None = None
) -> None:
    value = raw.get(name)
    if isinstance(value, list):
        items = cast(list[object], value)
        setattr(config, target or name, {str(item) for item in items})


def _set_list(
    config: LintConfig, raw: dict[str, Any], name: str, *, target: str | None = None
) -> None:
    value = raw.get(name)
    if isinstance(value, list):
        items = cast(list[object], value)
        setattr(config, target or name, [str(item) for item in items])
