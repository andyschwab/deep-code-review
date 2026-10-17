#!/usr/bin/env python3
"""Bench-integrity gate for docs/bench/<dir> (stdlib only).

Usage: bench_check.py [--changed [BASE]] [--allow FILE] [--max-overlap F] DIR...

Fails (exit 1, one line per problem) when a bench dir:
  a. has a tune or held scenario file (name contains "tune" or "held") that is not a
     non-empty list of {"id": ...} objects (or {"scenarios": [...]}), scores the same
     scenario id in a tune and a held file (a driver that skips existing outputs then
     serves tune outputs as held), or ships a non-empty outputs/ file byte-identical to
     the same relative path in another docs/bench dir (stale reuse);
  b. has no ledger.jsonl line {"event": "preregistered", "sha256": H} where H (>= 12 hex)
     is a prefix of sha256 of the first k lines of SHA256-frozen.txt for some k (k = all
     lines is the plain file hash; smaller k allows lines appended after the hash was
     logged), that line precedes the first non-preregistered line, and its timestamp is
     not later than that line's. The canonical key is "sha256"; "preregistered_sha256",
     "frozen_list_sha256" and "sha256_of_SHA256-frozen.txt" are accepted. Timestamps are
     "ts" or "iso" (epoch number or ISO-8601); an unparseable one fails, a missing one
     leaves line order as the only check;
  c. has a PREREGISTERED*.md naming a SHA256*.txt hash file that does not exist;
  d. has a scenario whose 10-word shingles overlap all other docs/bench dirs by more than
     --max-overlap (default 0.2). --allow FILE (default DIR/overlap-allow.txt) lists
     template phrases, one per line, whose shingles are ignored.
DIR/reuse-allow.txt (optional) lists outputs/ paths whose byte-identical reuse is
deliberate (e.g. a rival arm generated once and shared): an exact file path or a
directory (matches everything beneath it). Document why in PREREGISTERED.md.

Old benches lack ledgers, so only dirs named on the command line are checked; --changed
names the docs/bench dirs absent from BASE (default origin/main), so CI gates only new
benches; a missing BASE is an error.
"""
import argparse, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

N = 10
KEYS = ("sha256", "preregistered_sha256", "frozen_list_sha256", "sha256_of_SHA256-frozen.txt")
REPO = Path(__file__).resolve().parent.parent


def load(f):
    """Scenario list of f, or None when f is not a non-empty list of {"id"} objects."""
    try:
        data = json.loads(f.read_text())
    except ValueError:
        return None
    if isinstance(data, dict):
        data = data.get("scenarios")
    ok = isinstance(data, list) and data and all(isinstance(s, dict) and "id" in s for s in data)
    return data if ok else None


def scenarios(d):
    """[(file, id, text)] for every scenario list in d."""
    return [(f.name, str(s["id"]), " ".join(str(v) for k, v in s.items() if k != "id"))
            for f in sorted(d.glob("*.json")) for s in load(f) or []]


def shingles(text):
    w = re.findall(r"\w+", text.lower())
    return {tuple(w[i:i + N]) for i in range(len(w) - N + 1)}


def when(e):
    """Epoch seconds of an event's ts/iso; None when absent; ValueError when unparseable."""
    for k in ("ts", "iso"):
        v = e.get(k)
        if v is None:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        t = datetime.fromisoformat(v.replace("Z", "+00:00"))  # ValueError/AttributeError on junk
        return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).timestamp()
    return None


