#!/usr/bin/env python3
"""context_nudge.py — UserPromptSubmit hook: suggest a fresh session when the main context is huge.

Long sessions re-read their whole context from cache on every turn, so cost grows with size. This hook reads the
hook JSON on stdin, takes the last assistant message's usage (input + cache_read + cache_creation tokens) from
`transcript_path` as the current context size, and when it is at least `PERUN_CONTEXT_NUDGE_TOKENS` (default
250000) prints ONE line (UserPromptSubmit stdout enters context) suggesting a fresh session started from a short
handoff note. It repeats only after another 50000 tokens of growth, tracked in a stamp under
`$XDG_CACHE_HOME/perun/context-nudge/` (default `~/.cache`). Silent otherwise; any error exits 0 silently; only
the last 1 MB of the transcript is read.

Run `context_nudge.py --selftest` to check it.
"""
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

STEP = 50_000
TAIL = 1 << 20


def context_size(path):
    """Tokens in context at the last main-thread assistant message in the transcript, or None if there is none."""
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        fh.seek(max(0, fh.tell() - TAIL))
        lines = fh.read().decode("utf-8", "ignore").splitlines()
    for ln in reversed(lines):
        try:
            e = json.loads(ln)
            u = e["message"]["usage"]
        except (ValueError, KeyError, TypeError):
            continue
        if e.get("type") == "assistant" and not e.get("isSidechain"):
            return sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return None


def check(payload):
    """The nudge line for this hook payload, or None. Writes the growth stamp when it fires."""
    limit = int(os.environ.get("PERUN_CONTEXT_NUDGE_TOKENS") or 250_000)
    size = context_size(payload["transcript_path"])
    if size is None or size < limit:
        return None
    root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "perun" / "context-nudge"
    stamp = root / str(payload.get("session_id") or "unknown").replace("/", "_")
    try:
        last = int(stamp.read_text())
    except (OSError, ValueError):
        last = 0
    if size < last + STEP:
        return None
    root.mkdir(parents=True, exist_ok=True)
    stamp.write_text(str(size))
    return (f"Context is {size // 1000}k tokens and every turn re-reads it: consider a fresh session started from a "
            "short handoff note (state, open work, next step).")


def main():
    try:
        line = check(json.load(sys.stdin))
    except Exception:
        return 0  # fail open
    if line:
        print(line)
    return 0


def _run(payload):
    real_in, real_out = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO(payload if isinstance(payload, str) else json.dumps(payload)), io.StringIO()
    try:
        rc = main()
        return rc, sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = real_in, real_out


def _selftest():
    tmp = tempfile.mkdtemp(prefix="ctx-nudge-")
    saved = {k: os.environ.get(k) for k in ("XDG_CACHE_HOME", "PERUN_CONTEXT_NUDGE_TOKENS")}
    os.environ["XDG_CACHE_HOME"] = tmp
    os.environ.pop("PERUN_CONTEXT_NUDGE_TOKENS", None)
    tr = os.path.join(tmp, "t.jsonl")

    def write(n, tail=""):
        usage = {"input_tokens": 2, "cache_read_input_tokens": n - 2, "cache_creation_input_tokens": 0}
        with open(tr, "w") as fh:
            fh.write(json.dumps({"type": "assistant", "message": {"usage": usage}}) + "\n" + tail)

    res = []
    try:
        pl = {"transcript_path": tr, "session_id": "s"}
        write(100_000)
        res.append(("silent-below-threshold", check(pl) is None))
        write(260_000, "garbage\n" + json.dumps({"type": "user"}) + "\n")
        res.append(("fires-over-threshold-skipping-junk-tail", "260k" in (check(pl) or "")))
        write(290_000)
        res.append(("silent-within-50k-growth", check(pl) is None))
        write(310_000)
        res.append(("fires-again-after-50k-growth", check(pl) is not None))
        os.environ["PERUN_CONTEXT_NUDGE_TOKENS"] = "1000"
        res.append(("env-threshold-other-session", check({"transcript_path": tr, "session_id": "t"}) is not None))
        res.append(("garbage-stdin-exit-0-silent", _run("not json") == (0, "")))
        res.append(("missing-transcript-exit-0-silent", _run({"transcript_path": tr + "x"}) == (0, "")))
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        shutil.rmtree(tmp, ignore_errors=True)
    for n, ok in res:
        print(f"{'PASS' if ok else 'FAIL'}  {n}")
    print(f"\nselftest: {sum(ok for _, ok in res)}/{len(res)} passed")
    return 0 if all(ok for _, ok in res) else 1


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
