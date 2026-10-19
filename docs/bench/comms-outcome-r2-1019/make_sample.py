#!/usr/bin/env python3
"""Builds the judge-validation sample: every regex-flagged figure of r1 held-out V0 and E4 outputs plus 14 random ones each from RIVAL and NONE.
usage: make_sample.py  -> writes sample.json (items without labels) and prints a readable dump for hand labelling.
Flagging is r1's own rule (fixed.numbers: a numeric token or weekday absent from the notes)."""
import json, random, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
R1 = Path(__file__).resolve().parent.parent / "comms-outcome-1019"
sys.path.insert(0, str(R1))
import bench as b  # noqa: E402
import fixed  # noqa: E402,F401  patches bench._numbers (amendment A2)


def flagged(split, arms, base=R1):
    """[(arm, scenario, sample k, token)] for every flagged token of every output."""
    out = []
    for sc in json.loads((base / f"scenarios_{split}.json").read_text()):
        for a in arms:
            for k in range(b.SAMPLES):
                t = (base / "outputs" / split / a / f"{sc['id']}_{k}.txt").read_text()
                out += [(a, sc["id"], k, tok) for tok in b.invented(t, sc["prompt"])]
    return out


if __name__ == "__main__":
    rng = random.Random(7)
    items = flagged("held", ["V0", "E4"]) + [i for a in ("RIVAL", "NONE") for i in rng.sample(flagged("held", [a]), 14)]
    items.sort(key=lambda i: (i[1], i[0], i[2], i[3]))
    S = {s["id"]: s for s in json.loads((R1 / "scenarios_held.json").read_text())}
    sample = [{"n": n, "arm": a, "id": sid, "k": k, "token": tok, "split": "dev" if rng.random() < 0.5 else "test"} for n, (a, sid, k, tok) in enumerate(items)]
    (Path(__file__).resolve().parent / "sample.json").write_text(json.dumps(sample, indent=1) + "\n")
    last = None
    for it in sample:
        if it["id"] != last:
            print(f"\n=== {it['id']} NOTES: {S[it['id']]['prompt']}"); last = it["id"]
        msg = (R1 / "outputs/held" / it["arm"] / f"{it['id']}_{it['k']}.txt").read_text()
        pat = it["token"] if it["token"].isdigit() or "." in it["token"] else it["token"][:3]
        ctx = [l.strip() for l in msg.splitlines() if re.search(pat, re.sub(r"(?<=\d),(?=\d{3})", "", l.lower()))]
        print(f"#{it['n']} [{it['arm']}_{it['k']}] token={it['token']!r}: {' || '.join(ctx)[:420]}")
