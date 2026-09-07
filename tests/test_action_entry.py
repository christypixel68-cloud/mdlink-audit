import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "action_entry", Path(__file__).resolve().parents[1] / "scripts" / "action_entry.py"
)
assert SPEC is not None and SPEC.loader is not None
action_entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(action_entry)


@pytest.fixture
def action_env(tmp_path):
    workspace = tmp_path / "caller repo 空格"
    workspace.mkdir()
    action_path = tmp_path / "downloaded action"
    action_path.mkdir()
    (action_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return {
        "GITHUB_WORKSPACE": str(workspace),
        "MDLINK_ACTION_PATH": str(action_path),
    }


def test_line_inputs_preserve_spaces_and_literal_shell_text():
    assert action_entry.parse_lines(
        " README.md\r\n\r\n docs/my guide.md \n$(touch marker).md\n'quoted'.md\n", "paths"
    ) == ["README.md", "docs/my guide.md", "$(touch marker).md", "'quoted'.md"]


@pytest.mark.parametrize("value", ["docs\0folder", "README.md\n\0"])
def test_line_inputs_reject_nul(value):
    with pytest.raises(ValueError, match="NUL"):
        action_entry.parse_lines(value, "paths")


@pytest.mark.parametrize(
    ("value", "default", "expected"),
    [("true", None, True), (" FALSE ", True, False), ("", None, None), ("\n", True, True)],
)
def test_boolean_inputs(value, default, expected):
    assert action_entry.parse_boolean(value, "include-html", default=default) is expected


@pytest.mark.parametrize("value", ["yes", "0", "1", "true\nfalse", "false; echo bad"])
def test_boolean_inputs_reject_ambiguous_values(value):
    with pytest.raises(ValueError, match="include-html must be true, false, or empty"):
        action_entry.parse_boolean(value, "include-html", default=None)


def test_default_command_scans_workspace_fails_on_empty_and_follows_config(tmp_path):
    command = action_entry.build_audit_command({}, tmp_path, "python")
    assert command == [
        "python",
        "-I",
        "-m",
        "mdlink_audit",
        "--format",
        "github",
        f"--root={tmp_path.resolve()}",
        "--fail-on-empty",
    ]


def test_paths_and_patterns_cannot_supply_options_or_shell_commands(tmp_path):
    command = action_entry.build_audit_command(
        {
            "MDLINK_INPUT_PATHS": "docs/my guide.md\n--format\njson\n$(touch marker).md",
            "MDLINK_INPUT_EXCLUDE": "--format\ngenerated docs/**",
            "MDLINK_INPUT_IGNORE_LINKS": "--config=other.toml\n$(echo bad)/*",
        },
        tmp_path,
        "python with spaces",
    )
    assert "--exclude=--format" in command
    assert "--exclude=generated docs/**" in command
    assert "--ignore-link=--config=other.toml" in command
    assert "--ignore-link=$(echo bad)/*" in command
    assert command[command.index("--") + 1 :] == [
        "docs/my guide.md",
        "--format",
        "json",
        "$(touch marker).md",
    ]
    assert command[0] == "python with spaces"


def test_relative_root_and_config_use_workspace_without_changing_paths(tmp_path):
    (tmp_path / "nested root").mkdir()
    command = action_entry.build_audit_command(
        {
            "MDLINK_INPUT_ROOT": "nested root",
            "MDLINK_INPUT_CONFIG": "config files/audit.toml",
            "MDLINK_INPUT_PATHS": "nested root/docs",
        },
        tmp_path,
        "python",
    )
    assert f"--root={tmp_path / 'nested root'}" in command
    assert f"--config={tmp_path / 'config files' / 'audit.toml'}" in command
    assert command[-2:] == ["--", "nested root/docs"]


def test_absolute_root_and_config_remain_absolute(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    command = action_entry.build_audit_command(
        {"MDLINK_INPUT_ROOT": str(tmp_path), "MDLINK_INPUT_CONFIG": str(tmp_path / "audit.toml")},
        workspace,
        "python",
    )
    assert f"--root={tmp_path}" in command
    assert f"--config={tmp_path / 'audit.toml'}" in command


@pytest.mark.parametrize(
    ("value", "flag"), [("true", "--include-html"), ("false", "--no-include-html")]
)
def test_explicit_html_overrides_and_empty_scan_opt_out(tmp_path, value, flag):
    command = action_entry.build_audit_command(
        {"MDLINK_INPUT_INCLUDE_HTML": value, "MDLINK_INPUT_FAIL_ON_EMPTY": "false"},
        tmp_path,
        "python",
    )
    assert flag in command
    assert "--fail-on-empty" not in command


@pytest.mark.parametrize("value", ["some\nother", "some\rother", "some\0other"])
def test_single_path_inputs_reject_newlines_and_nul(tmp_path, value):
    with pytest.raises(ValueError, match="single path"):
        action_entry.resolve_path(value, tmp_path, "root")


def test_install_and_audit_use_distinct_directories_and_preserve_exit_status(
    action_env, monkeypatch
):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0 if len(calls) == 1 else 1)

    monkeypatch.setattr(action_entry.subprocess, "run", fake_run)
    assert action_entry.main(action_env) == 1
    install, audit = calls
    assert install[0][-1] == action_env["MDLINK_ACTION_PATH"]
    assert install[0][1:5] == ["-I", "-m", "pip", "install"]
    assert install[1] == {"cwd": Path(action_env["MDLINK_ACTION_PATH"]), "check": False}
    assert audit[0][1:6] == ["-I", "-m", "mdlink_audit", "--format", "github"]
    assert audit[1] == {"cwd": Path(action_env["GITHUB_WORKSPACE"]), "check": False}


def test_install_failure_does_not_run_checker(action_env, monkeypatch, capsys):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=3)

    monkeypatch.setattr(action_entry.subprocess, "run", fake_run)
    assert action_entry.main(action_env) == 3
    assert len(calls) == 1
    assert "::error::Could not install" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MDLINK_INPUT_FAIL_ON_EMPTY", "off"),
        ("MDLINK_INPUT_INCLUDE_HTML", "yes"),
        ("MDLINK_INPUT_ROOT", "missing directory"),
        ("GITHUB_WORKSPACE", ""),
        ("MDLINK_ACTION_PATH", ""),
    ],
)
def test_invalid_configuration_fails_before_install(action_env, monkeypatch, capsys, name, value):
    action_env[name] = value

    def unexpected_run(*args, **kwargs):
        pytest.fail("Invalid action input must not start an installation")

    monkeypatch.setattr(action_entry.subprocess, "run", unexpected_run)
    assert action_entry.main(action_env) == 2
    assert capsys.readouterr().out.startswith("::error::")


def test_python_version_error_is_actionable(action_env, monkeypatch, capsys):
    monkeypatch.setattr(action_entry.sys, "version_info", (3, 10, 9))
    assert action_entry.main(action_env) == 2
    assert "actions/setup-python" in capsys.readouterr().out


def test_action_errors_cannot_inject_workflow_commands(capsys):
    action_entry.print_error("bad%\r\n::warning::forged")
    assert capsys.readouterr().out == "::error::bad%25%0D%0A::warning::forged\n"
