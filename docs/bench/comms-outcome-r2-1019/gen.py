#!/usr/bin/env python3
"""Writes the r2 held-out scenarios (scenarios_held.json): (kind, domain) pairs disjoint from r1 tune and held, shuffled with seed 4019,
every pair tried up to 4 times with r1's writer brief and r1's validity checks (literals occur in the notes, >= 4 figures, gold figures in the
notes, gold action is not the drafting task); the first MAX valid ones are kept. usage: gen.py"""
import concurrent.futures as cf, json, random, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fabjudge as f  # noqa: E402  (sets bench.D to this directory, patches the extractor)
import fixed2  # noqa: E402
b, D, R1, MAX = f.b, f.D, f.R1, 80
LEDGER = "ledger.jsonl"


def make(k, d, sid, brief):
    for att in range(4):
        try:
            j = b.parse_json(b.call("write", b.WRITER, "You write synthetic test scenarios.", brief.format(kind_desc=b.KINDS[k], domain=d, seed=f"{sid}-{att}"), 0.9, id=sid, att=att))
        except RuntimeError:
            continue
        if not j or not all(isinstance(j.get(x), str) and j[x].strip() for x in ("prompt", "recipient", "number_literal", "owner_literal", "deadline_literal", *b.QS)) or not isinstance(j.get("facts"), list):
            continue
        facts = [x for x in dict.fromkeys([j["number_literal"], j["owner_literal"], j["deadline_literal"], *map(str, j["facts"])]) if x.strip()]
        sc = {"id": sid, "split": "held", "kind": k, "domain": d, "prompt": j["prompt"], "recipient": j["recipient"], **{x: j[x] for x in b.QS}, "facts": facts}
        if not (b.dropped(sc["prompt"], facts) or len(facts) < 4 or len(b._numbers(sc["prompt"])) < 4 or fixed2.bad(sc)):
            return sc
    return None


if __name__ == "__main__":
    f.LEDGER[0] = LEDGER
    taken = {(s["kind"], s["domain"]) for sp in ("tune", "held") for s in json.loads((R1 / f"scenarios_{sp}.json").read_text())}
    combos = [(k, d) for d in b.DOMAINS for k in b.KINDS if (k, d) not in taken]
    random.Random(4019).shuffle(combos)
    brief = (D / "prompts/writer_brief.txt").read_text()
    with cf.ThreadPoolExecutor(b.JOBS) as ex:
        res = list(ex.map(lambda i: make(*combos[i], f"held{i + 1:03d}", brief), range(len(combos))))
    ok = [r for r in res if r][:MAX]
    for n, r in enumerate(ok, 1):
        r["id"] = f"held{n:02d}"
    print(f"{len(ok)}/{len(combos)} scenarios valid", {k: sum(r["kind"] == k for r in ok) for k in b.KINDS})
    (D / "scenarios_held.json").write_text(json.dumps(ok, indent=1) + "\n")
