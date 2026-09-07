"""Command-line entry point and stable machine-readable output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .checker import Auditor, Issue, Report, discover_root
from .config import AuditError, Config, load_config


def annotation_escape(value: str, *, property_value: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def github_annotation(issue: Issue) -> str:
    path = annotation_escape(issue.file, property_value=True)
    detail = f"[{issue.code}] {issue.message} (target: {issue.target})"
    if issue.suggestion:
        detail += f"; did you mean: {issue.suggestion}"
    message = annotation_escape(detail)
    return f"::error file={path},line={issue.line}::{message}"


def print_report(report: Report, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return
    for issue in report.issues:
        if output_format == "github":
            print(github_annotation(issue))
        else:
            # JSON quoting keeps control characters from forging additional lines.
            target = json.dumps(issue.target, ensure_ascii=False)
            message = issue.message.replace("\r", "\\r").replace("\n", "\\n")
            file = issue.file.replace("\r", "\\r").replace("\n", "\\n")
            print(f"{file}:{issue.line}: {issue.code}: {message} ({target})")
            if issue.suggestion:
                print(f"  suggestion: {json.dumps(issue.suggestion, ensure_ascii=False)}")
    state = "FAIL" if report.issues else "PASS"
    print(
        f"{state}: {report.files_scanned} Markdown files, "
        f"{report.links_checked} local links checked, "
        f"{report.links_skipped} links skipped, {len(report.issues)} issues."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mdlink-audit",
        description="Check local Markdown links offline. External URLs are skipped, never fetched.",
    )
    parser.add_argument("paths", nargs="*", help="Markdown files or directories (default: root)")
    parser.add_argument("--root", type=Path, help="Repository root (default: nearest .git or cwd)")
    parser.add_argument("--format", choices=("text", "json", "github"), default="text")
    parser.add_argument(
        "--config", type=Path, help="TOML config (default: root/.mdlink-audit.toml)"
    )
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    parser.add_argument("--ignore-link", action="append", default=[], metavar="GLOB")
    parser.add_argument(
        "--include-html",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Also check static HTML href/src and IDs in Markdown (default: config or off)",
    )
    parser.add_argument(
        "--fail-on-empty", action="store_true", help="Exit 2 if no Markdown is scanned"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    try:
        root = args.root.resolve() if args.root else discover_root(Path.cwd())
        config = load_config(
            args.config if args.config else root / ".mdlink-audit.toml",
            required=args.config is not None,
        )
        config = Config(
            exclude=config.exclude + tuple(args.exclude),
            ignore_links=config.ignore_links + tuple(args.ignore_link),
            include_html=config.include_html if args.include_html is None else args.include_html,
        )
        paths = [Path(path) for path in args.paths] if args.paths else None
        report = Auditor(root, config).run(paths)
        if args.fail_on_empty and report.files_scanned == 0:
            raise AuditError("No Markdown files were selected")
    except (AuditError, OSError, RuntimeError) as exc:
        if args.format == "json":
            print(json.dumps({"schema_version": 1, "error": str(exc)}, ensure_ascii=False))
        elif args.format == "github":
            print(f"::error::{annotation_escape(str(exc))}")
        else:
            print(f"mdlink-audit: {exc}", file=sys.stderr)
        return 2
    print_report(report, args.format)
    return 1 if report.issues else 0
