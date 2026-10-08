#!/usr/bin/env python3
"""perun_auto_update.py — keep an installed Perun current with no manual step and no restart.

Wired by `install.sh --apply-operating-layer` as a SessionStart and a UserPromptSubmit hook (the
second is the periodic check for long sessions). Claude Code live-reloads skills and settings, so
an update applied mid-session takes effect without a restart.

Hook mode (no args): returns at once. Skips when the policy key `auto_update` is `off` or when the
per-project stamp under `$XDG_CACHE_HOME/perun/auto-update/` (default `~/.cache`) is younger than 6h;
otherwise touches the stamp and spawns `--run` detached (new session, stdio to /dev/null), so no
network wait ever lands on the session start path. Prints nothing (hook stdout would enter context).

`--run [--target DIR]` (the background worker, also runnable by hand): under one machine-wide
flock, it reads `.claude/.perun-install.json` (`version`, `remote`), skips when the target has a
merge, rebase, cherry-pick or train lock (`MERGE_HEAD`, `CHERRY_PICK_HEAD`, `rebase-merge/`,
`rebase-apply/`, `train-land.lock` in its git dir or any `worktrees/*/` dir), when a Perun-managed
file differs from the hash install recorded, or when `git status` shows uncommitted changes to a
managed path or `.claude/settings*.json`. It finds the newest `vX.Y.Z` tag on the remote
(`git ls-remote`); when it is newer it fetches the tag into a cache clone
(`$XDG_CACHE_HOME/perun/src`) without `--force` (a local tag that moved is refused), aborts unless
the tag's commit is an ancestor of the remote's `main` and the tree's `SHA256SUMS` verifies, then
runs that tag's `scripts/update-installed.sh TARGET` (`DCR_NO_PULL=1`), which replays the recorded
install flags. SHA256SUMS covers the skill files only (not install.sh or scripts/) and ships in the same tag, so it
proves skill-file integrity (no corrupt or partial checkout), not authenticity: trust rests on the repository owner's tags and `main`. install.sh keeps existing user
settings, writes a `.bak` and skill backups. Every worker run appends one line to
`$XDG_CACHE_HOME/perun/auto-update.log`. Exit 0 always in hook mode; `--run` exits 0 on
skip/up-to-date/updated, 1 when the update itself failed.

Stdlib only; a missing marker, remote or parseable version is a logged skip, never a guess.
"""
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perun_policy  # noqa: E402

THROTTLE = 6 * 3600
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def cache() -> Path:
    """Perun's user cache dir: `$XDG_CACHE_HOME/perun`, else `~/.cache/perun` (same root as perun_policy)."""
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "perun"


def log(target: Path, msg: str) -> None:
    """Append one timestamped line for `target` to the local log. Side effect: creates the cache dir."""
    cache().mkdir(parents=True, exist_ok=True)
    with open(cache() / "auto-update.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {target} {msg}\n")


def stamp(target: Path) -> Path:
    """Per-project throttle stamp; the name hashes the absolute path so projects never share one."""
    return cache() / "auto-update" / (hashlib.sha256(str(target).encode()).hexdigest()[:16] + ".stamp")


def enabled(target: Path) -> bool:
    """True when the policy found from `target` has `auto_update: on`. A malformed policy fails closed (False)."""
    try:
        return perun_policy.load(perun_policy.find_policy(str(target)))["auto_update"] == "on"
    except ValueError:
        return False


def hook(target: Path, now: float | None = None) -> bool:
    """Hook fast path: True when a background worker was spawned. No network, no git, no waiting."""
    now = time.time() if now is None else now
    s = stamp(target)
    if not enabled(target) or (s.is_file() and now - s.stat().st_mtime < THROTTLE):
        return False
    s.parent.mkdir(parents=True, exist_ok=True)
    s.write_text(f"{int(now)}\n")  # before the spawn, so a second session in the window does not double-run
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--run", "--target", str(target)], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def version(s: str) -> tuple | None:
    """`1.2.3` or `v1.2.3` as an int tuple; None for anything else."""
    m = TAG.match(s if s.startswith("v") else "v" + s)
    return tuple(int(x) for x in m.groups()) if m else None


def git(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})


LOCKS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply", "train-land.lock")


