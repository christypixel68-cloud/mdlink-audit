"""Install this action's source and audit the caller's checkout without a shell."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path


def parse_lines(value: str, name: str) -> list[str]:
    """Preserve embedded spaces and punctuation; omit empty, surrounding whitespace."""
    if "\0" in value:
        raise ValueError(f"{name} must not contain a NUL character")
    return [line.strip() for line in value.splitlines() if line.strip()]


def parse_boolean(value: str, name: str, *, default: bool | None) -> bool | None:
    """An empty input follows its default; only explicit true/false are accepted."""
    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{name} must be true, false, or empty")


def resolve_path(value: str, base: Path, name: str) -> Path:
    if "\0" in value or "\n" in value or "\r" in value:
        raise ValueError(f"{name} must be a single path without NUL or newline characters")
    path = Path(value.strip())
    return (path if path.is_absolute() else base / path).resolve()


def build_audit_command(env: Mapping[str, str], workspace: Path, python: str) -> list[str]:
    """Build one argv vector; no user input is interpreted as shell source or flags."""
    root = resolve_path(env.get("MDLINK_INPUT_ROOT", ".") or ".", workspace, "root")
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    command = [python, "-I", "-m", "mdlink_audit", "--format", "github", f"--root={root}"]
    config = env.get("MDLINK_INPUT_CONFIG", "").strip()
    if config:
        command.append(f"--config={resolve_path(config, workspace, 'config')}")
    for variable, name, option in (
        ("MDLINK_INPUT_EXCLUDE", "exclude", "--exclude"),
        ("MDLINK_INPUT_IGNORE_LINKS", "ignore-links", "--ignore-link"),
    ):
        command.extend(f"{option}={value}" for value in parse_lines(env.get(variable, ""), name))
    include_html = parse_boolean(
        env.get("MDLINK_INPUT_INCLUDE_HTML", ""), "include-html", default=None
    )
    if include_html is not None:
        command.append("--include-html" if include_html else "--no-include-html")
    if parse_boolean(env.get("MDLINK_INPUT_FAIL_ON_EMPTY", ""), "fail-on-empty", default=True):
        command.append("--fail-on-empty")
    paths = parse_lines(env.get("MDLINK_INPUT_PATHS", ""), "paths")
    if paths:
        command.extend(["--", *paths])
    return command


def build_install_command(action_path: Path, python: str) -> list[str]:
    """Install the selected action revision, not a package from the caller's checkout."""
    return [
        python,
        "-I",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        str(action_path),
    ]


def print_error(message: str) -> None:
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error::{escaped}")


def main(env: Mapping[str, str] | None = None) -> int:
    # This standalone bootstrap runs before pip checks the package's Python requirement.
    if sys.version_info < (3, 11):  # noqa: UP036
        print_error("mdlink-audit requires Python 3.11 or later; run actions/setup-python first")
        return 2
    env = os.environ if env is None else env
    try:
        for name in ("GITHUB_WORKSPACE", "MDLINK_ACTION_PATH"):
            if not env.get(name, "").strip():
                raise ValueError(f"{name} is required")
        workspace = resolve_path(env["GITHUB_WORKSPACE"], Path.cwd(), "GITHUB_WORKSPACE")
        action_path = resolve_path(env["MDLINK_ACTION_PATH"], Path.cwd(), "MDLINK_ACTION_PATH")
        if not workspace.is_dir():
            raise ValueError("GITHUB_WORKSPACE is not a directory; check out the repository first")
        if not (action_path / "pyproject.toml").is_file():
            raise ValueError("MDLINK_ACTION_PATH does not contain the action's pyproject.toml")
        command = build_audit_command(env, workspace, sys.executable)
        installed = subprocess.run(
            build_install_command(action_path, sys.executable), cwd=action_path, check=False
        )
        if installed.returncode:
            print_error("Could not install mdlink-audit from the selected action revision")
            return installed.returncode
        return subprocess.run(command, cwd=workspace, check=False).returncode
    except (ValueError, OSError, RuntimeError) as exc:
        print_error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
