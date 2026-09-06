import pytest

from mdlink_audit.checker import Auditor, discover_root
from mdlink_audit.config import AuditError, Config, load_config


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text(
        "# Install\n\n## 中文安装\n\n## Install\n", encoding="utf-8"
    )
    return tmp_path


def check(repo, text, *, config=Config()):
    source = repo / "README.md"
    source.write_text(text, encoding="utf-8")
    return Auditor(repo, config).run([source])


def test_relative_root_and_cross_file_anchors(repo):
    report = check(
        repo,
        "# Intro\n[a](docs/guide.md#install)\n[b](/docs/guide.md#中文安装)\n"
        "[c](#intro)\n[d](docs/guide.md#install-1)\n[e](./docs/)\n",
    )
    assert not report.issues
    assert report.files_scanned == 1
    assert report.links_checked == 5


def test_parent_relative_links(repo):
    (repo / "README.md").write_text("# Home", encoding="utf-8")
    (repo / "docs" / "guide.md").write_text("[home](../README.md#home)", encoding="utf-8")
    assert not Auditor(repo).run().issues


@pytest.mark.parametrize(
    ("target", "code"),
    [
        ("missing.md", "missing_file"),
        ("docs/guide.md#typo", "missing_anchor"),
        ("docs/Guide.md", "case_mismatch"),
        ("Docs/guide.md", "case_mismatch"),
        ("../outside.md", "outside_root"),
        ("docs/../../outside.md", "outside_root"),
        ("docs/guide.md/", "not_directory"),
        ("docs/guide.md/child.md", "missing_file"),
        ("docs/%00bad.md", "invalid_target"),
        ("docs/%FFbad.md", "invalid_target"),
        ("docs%5Cguide.md", "invalid_target"),
    ],
)
def test_broken_links_have_specific_codes_and_source_lines(repo, target, code):
    report = check(repo, f"# Example\n\nSome text\n[link]({target})\n")
    assert len(report.issues) == 1
    issue = report.issues[0]
    assert (issue.code, issue.file, issue.line) == (code, "README.md", 4)


def test_non_markdown_fragments_and_query_strings(repo):
    (repo / "diagram.svg").write_text("<svg/>", encoding="utf-8")
    report = check(repo, "![svg](diagram.svg#view)\n[guide](docs/guide.md?raw=1#install)")
    assert not report.issues
    assert report.links_checked == 2


def test_external_links_skipped_without_network(repo, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("A network request was attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    report = check(
        repo,
        "[https](https://invalid.example)\n[http](http://invalid.example)\n"
        "[mail](mailto:x@example.com)\n[proto](//example.com/no.md)\n"
        "[ssh](ssh://example.com)\n",
    )
    assert not report.issues
    assert report.links_checked == 0
    assert report.skipped == {"external": 5, "ignored": 0}


def test_excludes_are_root_relative_and_do_not_hide_targets(repo):
    (repo / "docs" / "guide.md").write_text("# Install\n[bad](absent.md)", encoding="utf-8")
    (repo / "README.md").write_text("[guide](docs/guide.md#install)", encoding="utf-8")
    report = Auditor(repo, Config(exclude=("docs/**",))).run()
    assert report.files_scanned == 1
    assert not report.issues


def test_hidden_github_docs_scanned_but_dependency_directories_excluded(repo):
    for folder in (".github", "node_modules", ".venv", "docs/node_modules"):
        path = repo / folder
        path.mkdir(parents=True, exist_ok=True)
        (path / "README.md").write_text("[bad](missing.md)", encoding="utf-8")
    report = Auditor(repo).run()
    assert [issue.file for issue in report.issues] == [".github/README.md"]


def test_ignore_link_decoded_and_encoded_forms(repo):
    report = check(
        repo, "[one](不存在.md)\n[two](another.md)", config=Config(ignore_links=("不存在.md",))
    )
    assert report.skipped["ignored"] == 1
    assert report.links_checked == 1
    assert report.issues[0].target == "another.md"


def test_overlapping_inputs_are_deduplicated(repo):
    report = Auditor(repo).run([repo, repo / "docs", repo / "docs" / "guide.md"])
    assert report.files_scanned == 1


def test_empty_repository_has_valid_report(tmp_path):
    report = Auditor(tmp_path).run()
    assert report.files_scanned == 0
    assert report.to_dict()["summary"]["issues"] == 0


@pytest.mark.parametrize("filename", ["missing.md", "not-markdown.txt"])
def test_invalid_explicit_inputs_raise(repo, filename):
    if filename.endswith(".txt"):
        (repo / filename).write_text("x")
    with pytest.raises(AuditError):
        Auditor(repo).run([repo / filename])


def test_outside_input_rejected_even_if_it_exists(repo):
    with pytest.raises(AuditError, match="outside"):
        Auditor(repo).run([repo.parent])


def test_bad_utf8_is_operational_error(repo):
    (repo / "bad.md").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(AuditError, match="Cannot read"):
        Auditor(repo).run()


def test_utf8_bom_readable(repo):
    (repo / "README.md").write_text("# Intro\n[self](#intro)", encoding="utf-8-sig")
    assert not Auditor(repo).run().issues


def test_git_root_discovery_including_worktree_git_file(repo):
    (repo / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    assert discover_root(repo / "docs") == repo.resolve()


def test_non_git_root_defaults_to_start(repo):
    assert discover_root(repo / "docs") == (repo / "docs").resolve()


def test_configuration_loads_arrays(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('exclude = ["generated/**"]\nignore_links = ["/api/*"]', encoding="utf-8")
    assert load_config(path) == Config(("generated/**",), ("/api/*",))


@pytest.mark.parametrize("content", ['exclude = "docs"', "unknown = []", "exclude = [1]", "[oops"])
def test_configuration_rejects_mistakes(tmp_path, content):
    path = tmp_path / "config.toml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(AuditError):
        load_config(path)


def test_explicit_missing_config_fails(tmp_path):
    path = tmp_path / "missing.toml"
    assert load_config(path) == Config()
    with pytest.raises(AuditError):
        load_config(path, required=True)


def test_missing_anchor_suggestion_is_specific_and_preserves_query(repo):
    report = check(repo, "[guide](docs/guide.md?raw=1#instal)")
    assert report.issues[0].suggestion == "docs/guide.md?raw=1#install"


def test_missing_file_suggestion_uses_existing_sibling(repo):
    report = check(repo, "[guide](docs/guied.md#install)")
    assert report.issues[0].suggestion == "docs/guide.md#install"


def test_case_suggestion_uses_repository_root_link_style(repo):
    report = check(repo, "[guide](/Docs/Guide.md#install)")
    assert report.issues[0].suggestion == "/docs/guide.md#install"


def test_unrelated_missing_anchor_has_no_suggestion(repo):
    report = check(repo, "[guide](docs/guide.md#xxxxxxxxx)")
    assert report.issues[0].suggestion is None


def test_reusing_auditor_after_a_fix_refreshes_document_and_directory_cache(repo):
    source = repo / "README.md"
    source.write_text("[new](new.md#changed)", encoding="utf-8")
    auditor = Auditor(repo)
    assert auditor.run([source]).issues[0].code == "missing_file"
    (repo / "new.md").write_text("# Changed\n", encoding="utf-8")
    assert not auditor.run([source]).issues
    (repo / "new.md").write_text("# Something Else\n", encoding="utf-8")
    assert auditor.run([source]).issues[0].code == "missing_anchor"
