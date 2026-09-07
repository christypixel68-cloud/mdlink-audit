import json
import os
import subprocess
import sys

import pytest

from mdlink_audit.config import AuditError, load_config


def run_cli(root, *args):
    return subprocess.run(
        [sys.executable, "-m", "mdlink_audit", "--format", "json", *args],
        cwd=root,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_html_is_opt_in_and_reports_broken_image(tmp_path):
    (tmp_path / "README.md").write_text('<img src="missing.svg">\n', encoding="utf-8")
    default = run_cli(tmp_path)
    assert default.returncode == 0
    assert json.loads(default.stdout)["summary"]["links_checked"] == 0
    enabled = run_cli(tmp_path, "--include-html")
    assert enabled.returncode == 1
    (issue,) = json.loads(enabled.stdout)["issues"]
    assert (issue["code"], issue["target"], issue["line"]) == ("missing_file", "missing.svg", 1)


def test_html_config_and_explicit_cli_override(tmp_path):
    (tmp_path / "README.md").write_text('<a href="missing.md">bad</a>\n', encoding="utf-8")
    (tmp_path / ".mdlink-audit.toml").write_text("include_html = true\n", encoding="utf-8")
    assert run_cli(tmp_path).returncode == 1
    assert run_cli(tmp_path, "--no-include-html").returncode == 0
    (tmp_path / ".mdlink-audit.toml").write_text("include_html = false\n", encoding="utf-8")
    assert run_cli(tmp_path, "--include-html").returncode == 1


@pytest.mark.parametrize("value", ['"true"', "1", "[]", "{}"])
def test_html_config_requires_actual_boolean(tmp_path, value):
    config = tmp_path / ".mdlink-audit.toml"
    config.write_text(f"include_html = {value}\n", encoding="utf-8")
    with pytest.raises(AuditError, match="must be a boolean"):
        load_config(config)


def test_markdown_links_can_target_opt_in_html_ids_in_other_files(tmp_path):
    (tmp_path / "README.md").write_text("[section](guide.md#中文)\n", encoding="utf-8")
    (tmp_path / "guide.md").write_text('<section id="中文">text</section>\n', encoding="utf-8")
    assert run_cli(tmp_path, "README.md").returncode == 1
    assert run_cli(tmp_path, "--include-html", "README.md").returncode == 0


def test_html_links_obey_ignores_and_repository_boundary(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (tmp_path / "outside.md").write_text("# Private\n", encoding="utf-8")
    (root / "README.md").write_text(
        '<a href="../outside.md#private">outside</a>\n'
        '<img src="generated/image.svg">\n'
        '<a href="https://example.invalid/">external</a>\n',
        encoding="utf-8",
    )
    result = run_cli(root, "--include-html", "--ignore-link=generated/*")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert [issue["code"] for issue in report["issues"]] == ["outside_root"]
    assert report["skipped"] == {"ignored": 1, "external": 1}
