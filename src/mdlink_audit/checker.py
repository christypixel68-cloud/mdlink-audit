"""Resolve local links without network requests or repository code execution."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import asdict, dataclass, field
from difflib import get_close_matches
from pathlib import Path
from urllib.parse import SplitResult, quote, unquote, urlsplit

from .config import AuditError, Config, excluded, matches
from .parser import Link, ParsedDocument, parse_markdown

MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


@dataclass(frozen=True)
class Issue:
    file: str
    line: int
    target: str
    code: str
    message: str
    suggestion: str | None = None


@dataclass
class Report:
    root: str
    files_scanned: int = 0
    links_checked: int = 0
    links_skipped: int = 0
    skipped: dict[str, int] = field(default_factory=lambda: {"external": 0, "ignored": 0})
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "root": self.root,
            "summary": {
                "files_scanned": self.files_scanned,
                "links_checked": self.links_checked,
                "links_skipped": self.links_skipped,
                "issues": len(self.issues),
            },
            "skipped": self.skipped,
            "issues": [asdict(issue) for issue in self.issues],
        }


def discover_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


def _inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root)
    except (OSError, RuntimeError):
        return False


def _linked_directory(path: Path) -> bool:
    """Do not recursively follow symlinks or Windows directory junctions."""
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise AuditError(f"Cannot inspect directory {path}: {exc}") from exc
    return stat.S_ISLNK(metadata.st_mode) or (
        getattr(metadata, "st_reparse_tag", 0) == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", -1)
    )


def collect_files(root: Path, paths: list[Path], config: Config) -> list[Path]:
    files: set[Path] = set()

    def walk_error(error: OSError) -> None:
        raise AuditError(f"Cannot scan directory: {error}") from error

    for supplied in paths:
        path = Path(os.path.abspath(supplied))
        if not path.is_relative_to(root) or not _inside(path, root):
            raise AuditError(f"Input is outside the repository root: {supplied}")
        if not path.exists():
            raise AuditError(f"Input does not exist: {supplied}")
        relative = path.relative_to(root).as_posix()
        if excluded(relative, config, directory=path.is_dir()):
            continue
        if path.is_file():
            if path.suffix.lower() not in MARKDOWN_SUFFIXES:
                raise AuditError(f"Input is not a Markdown file (.md or .markdown): {supplied}")
            files.add(path)
            continue
        if not path.is_dir():
            raise AuditError(f"Input is not a regular file or directory: {supplied}")
        for directory, dirs, names in os.walk(path, followlinks=False, onerror=walk_error):
            parent = Path(directory)
            dirs[:] = sorted(
                name
                for name in dirs
                if not _linked_directory(parent / name)
                and _inside(parent / name, root)
                and not excluded(
                    (parent / name).relative_to(root).as_posix(), config, directory=True
                )
            )
            for name in sorted(names):
                file = parent / name
                if file.suffix.lower() in MARKDOWN_SUFFIXES and not excluded(
                    file.relative_to(root).as_posix(), config
                ):
                    if not _inside(file, root):
                        raise AuditError(
                            f"Markdown source resolves outside the repository root: {file}"
                        )
                    if not file.is_file():
                        raise AuditError(f"Markdown source is not a regular file: {file}")
                    files.add(file)
    return sorted(files, key=lambda file: file.relative_to(root).as_posix())


def _lexical_target(source: Path, root: Path, url_path: str) -> Path | None:
    parts = [] if url_path.startswith("/") else list(source.parent.relative_to(root).parts)
    for part in url_path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return root.joinpath(*parts)


class Auditor:
    def __init__(self, root: Path, config: Config = Config()) -> None:
        self.root = root.resolve()
        self.config = config
        self.documents: dict[Path, ParsedDocument] = {}
        self.directory_names: dict[Path, set[str]] = {}

    def _read(self, file: Path) -> ParsedDocument:
        if file not in self.documents:
            if not _inside(file, self.root):
                raise AuditError(f"Refusing to read outside the repository root: {file}")
            try:
                self.documents[file] = parse_markdown(
                    file.read_text(encoding="utf-8-sig"), include_html=self.config.include_html
                )
            except (OSError, UnicodeError) as exc:
                raise AuditError(f"Cannot read Markdown file {file}: {exc}") from exc
        return self.documents[file]

    def _path_status(self, target: Path) -> tuple[Path, str | None]:
        """Detect spelling differences even on case-insensitive filesystems."""
        current = self.root
        wrong_case = False
        for part in target.relative_to(self.root).parts:
            if not _inside(current, self.root):
                return current, "outside_root"
            if not current.is_dir():
                return target, "missing_file"
            if current not in self.directory_names:
                try:
                    self.directory_names[current] = {entry.name for entry in current.iterdir()}
                except OSError as exc:
                    raise AuditError(f"Cannot inspect directory {current}: {exc}") from exc
            names = self.directory_names[current]
            if part in names:
                current = current / part
            else:
                similar = sorted(name for name in names if name.casefold() == part.casefold())
                if len(similar) != 1:
                    return target, "missing_file"
                current = current / similar[0]
                wrong_case = True
        if not _inside(current, self.root):
            return current, "outside_root"
        if not current.exists():
            return current, "missing_file"
        return current, "case_mismatch" if wrong_case else None

    def _replacement_url(self, actual: Path, source: Path, url: SplitResult) -> str:
        if url.path.startswith("/"):
            path = "/" + actual.relative_to(self.root).as_posix()
        else:
            path = Path(os.path.relpath(actual, source.parent)).as_posix()
        if url.path.endswith("/") and actual.is_dir():
            path += "/"
        return url._replace(path=quote(path, safe="/")).geturl()

    def _suggest_path(self, target: Path, source: Path, url: SplitResult) -> str | None:
        parent, status = self._path_status(target.parent)
        if status not in {None, "case_mismatch"} or not parent.is_dir():
            return None
        if parent not in self.directory_names:
            try:
                self.directory_names[parent] = {entry.name for entry in parent.iterdir()}
            except OSError:
                return None
        candidates = get_close_matches(
            target.name, sorted(self.directory_names[parent]), n=3, cutoff=0.72
        )
        for name in candidates:
            candidate = parent / name
            if _inside(candidate, self.root) and candidate.is_file():
                return self._replacement_url(candidate, source, url)
        return None

    def _check_link(self, source: Path, link: Link) -> tuple[str, str, str | None] | None:
        try:
            url = urlsplit(link.target)
            url_path = unquote(url.path, errors="strict")
            fragment = unquote(url.fragment, errors="strict")
        except (ValueError, UnicodeError):
            return "invalid_target", "Link contains an invalid URL or UTF-8 escape", None
        if (
            "\\" in url_path
            or "\x00" in url_path
            or any(re.match(r"^[a-zA-Z]:", part) for part in url_path.split("/"))
        ):
            return (
                "invalid_target",
                "Local links must use repository paths with forward slashes",
                None,
            )
        target = source if not url_path else _lexical_target(source, self.root, url_path)
        if target is None:
            return "outside_root", "Link escapes the repository root", None
        actual, code = self._path_status(target)
        if code == "outside_root":
            return code, "Link resolves outside the repository root", None
        if code == "missing_file":
            return (
                code,
                f"Target does not exist: {target.relative_to(self.root).as_posix()}",
                self._suggest_path(target, source, url),
            )
        if code == "case_mismatch":
            return (
                code,
                f"Path casing differs; on disk: {actual.relative_to(self.root).as_posix()}",
                self._replacement_url(actual, source, url),
            )
        if url_path.endswith("/") and not actual.is_dir():
            return "not_directory", "A path ending in '/' must refer to a directory", None
        # GitHub renders a directory's README, but this version only checks
        # directory existence. It does not invent site-generator routing rules.
        if fragment and actual.is_file() and actual.suffix.lower() in MARKDOWN_SUFFIXES:
            anchors = self._read(actual).anchors
            if fragment not in anchors:
                closest = get_close_matches(fragment, sorted(anchors), n=1, cutoff=0.6)
                suggestion = (
                    url._replace(fragment=quote(closest[0], safe="-_")).geturl()
                    if closest
                    else None
                )
                return (
                    "missing_anchor",
                    f"Heading or custom anchor '#{fragment}' does not exist",
                    suggestion,
                )
        return None

    def run(self, paths: list[Path] | None = None) -> Report:
        if not self.root.is_dir():
            raise AuditError(f"Repository root is not a directory: {self.root}")
        self.documents.clear()
        self.directory_names.clear()
        report = Report(root=self.root.as_posix())
        files = collect_files(self.root, paths if paths is not None else [self.root], self.config)
        report.files_scanned = len(files)
        for source in files:
            document = self._read(source)
            for link in document.links:
                if matches(link.target, self.config.ignore_links) or matches(
                    unquote(link.target), self.config.ignore_links
                ):
                    report.links_skipped += 1
                    report.skipped["ignored"] += 1
                    continue
                if SCHEME.match(link.target) or link.target.startswith("//"):
                    report.links_skipped += 1
                    report.skipped["external"] += 1
                    continue
                report.links_checked += 1
                problem = self._check_link(source, link)
                if problem:
                    code, message, suggestion = problem
                    report.issues.append(
                        Issue(
                            source.relative_to(self.root).as_posix(),
                            link.line,
                            link.target,
                            code,
                            message,
                            suggestion,
                        )
                    )
        report.issues.sort(key=lambda issue: (issue.file, issue.line, issue.target, issue.code))
        return report
