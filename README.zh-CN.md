# mdlink-audit

[![CI](https://github.com/christypixel68-cloud/mdlink-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/christypixel68-cloud/mdlink-audit/actions/workflows/ci.yml)

在重命名、移动文件或发布版本前，检查文档中的本地链接是否仍然有效。

**mdlink-audit** 是一个离线运行的 Python 命令行工具，用于检查仓库内 Markdown 的文件链接、图片路径和标题锚点。结果可输出为终端文本、JSON 或 GitHub Actions 注解。

[English](README.md) · [使用说明](docs/usage.md) · [GitHub Action](docs/github-action.md) · [真实仓库验证](docs/validation.md) · [参与贡献](CONTRIBUTING.md)

## 检查范围

- 相对路径和仓库根路径，例如 `../guide.md` 和 `/docs/guide.md`。
- 本地文件与图片目标，包括中文文件名和 URL 编码的空格。
- Markdown 文件中的标题锚点，包括同一文档内的跳转。
- 文件名大小写，即使在 Windows 上也检查，提前发现 Linux CI 中可能失效的链接。
- 超出指定仓库根目录的目标，包括指向仓库外的符号链接。
- 可选检查 Markdown 内静态 HTML 的 `href`、`src` 链接和元素 ID。

外部网址和带协议的链接会被跳过，不发起网络请求。当前不解析 MDX 表达式、`srcset`、CSS URL 和文档框架的路由规则。

## 快速开始

检查结果会为相近的文件名、标题和大小写错误提供候选修正链接，供你确认后修改。已闭合的 YAML 文档头、代码示例和注释不参与链接检查。

需要 **Python 3.11 或更高版本**。使用 pip 和 Git 安装指定版本，然后在需要检查的仓库目录运行：

```sh
python -m pip install "git+https://github.com/christypixel68-cloud/mdlink-audit.git@v0.2.0"
python -m mdlink_audit --help
python -m mdlink_audit .
```

也可以从 [GitHub Release](https://github.com/christypixel68-cloud/mdlink-audit/releases/tag/v0.2.0) 下载 `.whl` 文件，再用 `python -m pip install 下载的文件路径.whl` 安装。当前尚未发布到 PyPI。

安装后也可使用 `mdlink-audit` 命令：

```sh
mdlink-audit --root /path/to/repository
mdlink-audit README.md docs --format text
mdlink-audit --format json
```

从源码目录运行演示，会先在临时仓库中报告路径大小写和标题错误，再展示修正后的通过结果：

```sh
git clone https://github.com/christypixel68-cloud/mdlink-audit.git
cd mdlink-audit
python examples/demo.py
```

默认从当前工作目录向上查找最近的 `.git`，将其所在目录作为根目录；找不到时使用当前工作目录。不传入路径时扫描整个根目录。显式传入的路径相对于当前工作目录解析，并且必须位于所选根目录内。

退出码：`0` 表示未发现链接问题，`1` 表示链接校验失败，`2` 表示输入、配置或读取错误。默认情况下，没有 Markdown 文件也会返回 `0`；使用 `--fail-on-empty` 可将空扫描视为输入错误。

## 配置

在仓库根目录创建 `.mdlink-audit.toml`：

```toml
exclude = ["generated/**", "vendor/**"]
ignore_links = ["/generated-api/*"]
include_html = true
```

这些键直接位于文件顶层，不要添加表头。HTML 检查默认关闭，通过 `include_html = true` 或 `--include-html` 开启。也可使用 `--config` 指定配置文件，或重复传入 `--exclude`、`--ignore-link`。被忽略的目标将不再校验，建议只对明确由构建流程生成的内容设置例外。详细行为见[使用说明](docs/usage.md)。

## 接入 GitHub Actions

[本项目的 CI 配置](.github/workflows/ci.yml)会在推送和拉取请求时运行。其他需要检查的仓库可使用以下示例：

```yaml
name: Documentation links
on: [push, pull_request]

permissions:
  contents: read

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6
        with:
          python-version: "3.11"
      - uses: christypixel68-cloud/mdlink-audit@v0.2.0
        with:
          include-html: 'true'
```

Action 默认扫描整个仓库，没有 Markdown 文件时也会报错。[完整参数](docs/github-action.md#inputs)支持指定路径和配置。正式采用时建议将 Action 版本固定到经过审查的完整提交 SHA。安装依赖可能需要联网，安装后的检查过程不需要联网。

## 提交前检查

在 `.pre-commit-config.yaml` 中加入：

```yaml
repos:
  - repo: https://github.com/christypixel68-cloud/mdlink-audit
    rev: v0.2.0
    hooks:
      - id: mdlink-audit
```

每次运行钩子都会检查整个仓库，包括只移动或删除图片等被引用文件的提交，便于发现未修改的文档中受到影响的链接。

## 当前状态

`0.2.0` 仍是早期版本。已有其他工具具备相近能力，本项目聚焦离线 Python 工作流、本地路径和标题检查，以及便于定位问题的 CI 输出。它不是完整的 GitHub Markdown 渲染器，也不保证完整兼容 GitHub Flavored Markdown。

在把它作为发布检查前，请先阅读[已知限制](docs/design.md#known-limitations)。[路线图](docs/roadmap.md)列出了后续候选工作，[更新记录](CHANGELOG.md)仅记录已实现的变化。

## 开发与贡献

```sh
python -m pip install ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m mdlink_audit . --fail-on-empty
```

欢迎提交最小复现、跨平台兼容修复和文档改进。请参考[贡献指南](CONTRIBUTING.md)和[安全政策](SECURITY.md)。

## 许可证

安装包构建和干净环境验证方法见[发布准备说明](docs/releasing.md)。

MIT，见 [LICENSE](LICENSE)。
