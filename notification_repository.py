"""Read-only Git guard for delivery; never rewrites or pushes production."""
import re
import subprocess
from pathlib import Path


def revision_guard(root, built_commit):
    def git(*args):
        result = subprocess.run(["git", *args], cwd=Path(root), capture_output=True, text=True)
        if result.returncode:
            raise ValueError("Cannot establish delivery revision safely")
        return result.stdout.strip()

    if not re.fullmatch(r"[0-9a-f]{40}", built_commit or ""):
        raise ValueError("Delivery requires an exact built commit")
    head = git("rev-parse", "HEAD")
    git("merge-base", "--is-ancestor", built_commit, head)
    # Receipt-only descendants are safe. Check every intervening commit, not just
    # the net diff: a changed-and-reverted publication is not a receipt commit.
    changes = set(git("log", "--format=", "--name-only", f"{built_commit}..{head}").splitlines())
    changes.discard("")
    if changes - {"notification-delivery.json"}:
        raise ValueError("Main contains publication changes not in the built release")
    remote = git("ls-remote", "--exit-code", "origin", "refs/heads/main").split()
    if len(remote) != 2 or remote[0] != head:
        raise ValueError("Main advanced during delivery; defer to its release")
    return head
