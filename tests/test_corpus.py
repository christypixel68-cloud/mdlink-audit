import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_corpus.py"


def git(repo, *args):
    return subprocess.run(
        ["git", "-c", "core.hooksPath=", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
    ).stdout.strip()


@pytest.fixture
def checkout(tmp_path):
    repo = tmp_path / "checkout"
    repo.mkdir()
    git(repo, "init")
    (repo / "README.md").write_text("# Hello\n[self](#hello)\n", encoding="utf-8")
    # The evaluation must not hide findings through a checked-out repository's config.
    (repo / ".mdlink-audit.toml").write_text('ignore_links = ["*"]\n', encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "Seed",
    )
    return repo


def run_corpus(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return result, json.loads(result.stdout)


def test_corpus_records_commit_clean_state_and_markdown_fingerprint(checkout):
    result, body = run_corpus(checkout)
    assert result.returncode == 0
    snapshot = body["checkouts"][0]
    assert snapshot["commit"] == git(checkout, "rev-parse", "HEAD")
    assert snapshot["worktree_clean"] is True
    assert snapshot["report"]["summary"]["links_checked"] == 1
    assert snapshot["markdown_files"] == [
        {
            "file": "README.md",
            "sha256": hashlib.sha256((checkout / "README.md").read_bytes()).hexdigest(),
        }
    ]
    assert len(body["tool"]["source_sha256"]) == 64
    assert len(body["tool"]["corpus_script_sha256"]) == 64
    assert body["configuration"]["include_html"] is False
    _, repeated = run_corpus(checkout)
    assert repeated == body


def test_corpus_reports_modified_worktree_and_does_not_load_checkout_config(checkout):
    (checkout / "README.md").write_text("[bad](missing.md)", encoding="utf-8")
    result, body = run_corpus(checkout)
    assert result.returncode == 1
    snapshot = body["checkouts"][0]
    assert snapshot["worktree_clean"] is False
    assert snapshot["report"]["issues"][0]["code"] == "missing_file"
    assert snapshot["report"]["skipped"]["ignored"] == 0


def test_corpus_html_is_opt_in_and_configuration_is_recorded(checkout):
    (checkout / "README.md").write_text('<a href="missing.md">Missing</a>\n', encoding="utf-8")
    default, baseline = run_corpus(checkout)
    assert default.returncode == 0
    assert baseline["configuration"]["include_html"] is False
    assert baseline["checkouts"][0]["report"]["summary"]["links_checked"] == 0

    enabled, expanded = run_corpus(checkout, "--include-html")
    assert enabled.returncode == 1
    assert expanded["configuration"]["include_html"] is True
    issue = expanded["checkouts"][0]["report"]["issues"][0]
    assert (issue["code"], issue["target"]) == ("missing_file", "missing.md")
    assert (
        expanded["checkouts"][0]["markdown_manifest_sha256"]
        == baseline["checkouts"][0]["markdown_manifest_sha256"]
    )


def test_corpus_continues_after_invalid_checkout_and_returns_operational_error(checkout, tmp_path):
    result, body = run_corpus(tmp_path / "missing", checkout)
    assert result.returncode == 2
    assert "error" in body["checkouts"][0]
    assert body["checkouts"][1]["exit_code"] == 0


def test_corpus_scope_and_file_output(checkout, tmp_path):
    output = tmp_path / "audit.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(checkout),
            "--scope",
            "README.md",
            "--output",
            str(output),
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == b""
    assert json.loads(output.read_text(encoding="utf-8"))["checkouts"][0]["scope"] == ["README.md"]


def test_corpus_does_not_overwrite_files_in_audited_checkout(checkout):
    readme = checkout / "README.md"
    original = readme.read_bytes()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(checkout), "--output", str(readme)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "outside every audited checkout" in result.stderr
    assert readme.read_bytes() == original


@pytest.mark.parametrize("scope", ["../", "../outside.md"])
def test_corpus_rejects_scopes_outside_checkout(checkout, scope):
    result, body = run_corpus(checkout, "--scope", scope)
    assert result.returncode == 2
    assert "outside" in body["checkouts"][0]["error"]
