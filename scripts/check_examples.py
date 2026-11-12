#!/usr/bin/env python3
"""Checks the code blocks of the guides without calling the API: Python compiles, JavaScript parses, shell parses, JSON is valid.

    python3 scripts/check_examples.py            # new/ and es/new/

To run the examples for real (against a test API key), see "Customer API guides" in README.md.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```(\w+)([^\n]*)\n(.*?)^```", re.S | re.M)
PAGES = [p for base in ("new", "es/new") for p in (ROOT / base).rglob("*.mdx")
         if p.parent.name != "platform-api"]            # the tool pages are generated, not written by hand


def check(lang: str, code: str, where: str) -> str | None:
    if lang == "python":
        try:
            compile(code, where, "exec")
        except SyntaxError as exc:
            return f"python: {exc}"
    elif lang == "json":
        try:
            json.loads(code)
        except ValueError as exc:
            return f"json: {exc}"
    elif lang == "bash":
        proc = subprocess.run(["bash", "-n"], input=code, capture_output=True, text=True)
        if proc.returncode:
            return f"bash: {proc.stderr.strip()}"
    elif lang == "javascript" and shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
            handle.write(code)
        proc = subprocess.run(["node", "--check", handle.name], capture_output=True, text=True)
        if proc.returncode:
            return f"javascript: {proc.stderr.strip().splitlines()[0] if proc.stderr else 'error'}"
    return None


def main() -> int:
    problems, blocks = [], 0
    for page in sorted(PAGES):
        text = page.read_text(encoding="utf-8")
        for match in FENCE.finditer(text):
            lang, code = match.group(1).lower(), match.group(3)
            blocks += 1
            line = text[: match.start()].count("\n") + 1
            error = check(lang, code, f"{page.relative_to(ROOT)}:{line}")
            if error:
                problems.append(f"{page.relative_to(ROOT)}:{line}: {error}")
    print(f"{blocks} code blocks in {len(PAGES)} pages, {len(problems)} problems")
    for item in problems:
        print(" -", item)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