def ledger_errs(d):
    frozen, led = d / "SHA256-frozen.txt", d / "ledger.jsonl"
    if not frozen.is_file() or not led.is_file():
        return [f"{d}: SHA256-frozen.txt and ledger.jsonl are both required"]
    lines = frozen.read_bytes().splitlines(keepends=True)
    hs = [hashlib.sha256(b"".join(lines[:k])).hexdigest() for k in range(1, len(lines) + 1)]
    ev = []
    for n, l in enumerate(led.read_text().splitlines(), 1):
        if not l.strip():
            continue
        try:
            e = json.loads(l)
            assert isinstance(e, dict)
            e["_t"] = when(e)
        except (ValueError, AttributeError, AssertionError):
            return [f"{d}: ledger.jsonl line {n} is not a JSON object with a comparable ts/iso"]
        ev.append(e)

    def hit(e):
        return e.get("event") == "preregistered" and any(
            isinstance(e.get(k), str) and len(e[k]) >= 12 and any(h.startswith(e[k].lower()) for h in hs) for k in KEYS)
    pre = [n for n, e in enumerate(ev) if hit(e)]
    gen = next((n for n, e in enumerate(ev) if e.get("event") != "preregistered"), len(ev))
    if not pre:
        return [f"{d}: ledger.jsonl has no preregistered event matching a line-prefix hash of SHA256-frozen.txt"]
    p, g = ev[pre[0]], ev[gen:gen + 1]
    if pre[0] > gen or (g and p["_t"] is not None and g[0]["_t"] is not None and p["_t"] > g[0]["_t"]):
        return [f"{d}: preregistered event is not earlier than the first generation event"]
    return []


def check(d, others, allow=None, max_overlap=0.2):
    d, errs = Path(d), []
    # a. scenario files fail closed; tune/held id collision; cross-bench byte-identical outputs
    for f in sorted(d.glob("*.json")):
        if re.search("tune|held", f.name) and load(f) is None:
            errs.append(f"{d}: {f.name} is not a non-empty list of scenarios with ids")
    sc = scenarios(d)
    ids = {s: {i for f, i, _ in sc if s in f} for s in ("tune", "held")}
    for i in sorted(ids["tune"] & ids["held"]):
        errs.append(f"{d}: scenario id {i} is in both tune and held")
    ra = d / "reuse-allow.txt"
    keep = [l.strip().rstrip("/") for l in ra.read_text().splitlines() if l.strip()] if ra.is_file() else []
    for o in sorted((d / "outputs").rglob("*")) if (d / "outputs").is_dir() else []:
        rel = o.relative_to(d).as_posix()
        if not o.is_file() or o.stat().st_size == 0 or any(rel == k or rel.startswith(k + "/") for k in keep):
            continue
        for x in others:
            p = x / rel
            if p.is_file() and p.read_bytes() == o.read_bytes():
                errs.append(f"{d}: {rel} is byte-identical to {p}")
    errs += ledger_errs(d)
    # c. hash files named by the prereg docs
    for p in d.glob("PREREGISTERED*.md"):
        for n in sorted(set(re.findall(r"SHA256[\w.-]*\.txt", p.read_text()))):
            if not (d / n).is_file():
                errs.append(f"{p}: names hash file {n}, which does not exist")
    # d. 10-word shingle overlap vs all other benches
    ok = set()
    a = Path(allow) if allow else d / "overlap-allow.txt"
    if a.is_file():
        for l in a.read_text().splitlines():
            ok |= shingles(l)
    seen = set()
    for x in others:
        for _, _, t in scenarios(x):
            seen |= shingles(t)
    for f, i, t in sc:
        s = shingles(t) - ok
        r = len(s & seen) / len(s) if s else 0
        if r > max_overlap:
            errs.append(f"{d}: {f} id {i} shares {r:.0%} of its {N}-word shingles with other benches (max {max_overlap:.0%})")
    return errs


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*")
    ap.add_argument("--changed", nargs="?", const="origin/main")
    ap.add_argument("--allow")
    ap.add_argument("--max-overlap", type=float, default=0.2)
    a = ap.parse_args(argv)
    dirs = [Path(x) for x in a.dirs]
    root = REPO / "docs/bench"
    if a.changed:
        if git("rev-parse", "--verify", "-q", a.changed).returncode:
            sys.exit(f"bench_check: --changed base {a.changed} not found (fetch it)")
        dirs += [d for d in sorted(root.iterdir()) if d.is_dir()
                 and not git("ls-tree", a.changed, f"docs/bench/{d.name}/").stdout.strip()]
    errs = []
    for d in dirs:
        others = [x for x in sorted(root.iterdir()) if x.is_dir() and x.resolve() != d.resolve()]
        errs += check(d, others, a.allow, a.max_overlap)
    print("\n".join(errs) or f"bench_check: {len(dirs)} dir(s) clean")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
