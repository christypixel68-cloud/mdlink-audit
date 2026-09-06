"""Verify a built wheel in a fresh environment, with offline installation.

Preparation downloads dependency wheels. Installation and auditing then run
without an index. Nothing is published and no user repository is modified.
Run `python -m build` before invoking this script from the project root.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    wheels = sorted(Path("dist").glob("*.whl"))
    if len(wheels) != 1:
        print("Expected exactly one built wheel in dist/", file=sys.stderr)
        return 2
    wheel = wheels[0].resolve()
    with TemporaryDirectory(prefix="mdlink-audit-wheel-") as directory:
        work = Path(directory)
        wheelhouse = work / "wheelhouse"
        wheelhouse.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--dest",
                str(wheelhouse),
                str(wheel),
            ],
            check=True,
        )
        environment = work / "environment"
        venv.EnvBuilder(with_pip=True).create(environment)
        binary = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                str(binary),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-index",
                "--find-links",
                str(wheelhouse),
                str(wheel),
            ],
            cwd=work,
            check=True,
        )
        probe = work / "probe"
        probe.mkdir()
        guide = probe / "Guide.md"
        guide.write_text("# 安装\n", encoding="utf-8")
        source = probe / "README.md"
        source.write_text("[guide](guide.md#安装)\n", encoding="utf-8")
        command = [str(binary), "-m", "mdlink_audit", "--root", str(probe), "--format", "json"]
        result = subprocess.run(command, cwd=work, capture_output=True, text=True, encoding="utf-8")
        report = json.loads(result.stdout)
        if result.returncode != 1 or report["issues"][0]["code"] != "case_mismatch":
            raise RuntimeError(f"Installed wheel failed the broken-link probe: {result}")
        source.write_text("[guide](Guide.md#安装)\n", encoding="utf-8")
        result = subprocess.run(command, cwd=work, capture_output=True, text=True, encoding="utf-8")
        report = json.loads(result.stdout)
        if result.returncode != 0 or report["summary"]["links_checked"] != 1:
            raise RuntimeError(f"Installed wheel failed the fixed-link probe: {result}")
        entry = environment / (
            "Scripts/mdlink-audit.exe" if os.name == "nt" else "bin/mdlink-audit"
        )
        subprocess.run([str(entry), "--version"], cwd=work, check=True)
    print("Wheel smoke test passed: clean install, CLI entry point, broken and fixed links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
