"""Filesystem/URL boundaries that commonly differ between local and CI runs."""

from __future__ import annotations

import os
import socket
import subprocess
import urllib.request
from pathlib import Path

import pytest

from mdlink_audit.checker import Auditor
from mdlink_audit.config import AuditError, Config, load_config, matches


def _write(root: Path, relative: str, text: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _symlink(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks are unavailable in this environment: {exc}")


def test_unicode_spaces_query_and_fragment_are_resolved_separately(tmp_path):
    _write(tmp_path, "文档/使用 指南.md", "# 中文 标题\n")
    source = _write(
        tmp_path,
        "README.md",
        "[guide](<文档/使用 指南.md?raw=true#中文-标题>)\n"
        "[encoded](%E6%96%87%E6%A1%A3/%E4%BD%BF%E7%94%A8%20%E6%8C%87%E5%8D%97.md"
        "?download=1#%E4%B8%AD%E6%96%87-%E6%A0%87%E9%A2%98)\n",
    )
    report = Auditor(tmp_path).run([source])
    assert report.links_checked == 2
    assert report.issues == []


def test_percent_decoding_happens_exactly_once_for_path_and_anchor(tmp_path):
    _write(tmp_path, "literal%20name.md", '<a name="percent%20anchor"></a>\n')
    _write(tmp_path, "hash#file.md", "# Works\n")
    source = _write(
        tmp_path,
        "README.md",
        "[percent](literal%2520name.md#percent%2520anchor)\n[hash](hash%23file.md#works)\n",
    )
    assert Auditor(tmp_path).run([source]).issues == []


def test_double_encoded_path_does_not_accidentally_match_a_space(tmp_path):
    _write(tmp_path, "a b.md", "# Works\n")
    source = _write(tmp_path, "README.md", "[bad](a%2520b.md)\n")
    assert [issue.code for issue in Auditor(tmp_path).run([source]).issues] == ["missing_file"]


def test_empty_path_and_query_only_links_resolve_against_current_document(tmp_path):
    source = _write(
        tmp_path,
        "docs/guide.md",
        "# Local\n[anchor](#local)\n[query](?raw=1#local)\n[self](./guide.md#local)\n[empty]()\n",
    )
    report = Auditor(tmp_path).run([source])
    assert report.links_checked == 4
    assert report.issues == []


def test_root_relative_paths_resolve_under_repository_not_filesystem_root(tmp_path):
    _write(tmp_path, "README.md", "# Root\n")
    source = _write(tmp_path, "docs/guide.md", "[root](/README.md#root)\n")
    assert Auditor(tmp_path).run([source]).issues == []


def test_directory_and_non_markdown_fragments_check_only_existence(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "directory.md").mkdir()
    _write(tmp_path, "manual.pdf", "not actually a PDF; existence is sufficient")
    source = _write(
        tmp_path,
        "README.md",
        "[directory](docs/#unverified)\n"
        "[md-directory](directory.md#unverified)\n"
        "[PDF](manual.pdf#page=9)\n",
    )
    assert Auditor(tmp_path).run([source]).issues == []


def test_file_target_with_trailing_slash_is_not_a_directory(tmp_path):
    _write(tmp_path, "guide.md", "# Guide\n")
    source = _write(tmp_path, "README.md", "[bad](guide.md/)\n")
    assert [issue.code for issue in Auditor(tmp_path).run([source]).issues] == ["not_directory"]


def test_encoded_parent_directory_escape_is_reported(tmp_path):
    source = _write(tmp_path, "README.md", "[outside](%2e%2e/secret.md)\n")
    assert [issue.code for issue in Auditor(tmp_path).run([source]).issues] == ["outside_root"]


@pytest.mark.parametrize("target", ["bad%00.md", "docs/%5Csecret.md", "bad%FF.md"])
def test_invalid_local_path_encodings_produce_issues_instead_of_crashing(tmp_path, target):
    source = _write(tmp_path, "README.md", f"[bad]({target})\n")
    assert [issue.code for issue in Auditor(tmp_path).run([source]).issues] == ["invalid_target"]


@pytest.mark.skipif(os.name != "nt", reason="Drive-reset behavior is specific to WindowsPath")
@pytest.mark.parametrize("target", ["/Z:/file.md", "docs/Z:/file.md", "/%5A:/file.md"])
def test_windows_drive_segments_do_not_escape_or_crash_path_resolution(tmp_path, target):
    source = _write(tmp_path, "README.md", f"[bad]({target})\n")
    report = Auditor(tmp_path).run([source])
    assert [issue.code for issue in report.issues] == ["invalid_target"]


def test_each_path_component_is_case_checked_on_every_platform(tmp_path):
    _write(tmp_path, "Docs/Guide.md", "# Start\n")
    source = _write(tmp_path, "README.md", "[bad](docs/guide.md#start)\n")
    (issue,) = Auditor(tmp_path).run([source]).issues
    assert issue.code == "case_mismatch"
    assert "Docs/Guide.md" in issue.message


def test_external_links_never_require_network_requests(tmp_path, monkeypatch):
    def network_forbidden(*args, **kwargs):
        raise AssertionError("Auditor attempted network access")

    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", network_forbidden)
    source = _write(
        tmp_path,
        "README.md",
        "[https](https://example.invalid/guide.md#missing)\n"
        "[http](http://example.invalid/)\n"
        "[protocol-relative](//example.invalid/guide.md)\n"
        "[email](mailto:user@example.invalid)\n"
        "[custom](custom-protocol:example)\n",
    )
    report = Auditor(tmp_path).run([source])
    assert report.links_checked == 0
    assert report.links_skipped == 5
    assert report.skipped["external"] == 5
    assert report.issues == []


def test_internal_file_and_directory_symlink_targets_are_checked(tmp_path):
    target = _write(tmp_path, "docs/guide.md", "# Existing\n")
    _symlink(tmp_path / "guide-alias.md", target)
    _symlink(tmp_path / "docs-alias", tmp_path / "docs", directory=True)
    source = _write(
        tmp_path,
        "README.md",
        "[file](guide-alias.md#existing)\n"
        "[directory](docs-alias/guide.md#existing)\n"
        "[broken-anchor](guide-alias.md#missing)\n",
    )
    report = Auditor(tmp_path).run([source])
    assert [issue.code for issue in report.issues] == ["missing_anchor"]
    assert report.issues[0].line == 3


def test_symlink_targets_outside_root_are_reported_without_reading_them(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = _write(tmp_path, "outside/secret.md", "# Secret\n")
    _symlink(root / "escape.md", outside)
    _symlink(root / "escape-dir", outside.parent, directory=True)
    source = _write(
        root,
        "README.md",
        "[file](escape.md#secret)\n[dir](escape-dir/secret.md#secret)\n",
    )
    auditor = Auditor(root)
    report = auditor.run([source])
    assert [issue.code for issue in report.issues] == ["outside_root", "outside_root"]
    assert set(auditor.documents) == {source}


def test_outside_symlink_source_is_an_input_error(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = _write(tmp_path, "outside.md", "# Outside\n")
    alias = root / "outside.md"
    _symlink(alias, outside)
    with pytest.raises(AuditError, match="outside"):
        Auditor(root).run([alias])


def test_dangling_internal_symlink_is_missing_file(tmp_path):
    _symlink(tmp_path / "dangling.md", tmp_path / "absent.md")
    source = _write(tmp_path, "README.md", "[bad](dangling.md)\n")
    assert [issue.code for issue in Auditor(tmp_path).run([source]).issues] == ["missing_file"]


def test_symlinked_directories_are_not_recursively_scanned(tmp_path):
    _write(tmp_path, "docs/guide.md", "# Guide\n")
    _symlink(tmp_path / "docs" / "loop", tmp_path, directory=True)
    report = Auditor(tmp_path).run()
    assert report.files_scanned == 1
    assert report.issues == []


def test_ignore_patterns_match_unicode_decoded_targets(tmp_path):
    source = _write(tmp_path, "README.md", "[generated](<文档/生成 文件.md#标题>)\n")
    report = Auditor(tmp_path, Config(ignore_links=("文档/*",))).run([source])
    assert report.links_checked == 0
    assert report.skipped["ignored"] == 1
    assert report.issues == []


def test_excluding_a_source_does_not_exempt_links_pointing_to_it(tmp_path):
    _write(tmp_path, "generated/output.md", "# Existing\n[bad](absent.md)\n")
    _write(tmp_path, "README.md", "[bad](generated/output.md#missing)\n")
    report = Auditor(tmp_path, Config(exclude=("generated/",))).run()
    assert report.files_scanned == 1
    assert [issue.code for issue in report.issues] == ["missing_anchor"]


def test_pattern_matching_is_case_sensitive_and_double_star_covers_root():
    assert matches("README.md", ("**/*.md",))
    assert matches("docs/README.md", ("**/*.md",))
    assert not matches("Docs/a.md", ("docs/*",))


def test_bom_encoded_configuration_and_markdown_are_supported(tmp_path):
    config_path = tmp_path / ".mdlink-audit.toml"
    config_path.write_text('ignore_links = ["generated/*"]\n', encoding="utf-8-sig")
    source = tmp_path / "README.md"
    source.write_text(
        "# Start\n[self](#start)\n[generated](generated/a.md)\n", encoding="utf-8-sig"
    )
    report = Auditor(tmp_path, load_config(config_path)).run([source])
    assert report.links_checked == 1
    assert report.links_skipped == 1
    assert report.issues == []


def _junction(link: Path, target: Path) -> None:
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "New-Item -ItemType Junction -Path $env:MDLINK_TEST_LINK "
            "-Target $env:MDLINK_TEST_TARGET -ErrorAction Stop | Out-Null",
        ],
        env={**os.environ, "MDLINK_TEST_LINK": str(link), "MDLINK_TEST_TARGET": str(target)},
        capture_output=True,
        timeout=20,
    )
    if result.returncode:
        pytest.skip("This Windows host cannot create directory junctions")


@pytest.mark.skipif(os.name != "nt", reason="Windows directory junction behavior")
def test_windows_directory_junction_loop_not_recursively_scanned(tmp_path):
    _write(tmp_path, "docs/guide.md", "# Guide\n")
    _junction(tmp_path / "docs" / "loop", tmp_path)
    report = Auditor(tmp_path).run()
    assert report.files_scanned == 1
    assert not report.issues


@pytest.mark.skipif(os.name != "nt", reason="Windows directory junction behavior")
def test_windows_directory_junction_cannot_read_outside_root(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = _write(tmp_path, "outside/secret.md", "# Secret\n")
    _junction(root / "escape", outside.parent)
    source = _write(root, "README.md", "[outside](escape/secret.md#secret)\n")
    auditor = Auditor(root)
    report = auditor.run([source])
    assert [issue.code for issue in report.issues] == ["outside_root"]
    assert set(auditor.documents) == {source}
