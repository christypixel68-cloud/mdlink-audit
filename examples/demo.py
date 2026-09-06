"""Run a self-contained broken-then-fixed repository demo after installing the package."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    with TemporaryDirectory(prefix="mdlink-audit-demo-") as directory:
        root = Path(directory)
        (root / "docs").mkdir()
        (root / "docs" / "guide.md").write_text("# 安装指南\n", encoding="utf-8")
        readme = root / "README.md"
        readme.write_text(
            "# Demo\n\n[guide](docs/Guide.md#安装指南)\n[setup](docs/guide.md#setup)\n",
            encoding="utf-8",
        )
        print("1. Catch a path casing error and a stale heading:", flush=True)
        command = [sys.executable, "-m", "mdlink_audit", "--root", str(root)]
        broken = subprocess.run(command, check=False)
        if broken.returncode != 1:
            return 1
        readme.write_text("# Demo\n\n[guide](docs/guide.md#安装指南)\n", encoding="utf-8")
        print("\n2. Fix both links and rerun:", flush=True)
        return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