def blocker(target: Path, marker: dict) -> str:
    """Why an update must wait ('' when clear): a merge/rebase/cherry-pick/train lock in this or any
    linked worktree, a managed file edited since install, or uncommitted git changes to a managed path
    or `.claude/settings*.json` (untracked files do not count)."""
    gd = git("-C", str(target), "rev-parse", "--absolute-git-dir", "--git-common-dir")
    if gd.returncode == 0:
        own, common = gd.stdout.split("\n")[:2]
        common = target / common  # relative to the -C dir when not absolute; an absolute path wins in `/`
        for d in [Path(own), common, *(common / "worktrees").glob("*")]:
            for lock in LOCKS:
                if (d / lock).exists():
                    return f"{lock} present in {d}"
    files = [(Path(d) / f, h) for d, fs in marker.get("skills", {}).items() for f, h in fs.items()]
    if marker.get("agent"):
        files.append((Path(marker["agent"]["path"]), marker["agent"]["sha"]))
    for rel, h in files:
        p = target / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
            return f"dirty Perun-managed file {rel}"
    paths = [*marker.get("skills", {}), *([marker["agent"]["path"]] if marker.get("agent") else []),
             ":(glob).claude/settings*.json"]
    st = git("-C", str(target), "status", "--porcelain", "--untracked-files=no", "--", *paths)
    if st.returncode == 0 and st.stdout.strip():
        return f"uncommitted changes: {st.stdout.strip().splitlines()[0].strip()}"
    return ""


def verify_sums(src: Path) -> str:
    """'' when every `SHA256SUMS` line in the checkout matches; else the first mismatch. Missing file fails."""
    sums = src / "SHA256SUMS"
    if not sums.is_file():
        return "no SHA256SUMS"
    for line in sums.read_text().splitlines():
        h, _, rel = line.partition("  ")
        p = src / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
            return f"SHA256SUMS mismatch: {rel}"
    return ""


def run(target: Path) -> int:
    """Background worker body (see module doc). Returns 0 skip/current/updated, 1 failed update."""
    cache().mkdir(parents=True, exist_ok=True)
    with open(cache() / "auto-update.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)  # one worker per machine: the cache clone is shared
        mf = target / ".claude/.perun-install.json"
        try:
            marker = json.loads(mf.read_text())
        except (OSError, ValueError):
            log(target, "skip: no readable install marker")
            return 0
        remote = marker.get("remote")
        have = version(marker.get("version") or "")
        if not remote or have is None:
            log(target, "skip: install marker has no remote or version (reinstall once to record them)")
            return 0
        why = blocker(target, marker)
        if why:
            log(target, f"skip: {why}")
            return 0
        ls = git("ls-remote", "--tags", "--refs", remote)
        if ls.returncode != 0:
            log(target, f"skip: cannot list tags on {remote}")
            return 0
        tags = [r.split("refs/tags/", 1)[1] for r in ls.stdout.split() if r.startswith("refs/tags/")]
        newest = max((t for t in tags if version(t)), key=version, default=None)
        if newest is None or version(newest) <= have:
            log(target, f"up to date at {marker['version']}")
            return 0
        src = cache() / "src"
        steps = ([] if (src / ".git").is_dir() else [["clone", "-q", "--no-checkout", remote, str(src)]]) + [
            ["-C", str(src), "fetch", "-q", remote, f"refs/tags/{newest}:refs/tags/{newest}",
             "+refs/heads/main:refs/remotes/origin/main"],  # no --force on tags: a moved tag is refused
            ["-C", str(src), "-c", "advice.detachedHead=false", "checkout", "-q", "-f", "--detach", newest]]
        for step in steps:
            r = git(*step, timeout=600)
            if r.returncode != 0:
                log(target, f"failed {marker['version']} -> {newest}: git {next(x for x in step if x in ('clone', 'fetch', 'checkout'))}: "
                    f"{(r.stderr.strip().splitlines() or ['?'])[-1]}")
                return 1
        why = ("" if git("-C", str(src), "merge-base", "--is-ancestor", f"refs/tags/{newest}",
                         "refs/remotes/origin/main").returncode == 0 else f"{newest} is not an ancestor of main")
        why = why or verify_sums(src)
        if why:
            log(target, f"failed {marker['version']} -> {newest}: aborted, {why}")
            return 1
        r = subprocess.run(["bash", str(src / "scripts/update-installed.sh"), str(target)], capture_output=True,
                           text=True, timeout=600, env={**os.environ, "DCR_NO_PULL": "1"})
        if r.returncode != 0:
            log(target, f"failed {marker['version']} -> {newest}: update-installed.sh exit {r.returncode}: "
                f"{((r.stderr or r.stdout).strip().splitlines() or ['?'])[-1]}")
            return 1
        log(target, f"updated {marker['version']} -> {newest} (backups: .claude/settings.local.json.bak.*, skill-backups/)")
        return 0


def main(argv: list) -> int:
    target = Path(argv[argv.index("--target") + 1] if "--target" in argv
                  else os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    if "--run" in argv:
        try:
            return run(target)
        except (OSError, subprocess.TimeoutExpired) as e:
            log(target, f"failed: {type(e).__name__}: {e}")
            return 1
    try:
        hook(target)
    except OSError:
        pass  # a hook must never break session start
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
