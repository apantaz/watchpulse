"""Prevent direct pushes to protected branches from local Git hooks."""

from __future__ import annotations

import os

PROTECTED_BRANCHES = frozenset({"main", "master"})


def branch_name(ref: str) -> str:
    """Return the final branch component from a Git ref."""
    return ref.removeprefix("refs/heads/")


def main() -> int:
    """Reject a pre-push operation targeting a protected branch."""
    remote_ref = os.getenv("PRE_COMMIT_REMOTE_BRANCH", "")
    branch = branch_name(remote_ref)
    if branch in PROTECTED_BRANCHES:
        print(f"Direct pushes to {branch!r} are blocked; open a pull request instead.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
