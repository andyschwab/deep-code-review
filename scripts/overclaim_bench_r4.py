#!/usr/bin/env python3
"""Over-claim bench R4: a claim-first rule in Perun's text vs obra/superpowers on the R3 corpus. Preregistered, free (PCSS), no judge.

Thin layer over the R3 driver (which reuses the R2 driver): same cases, prompts, scorer and pinned rival text; three arms
(perun_old, perun_new with the R4 rule, superpowers), a fresh bootstrap seed and a different keep rule in verdict().
See docs/bench/overclaim-r4-1021/PREREGISTERED.md.

  overclaim_bench_r4.py [--model M] [--write]   generate (cached), score, bootstrap, print; --write saves results-<model>.json + a ledger line
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overclaim_bench as O  # noqa: E402
import overclaim_bench_r3 as R3  # noqa: E402

D = O.ROOT / "docs/bench/overclaim-r4-1021"
ARMS = ("perun_old", "perun_new", "superpowers")
SEED, UNDER_MARGIN, MAX_UNPARSED = 2, 0.05, 3  # preregistered; R3 used bootstrap seed 1


def verdict(arms, contrasts=None):
    """Preregistered verdict from results["arms"] (primary model, point estimates).
    INVALID if any arm has > MAX_UNPARSED unparsed lines; KEEP iff perun_new over-claim <= superpowers' AND < perun_old's AND
    perun_new under-claim exceeds superpowers' and perun_old's by <= UNDER_MARGIN; else REVERT. `contrasts` is unused (R3 signature)."""
    n, sp, old = arms["perun_new"], arms["superpowers"], arms["perun_old"]
    g = {"under_vs_superpowers": n["under_rate"] - sp["under_rate"], "under_vs_perun_old": n["under_rate"] - old["under_rate"]}
    ok = n["over_rate"] <= sp["over_rate"] + 1e-9 and n["over_rate"] < old["over_rate"] - 1e-9 and all(v <= UNDER_MARGIN + 1e-9 for v in g.values())
    v = "INVALID" if any(a["unparsed"] > MAX_UNPARSED for a in arms.values()) else "KEEP" if ok else "REVERT"
    return {"verdict": v, "over_new_minus_superpowers": n["over_rate"] - sp["over_rate"], "over_new_minus_old": n["over_rate"] - old["over_rate"], "guardrail": g}


def main(argv=None):
    R3.D, R3.ARMS, R3.verdict = D, ARMS, verdict
    O.boot_ci, O.boot_diff = functools.partial(O.boot_ci, seed=SEED), functools.partial(O.boot_diff, seed=SEED)
    R3.main(argv)


if __name__ == "__main__":
    main()
