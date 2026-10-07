#!/usr/bin/env python3
"""merge_findings.py [--cap N] <findings.json>... — dedupe, rank and cap findings from one or more passes.

Purpose: cut review noise. Inputs are findings files already annotated by finding_ground_check.py.
Steps: drop gap rows whose `grounded` is not true (fail closed: unchecked counts as ungrounded);
dedupe by (file of first evidence, `mechanism`, falling back to the normalized title), keeping the
highest-severity row and unioning evidence; rank Critical>High>Medium>Low>Info (stable); keep the top
--cap (default 20). Strength rows pass through uncapped. Output: {"findings": [...], "dropped":
{"ungrounded": n, "duplicate": n, "over_cap": n}} on stdout. An empty `findings` list is a valid result:
a clean diff yields NONE. Exit 0, or 2 on usage/unreadable input. Side effects: none.
"""
import json, re, sys

SEV = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _sev(f):
    return SEV.get(str(f.get("severity", "")).lower(), 5)


def _key(f):
    ev = (f.get("evidence") or [""])[0]
    mech = f.get("mechanism") or re.sub(r"\W+", " ", f.get("title", "")).strip()
    return (ev.rsplit(":", 1)[0], mech.lower())


def merge(rows, cap=20):
    drop = {"ungrounded": 0, "duplicate": 0, "over_cap": 0}
    strengths, best = [], {}
    for f in rows:
        if f.get("polarity", "gap") != "gap":
            strengths.append(f)
        elif f.get("grounded") is not True:
            drop["ungrounded"] += 1
        else:
            k = _key(f)
            if k in best:
                drop["duplicate"] += 1
                keep, other = (best[k], f) if _sev(best[k]) <= _sev(f) else (f, best[k])
                keep["evidence"] = list(dict.fromkeys((keep.get("evidence") or []) + (other.get("evidence") or [])))
                best[k] = keep
            else:
                best[k] = f
    ranked = sorted(best.values(), key=_sev)
    drop["over_cap"] = max(0, len(ranked) - cap)
    return {"findings": ranked[:cap] + strengths, "dropped": drop}


def main(argv):
    args, cap = argv[1:], 20
    if args[:1] == ["--cap"]:
        try:
            cap, args = int(args[1]), args[2:]
        except (IndexError, ValueError):
            args = []
    if not args or cap < 0:
        print("usage: merge_findings.py [--cap N] <findings.json>...", file=sys.stderr)
        return 2
    try:
        rows = []
        for p in args:
            with open(p, encoding="utf-8") as fh:
                rows += json.load(fh)["findings"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"merge_findings: cannot read findings: {type(e).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(merge(rows, cap), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
