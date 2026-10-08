#!/usr/bin/env python3
"""sandbox_probe.py: first-run check that an agent can work autonomously inside the sandbox.

Usage: python3 sandbox_probe.py [REPO] [--verdict-only]

Runs five harmless checks (git status in REPO, `import ssl`, an HTTPS HEAD to github.com,
binding 127.0.0.1:0, writing a temp file under ~/.cache) and prints one line per check;
each failure gets a plain-English cause and the exact fix (a settings key or a
`/sandbox exclude` pattern). The last line is the verdict. Nothing is deleted or killed:
the ~/.cache file is a self-removing tempfile, the socket is closed at once.
Run it from a Claude Code Bash call to test the sandbox itself; from a plain terminal it
only tests that shell. Exit 0 = all OK, 1 = at least one failure.
"""
import os, socket, subprocess, sys, tempfile
from pathlib import Path


def _run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=15, check=False)
    if r.returncode:
        raise RuntimeError(f"exit {r.returncode}")


def _bind():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))


def _cache_write():
    d = Path.home() / ".cache"
    d.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=d, prefix="perun-probe-"):
        pass


def checks(repo):
    """(name, callable that raises on failure, plain-English cause, exact fix) for each probe."""
    return [
        ("git", lambda: _run(["git", "status", "--porcelain"], cwd=repo), "git cannot run in this repo",
         "run the failing git command yourself with the ! prefix (protected paths such as .claude/skills stay write-denied)"),
        ("python-ssl", lambda: _run([sys.executable, "-c", "import ssl"]), "python3 has no working ssl module",
         "reinstall python3 with OpenSSL support (not a sandbox setting)"),
        ("network", lambda: _run(["curl", "-sI", "-m", "10", "-o", os.devnull, "https://github.com"]),
         "HTTPS to github.com is blocked", 'add "github.com" to sandbox.network.allowedDomains'),
        ("local-bind", _bind, "dev servers cannot listen on localhost", "set sandbox.network.allowLocalBinding: true"),
        ("cache-write", _cache_write, "package managers cannot write their cache in ~/.cache",
         'add "~/.cache" to sandbox.filesystem.allowWrite'),
    ]


def probe(items):
    """Run each check; return (lines, failures). A check fails on any exception (timeouts included)."""
    lines, bad = [], 0
    for name, fn, cause, fix in items:
        try:
            fn()
            lines.append(f"OK    {name}")
        except Exception:  # noqa: BLE001 - any failure is reported, never raised
            bad += 1
            lines.append(f"FAIL  {name}: {cause}. Fix: {fix}")
    n = len(items)
    lines.append(f"sandbox probe: {n}/{n} checks passed in this shell; agents can work without manual permission edits" if not bad
                 else f"sandbox probe: {bad} of {n} checks failed; run python3 {Path(__file__).resolve()} for the fixes")
    return lines, bad


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    repo = next((a for a in argv if not a.startswith("-")), ".")
    lines, bad = probe(checks(repo))
    print("\n".join(lines[-1:] if "--verdict-only" in argv else lines))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
