from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def has_git_changes(cwd: Path, files: Iterable[str]) -> bool:
    rel = list(files)
    res = run_git(["status", "--porcelain", "--", *rel], cwd)
    if res.returncode != 0:
        raise RuntimeError(f"git status failed: {res.stderr.strip()}")
    return bool(res.stdout.strip())


def commit_and_push(cwd: Path, files: Iterable[str], message: str, push: bool = True) -> None:
    rel = list(files)

    add_res = run_git(["add", "--", *rel], cwd)
    if add_res.returncode != 0:
        raise RuntimeError(f"git add failed: {add_res.stderr.strip()}")

    commit_res = run_git(["commit", "-m", message], cwd)
    if commit_res.returncode != 0:
        if "nothing to commit" in (commit_res.stdout + commit_res.stderr).lower():
            return
        raise RuntimeError(f"git commit failed: {commit_res.stderr.strip()}")

    if push:
        push_res = run_git(["push"], cwd)
        if push_res.returncode != 0:
            raise RuntimeError(f"git push failed: {push_res.stderr.strip()}")
