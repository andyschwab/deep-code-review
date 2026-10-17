#!/usr/bin/env python3
"""Bench-integrity gate for docs/bench/<dir> (stdlib only).

Usage: bench_check.py [--changed [BASE]] [--allow FILE] [--max-overlap F] DIR...

Fails (exit 1, one line per problem) when a bench dir:
  a. scores the same scenario id in a tune file and a held file (a driver that skips
     existing outputs then serves tune outputs as held), or ships an outputs/ file that
     is byte-identical to the same relative path in another docs/bench dir (stale reuse);
  b. has no ledger.jsonl line {"event": "preregistered", "sha256": H} where H (>= 12 hex)
     is a prefix of sha256(SHA256-frozen.txt) and that line precedes the first other line
     (and its "ts", when both have one, is not later);
  c. has a PREREGISTERED*.md naming a SHA256*.txt hash file that does not exist;
  d. has a scenario whose 10-word shingles overlap earlier benches by more than
     --max-overlap (default 0.2). --allow FILE (default DIR/overlap-allow.txt) lists
     template phrases, one per line, whose shingles are ignored.
DIR/reuse-allow.txt (optional) lists outputs/ path prefixes whose byte-identical reuse is
deliberate (e.g. a rival arm generated once and shared); document why in PREREGISTERED.md.

Scenario files: top-level DIR/*.json that are lists of {"id": ...} objects. Old benches
lack ledgers, so only dirs named on the command line are checked; --changed names the
docs/bench dirs absent from BASE (default origin/main), so CI gates only new benches.
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

N = 10


def scenarios(d):
    """[(file, id, text)] for every scenario list in d."""
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except ValueError:
            continue
        if isinstance(data, list) and data and all(isinstance(s, dict) and "id" in s for s in data):
            out += [(f.name, str(s["id"]), " ".join(str(v) for k, v in s.items() if k != "id")) for s in data]
    return out


def shingles(text):
    w = re.findall(r"\w+", text.lower())
    return {tuple(w[i:i + N]) for i in range(len(w) - N + 1)}


def check(d, others, allow=None, max_overlap=0.2):
    d, errs = Path(d), []
    sc = scenarios(d)
    # a. tune/held id collision; cross-bench byte-identical outputs
    ids = {s: {i for f, i, _ in sc if s in f} for s in ("tune", "held")}
    for i in sorted(ids["tune"] & ids["held"]):
        errs.append(f"{d}: scenario id {i} is in both tune and held")
    ra = d / "reuse-allow.txt"
    keep = tuple(l.strip() for l in ra.read_text().splitlines() if l.strip()) if ra.is_file() else ()
    for o in (d / "outputs").rglob("*") if (d / "outputs").is_dir() else []:
        if not o.is_file() or str(o.relative_to(d)).startswith(keep):
            continue
        for x in others:
            p = x / o.relative_to(d)
            if p.is_file() and p.read_bytes() == o.read_bytes():
                errs.append(f"{d}: {o.relative_to(d)} is byte-identical to {p}")
    # b. preregistration ledger
    frozen, led = d / "SHA256-frozen.txt", d / "ledger.jsonl"
    if not frozen.is_file() or not led.is_file():
        errs.append(f"{d}: SHA256-frozen.txt and ledger.jsonl are both required")
    else:
        h = hashlib.sha256(frozen.read_bytes()).hexdigest()
        ev = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
        pre = [(n, e) for n, e in enumerate(ev) if e.get("event") == "preregistered"
               and len(str(e.get("sha256", ""))) >= 12 and h.startswith(str(e["sha256"]))]
        gen = next((n for n, e in enumerate(ev) if e.get("event") != "preregistered"), len(ev))
        if not pre:
            errs.append(f"{d}: ledger.jsonl has no preregistered event matching sha256(SHA256-frozen.txt)={h[:12]}")
        elif pre[0][0] > gen or any(
                isinstance(pre[0][1].get("ts"), (int, float)) and isinstance(e.get("ts"), (int, float))
                and pre[0][1]["ts"] > e["ts"] for e in ev[gen:gen + 1]):
            errs.append(f"{d}: preregistered event is not earlier than the first generation event")
    # c. hash files named by the prereg docs
    for p in d.glob("PREREGISTERED*.md"):
        for n in sorted(set(re.findall(r"SHA256[\w.-]*\.txt", p.read_text()))):
            if not (d / n).is_file():
                errs.append(f"{p}: names hash file {n}, which does not exist")
    # d. shingle overlap vs earlier benches
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
            errs.append(f"{d}: {f} id {i} shares {r:.0%} of its {N}-word shingles with earlier benches (max {max_overlap:.0%})")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*")
    ap.add_argument("--changed", nargs="?", const="origin/main")
    ap.add_argument("--allow")
    ap.add_argument("--max-overlap", type=float, default=0.2)
    a = ap.parse_args(argv)
    dirs = [Path(x) for x in a.dirs]
    root = Path("docs/bench")
    if a.changed:
        for d in sorted(root.iterdir()) if root.is_dir() else []:
            if d.is_dir() and not subprocess.run(["git", "ls-tree", a.changed, f"{d}/"],
                                                 capture_output=True, text=True, check=True).stdout.strip():
                dirs.append(d)
    errs = []
    for d in dirs:
        others = [x for x in sorted(root.iterdir()) if x.is_dir() and x.resolve() != d.resolve()]
        errs += check(d, others, a.allow, a.max_overlap)
    print("\n".join(errs) or f"bench_check: {len(dirs)} dir(s) clean")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
