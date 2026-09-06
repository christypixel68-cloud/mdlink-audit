import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mdlink_audit.checker import Issue
from mdlink_audit.cli import github_annotation


def run_cli(repo, *args):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "mdlink_audit", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_cli_json_reports_broken_file_with_exit_one(tmp_path):
    (tmp_path / "README.md").write_text("# Hello\n\n[bad](缺失.md)", encoding="utf-8")
    result = run_cli(tmp_path, "--format", "json")
    assert result.returncode == 1
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["issues"][0]["code"] == "missing_file"
    assert report["issues"][0]["line"] == 3
    assert "缺失.md" in report["issues"][0]["message"]


def test_cli_success_and_relative_explicit_inputs(tmp_path):
    (tmp_path / "README.md").write_text("# Hello\n[self](#hello)", encoding="utf-8")
    result = run_cli(tmp_path, "README.md", "--fail-on-empty")
    assert result.returncode == 0
    assert "1 local links checked" in result.stdout


@pytest.mark.parametrize("args", [[], ["--fail-on-empty"]])
def test_cli_empty_behavior(tmp_path, args):
    result = run_cli(tmp_path, "--format", "json", *args)
    assert result.returncode == (2 if args else 0)
    body = json.loads(result.stdout)
    assert ("error" in body) == bool(args)


def test_cli_invalid_root_returns_json_error(tmp_path):
    result = run_cli(tmp_path, "--root", "absent", "--format", "json")
    assert result.returncode == 2
    assert "not a directory" in json.loads(result.stdout)["error"]


def test_cli_config_and_flags_are_additive(tmp_path):
    (tmp_path / "README.md").write_text("[a](first.md)\n[b](second.md)", encoding="utf-8")
    (tmp_path / ".mdlink-audit.toml").write_text('ignore_links = ["first.md"]', encoding="utf-8")
    result = run_cli(tmp_path, "--ignore-link", "second.md", "--format", "json")
    assert result.returncode == 0
    assert json.loads(result.stdout)["skipped"]["ignored"] == 2


def test_cli_exclude_applies_to_selected_files(tmp_path):
    (tmp_path / "README.md").write_text("[a](missing.md)", encoding="utf-8")
    result = run_cli(tmp_path, "--exclude", "**/README.md")
    assert result.returncode == 0


def test_cli_bad_config_returns_error_not_traceback(tmp_path):
    (tmp_path / ".mdlink-audit.toml").write_text("exclude = false", encoding="utf-8")
    result = run_cli(tmp_path)
    assert result.returncode == 2
    assert "array of strings" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_explicit_config_not_found(tmp_path):
    result = run_cli(tmp_path, "--config", "missing.toml")
    assert result.returncode == 2
    assert "does not exist" in result.stderr


def test_cli_github_output(tmp_path):
    (tmp_path / "README.md").write_text("[a](missing.md)", encoding="utf-8")
    result = run_cli(tmp_path, "--format", "github")
    assert result.returncode == 1
    assert "::error file=README.md,line=1::[missing_file]" in result.stdout


def test_annotation_data_cannot_inject_workflow_commands():
    issue = Issue(
        "docs/a,b:%.md\nname", 4, "target\n::warning::oops", "missing_file", "bad\r\nfile"
    )
    annotation = github_annotation(issue)
    assert "\n" not in annotation and "\r" not in annotation
    assert "a%2Cb%3A%25.md%0Aname" in annotation
    assert "target%0A::warning::oops" in annotation


def test_cli_nested_working_directory_detects_git_root(tmp_path):
    (tmp_path / ".git").mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (tmp_path / "README.md").write_text("# Home", encoding="utf-8")
    (docs / "guide.md").write_text("[home](/README.md#home)", encoding="utf-8")
    result = run_cli(docs, "guide.md", "--format", "json")
    assert result.returncode == 0
    assert Path(json.loads(result.stdout)["root"]) == tmp_path.resolve()


def test_cli_help_and_version(tmp_path):
    assert "External URLs are skipped" in run_cli(tmp_path, "--help").stdout
    assert run_cli(tmp_path, "--version").returncode == 0
