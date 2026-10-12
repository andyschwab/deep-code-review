#!/usr/bin/env python3
"""review_feedback.py -- repo-local accept/dismiss ledger for review findings.

  record  --id F3 --rule <rule> --verdict accept|dismiss --severity <sev> [--area B] [--reason "..."]
  summary [--min-dismissals 3] [--json]
  learn   [--out PATH]   (record also runs it; default PATH = learned-rules.md beside the ledger)

learn derives each rule's lifecycle state from the ledger alone (no stored state, so it is idempotent:
same ledger -> byte-identical file). candidate (>= CANDIDATE_MIN rows) -> shadow (>= SHADOW_MIN rows:
applied but marked) -> promoted (>= PROMOTE_ACCEPTS accepts and accept-rate >= PROMOTE_RATE) or
disabled (>= DISABLE_MIN dismissals and dismiss-rate >= DISABLE_RATE). A safety-floor rule is never
disabled. The output is capped at MAX_LINES lines; a review loads it only if present.

record appends one JSON line to the ledger (default .review/feedback.jsonl, override with --ledger or
$REVIEW_FEEDBACK_LEDGER). summary prints per-rule accept-rate (telemetry) and SUGGESTED REVIEW.md
rules: a rule is suggested only when it was dismissed at least --min-dismissals times and never
accepted, and never when any of its rows is safety-floor (severity Blocker/Critical, or area in
A B C D N Q T, or any area that is not an assigned domain letter: security, LLM/agent, data integrity, secrets, privacy, tenancy). Suggestions are text for
a human to paste into REVIEW.md; this script never writes it, so nothing is silenced automatically.
Side effects: learn writes (or removes, when empty) its --out file; record creates the ledger directory and appends. Reasons are free text: keep names and
identifiers out, and keep the ledger out of public commits. Exits non-zero on a bad ledger line
(fail closed).
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

SEVERITIES = ("Blocker", "Critical", "High", "Medium", "Low", "Nit")
SAFETY_SEV = {"Blocker", "Critical"}
SAFETY_AREAS = set("ABCDNQT")
AREAS = tuple("ABCDEFGHIJKLMNOPQRST") + ("W",)  # assigned domains; U/V/X-Z are not
DEFAULT_LEDGER = ".review/feedback.jsonl"
CANDIDATE_MIN, SHADOW_MIN = 2, 3
PROMOTE_ACCEPTS, PROMOTE_RATE = 5, 0.8
DISABLE_MIN, DISABLE_RATE = 3, 0.7  # DISABLE_MIN is also summary's --min-dismissals default
MAX_LINES = 40
ORDER = ("promoted", "shadow", "candidate", "disabled")


def is_safety(row):
    # fail closed: a missing, lowercase or unknown area is treated as safety-floor
    area = row.get("area", "")
    return row["severity"] in SAFETY_SEV or area in SAFETY_AREAS or area not in AREAS


def load(path):
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            assert r["verdict"] in ("accept", "dismiss") and r["severity"] in SEVERITIES and r["rule"]
        except (ValueError, KeyError, AssertionError, TypeError):
            sys.exit(f"review_feedback: bad ledger line {n} in {path} (fail closed)")
        rows.append(r)
    return rows


def summarize(rows, min_dismissals=DISABLE_MIN):
    by = defaultdict(list)
    for r in rows:
        by[r["rule"]].append(r)
    out = []
    for rule, rs in sorted(by.items()):
        acc = sum(r["verdict"] == "accept" for r in rs)
        dis = len(rs) - acc
        safety = any(is_safety(r) for r in rs)
        out.append({
            "rule": rule, "accepted": acc, "dismissed": dis, "accept_rate": round(acc / len(rs), 2),
            "safety_floor": safety,
            "suggest": (not safety) and acc == 0 and dis >= min_dismissals,
            "reasons": sorted({" ".join(r["reason"].split()) for r in rs if r.get("reason") and r["verdict"] == "dismiss"}),
        })
    return out


def state(acc, dis, safety):
    """Lifecycle state from counts: disabled > promoted > shadow > candidate > None (below CANDIDATE_MIN)."""
    n = acc + dis
    if not safety and dis >= DISABLE_MIN and dis / n >= DISABLE_RATE:
        return "disabled"
    if acc >= PROMOTE_ACCEPTS and acc / n >= PROMOTE_RATE:
        return "promoted"
    return "shadow" if n >= SHADOW_MIN else "candidate" if n >= CANDIDATE_MIN else None


def clean(rule):
    return rule.isprintable() and "\n" not in rule


def learned_rules(rows):
    """Compact learned-rules.md text (<= MAX_LINES lines) or "" when no rule reached candidate."""
    items = []
    for x in summarize(rows):
        if not clean(x["rule"]):
            continue  # a forged ledger rule must not inject lines
        st = state(x["accepted"], x["dismissed"], x["safety_floor"])
        if st:
            items.append((ORDER.index(st), x["rule"], st, x))
    if not items:
        return ""
    head = ["# Learned rules (derived from .review/feedback.jsonl; shadow = applied but marked, report it as shadow)",
            "promoted: keep reporting. shadow/candidate: report, tag [shadow]. disabled: skip, count it as suppressed. Safety floor never disabled."]
    body = [f"- {st}: {r} ({x['accepted']} accept / {x['dismissed']} dismiss)" for _, r, st, x in sorted(items)]
    room = MAX_LINES - len(head)
    if len(body) > room:
        body = body[:room - 1] + [f"- (+{len(body) - room + 1} more omitted)"]
    return "\n".join(head + body) + "\n"


def learn(ledger, out=None):
    """Write learned-rules.md beside the ledger (or --out); remove it when nothing is learned."""
    out = Path(out) if out else Path(ledger).parent / "learned-rules.md"
    text = learned_rules(load(ledger))
    if text:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        out.unlink(missing_ok=True)  # no learned rules: absent file means a review loads nothing
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", default=os.environ.get("REVIEW_FEEDBACK_LEDGER", DEFAULT_LEDGER))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--id", required=True)
    r.add_argument("--rule", required=True)
    r.add_argument("--verdict", required=True, choices=("accept", "dismiss"))
    r.add_argument("--severity", required=True, choices=SEVERITIES)
    r.add_argument("--area", required=True, type=str.upper, choices=AREAS, help="domain letter A-T or W")
    r.add_argument("--reason", default="")
    s = sub.add_parser("summary")
    s.add_argument("--min-dismissals", type=int, default=DISABLE_MIN)
    s.add_argument("--json", action="store_true")
    l = sub.add_parser("learn")
    l.add_argument("--out", help="default: learned-rules.md beside the ledger")
    a = ap.parse_args(argv)
    if a.cmd == "learn":
        return learn(a.ledger, a.out)
    if a.cmd == "record":
        if not clean(a.rule):
            sys.exit("review_feedback: --rule must be printable single-line text")
        row = {k: getattr(a, k) for k in ("id", "rule", "verdict", "severity", "area", "reason")}
        row["reason"] = " ".join(row["reason"].split())  # one line: a newline must not forge extra suggestion lines
        Path(a.ledger).parent.mkdir(parents=True, exist_ok=True)
        with open(a.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return learn(a.ledger)  # keep learned-rules.md current so a review finds it without a manual step
    res = summarize(load(a.ledger), a.min_dismissals)
    if a.json:
        print(json.dumps(res, indent=2))
        return 0
    print("rule\taccepted\tdismissed\taccept_rate\tnote")
    for x in res:
        note = "safety floor: never suppressed" if x["safety_floor"] else ""
        print(f"{x['rule']}\t{x['accepted']}\t{x['dismissed']}\t{x['accept_rate']}\t{note}")
    sug = [x for x in res if x["suggest"]]
    if sug:
        print("\nSuggested REVIEW.md rules (human approves; paste or discard):")
    for x in sug:
        why = "; ".join(x["reasons"]) or "no reason recorded"
        print(f"- skip: {x['rule']} (dismissed {x['dismissed']}x, accepted 0x; reasons: {why})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
