"""Audit existing local Git checkouts and record reproducible evidence; never fetch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import mdlink_audit
from mdlink_audit.checker import Auditor, collect_files
from mdlink_audit.config import DEFAULT_IGNORED_DIRS, AuditError, Config


def git(root: Path, *args: str) -> str:
    """Read Git metadata with hooks and filesystem-monitor commands disabled."""
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    if result.returncode:
        raise AuditError(f"Cannot read Git metadata for {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def file_hashes(root: Path, paths: list[Path]) -> list[dict[str, str]]:
    return [
        {
            "file": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(paths, key=lambda path: path.relative_to(root).as_posix())
    ]


def digest_manifest(manifest: list[dict[str, str]]) -> str:
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def audit_checkout(checkout: Path, scopes: list[str], *, include_html: bool = False) -> dict:
    root = checkout.resolve()
    git_root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    if root != git_root:
        raise AuditError(f"Use the Git checkout root, not a subdirectory: {root}")
    revision = git(root, "rev-parse", "HEAD")
    status_before = git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    selected = []
    for scope in scopes:
        path = Path(scope)
        if path.is_absolute():
            raise AuditError(f"Scope must be relative to each checkout: {scope}")
        selected.append(root / path)
    config = Config(include_html=include_html)
    files = collect_files(root, selected, config)
    before = file_hashes(root, files)
    report = Auditor(root, config).run(files)
    after = file_hashes(root, files)
    status_after = git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    if (
        before != after
        or status_before != status_after
        or revision != git(root, "rev-parse", "HEAD")
    ):
        raise AuditError(f"Checkout changed during the audit; rerun on a stable snapshot: {root}")
    return {
        "checkout": root.as_posix(),
        "commit": revision,
        "worktree_clean": not status_after,
        "scope": scopes,
        "markdown_manifest_sha256": digest_manifest(after),
        "markdown_files": after,
        "exit_code": 1 if report.issues else 0,
        "report": report.to_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkouts", nargs="+", type=Path, help="Existing local Git checkout roots")
    parser.add_argument(
        "--scope",
        action="append",
        help="Relative file/directory, repeatable; default: whole checkout",
    )
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout")
    parser.add_argument(
        "--include-html",
        action="store_true",
        help="Also audit supported static HTML links and IDs embedded in Markdown",
    )
    args = parser.parse_args(argv)
    if args.output and any(
        args.output.resolve().is_relative_to(checkout.resolve()) for checkout in args.checkouts
    ):
        parser.error("--output must be outside every audited checkout")
    scopes = args.scope or ["."]
    package_root = Path(mdlink_audit.__file__).resolve().parent
    sources = file_hashes(package_root, list(package_root.rglob("*.py")))
    body = {
        "corpus_schema_version": 1,
        "tool": {
            "name": "mdlink-audit",
            "version": mdlink_audit.__version__,
            "source_sha256": digest_manifest(sources),
            "source_files": sources,
            "corpus_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "markdown_it_py": version("markdown-it-py"),
        },
        "configuration": {
            "policy": "built-in defaults; checkout configuration files are not loaded",
            "ignored_directory_names": sorted(DEFAULT_IGNORED_DIRS),
            "exclude": [],
            "ignore_links": [],
            "include_html": args.include_html,
        },
        "checkouts": [],
    }
    exit_code = 0
    for checkout in args.checkouts:
        try:
            result = audit_checkout(checkout, scopes, include_html=args.include_html)
        except (AuditError, OSError, RuntimeError) as exc:
            result = {"checkout": checkout.resolve().as_posix(), "error": str(exc), "exit_code": 2}
        body["checkouts"].append(result)
        exit_code = max(exit_code, result["exit_code"])
    payload = json.dumps(body, ensure_ascii=False, indent=2) + "\n"
    try:
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
            sys.stdout.write(payload)
    except OSError as exc:
        print(f"audit_corpus: {exc}", file=sys.stderr)
        return 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
