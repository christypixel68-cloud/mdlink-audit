"""Small, explicit configuration surface for reproducible CLI runs."""

from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "build",
        "dist",
        ".tox",
        ".pytest_cache",
        ".ruff_cache",
    }
)


class AuditError(Exception):
    """An input, configuration, or filesystem error, distinct from a broken link."""


@dataclass(frozen=True)
class Config:
    exclude: tuple[str, ...] = ()
    ignore_links: tuple[str, ...] = ()
    include_html: bool = False


def load_config(path: Path, *, required: bool = False) -> Config:
    try:
        contents = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        if not required:
            return Config()
        raise AuditError(f"Configuration does not exist: {path}") from exc
    except (OSError, UnicodeError) as exc:
        raise AuditError(f"Cannot read configuration {path}: {exc}") from exc
    try:
        data = tomllib.loads(contents)
    except tomllib.TOMLDecodeError as exc:
        raise AuditError(f"Invalid TOML in {path}: {exc}") from exc
    unknown = set(data) - {"exclude", "ignore_links", "include_html"}
    if unknown:
        raise AuditError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
    for name in ("exclude", "ignore_links"):
        value = data.get(name, [])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise AuditError(f"Configuration '{name}' must be an array of strings")
    if not isinstance(data.get("include_html", False), bool):
        raise AuditError("Configuration 'include_html' must be a boolean")
    return Config(
        tuple(data.get("exclude", [])),
        tuple(data.get("ignore_links", [])),
        data.get("include_html", False),
    )


def matches(value: str, patterns: tuple[str, ...]) -> bool:
    """Case-sensitive fnmatch; **/ also matches a path at the repository root."""
    for pattern in patterns:
        if fnmatch.fnmatchcase(value, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatchcase(value, pattern[3:]):
            return True
    return False


def excluded(relative: str, config: Config, *, directory: bool = False) -> bool:
    if any(part in DEFAULT_IGNORED_DIRS for part in relative.split("/")):
        return True
    return matches(relative, config.exclude) or (
        directory and matches(relative.rstrip("/") + "/", config.exclude)
    )
