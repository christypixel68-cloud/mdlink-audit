"""Exercise the real pre-commit hook when only a non-Markdown asset is selected."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="mdlink-precommit-") as temporary:
        base = Path(temporary).resolve()
        repo = base / "consumer repo"
        repo.mkdir()
        assets = repo / "assets"
        assets.mkdir()
        (repo / "README.md").write_text("![Diagram](assets/diagram.svg)\n", encoding="utf-8")
        renamed = assets / "renamed.svg"
        renamed.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
        env = {**os.environ, "PRE_COMMIT_HOME": str(base / "hook-cache")}
        subprocess.run(["git", "init", "--quiet", str(repo)], check=True, env=env)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)

        def check_asset(filename: str, expected: int) -> None:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pre_commit",
                    "try-repo",
                    str(source),
                    "mdlink-audit",
                    "--files",
                    filename,
                    "--verbose",
                    "--color",
                    "never",
                ],
                cwd=repo,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=180,
                check=False,
            )
            if result.returncode != expected:
                raise RuntimeError(
                    f"Expected hook exit {expected}, got {result.returncode}:\n"
                    f"{result.stdout}\n{result.stderr}"
                )
            if expected == 1 and "missing_file" not in result.stdout:
                raise RuntimeError(f"Hook did not report the broken image link:\n{result.stdout}")
            if expected == 0 and "1 local links checked" not in result.stdout:
                raise RuntimeError(f"Hook skipped the unchanged Markdown:\n{result.stdout}")

        check_asset("assets/renamed.svg", 1)
        renamed.rename(assets / "diagram.svg")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
        check_asset("assets/diagram.svg", 0)
    print("pre-commit smoke passed: asset-only change checked unchanged Markdown; fix accepted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
