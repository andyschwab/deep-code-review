#!/usr/bin/env python3
"""Regenerate docs/bench/overclaim-r4-1021/per-case-labels.json (case id -> label list, no generated text) from the local generation cache.

Reads only the cache the R4 run wrote (OVERCLAIM_CACHE or .bench-cache/overclaim); a cache miss raises instead of calling a model, so this never
makes a network call to PCSS. Deterministic: same cache -> same bytes. The rival text is read from its cached, hash-checked copy.

  overclaim_r4_labels.py        write per-case-labels.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overclaim_bench as O  # noqa: E402
import overclaim_bench_r3 as R3  # noqa: E402
import overclaim_bench_r4 as R  # noqa: E402

MODELS = ("Mistral-Small-3.2:24b", "Qwen3.5-397B-A17B")  # primary, direction-only: the order of the results files


def _no_call(*_a, **_k):
    raise RuntimeError("cache miss: refusing to call a model")


def cached_arm_text(arm):
    """Skill text for an arm without any fetch: Perun arms are frozen files, the rival text must already sit in the hash-checked cache."""
    if arm != "superpowers":
        return R3.arm_text(arm)
    f = O.CACHE / "rivals" / f"{arm}.md"
    if not f.exists():
        raise RuntimeError(f"cache miss: {f.name} (refusing to fetch)")
    t = f.read_text()
    if hashlib.sha256(t.encode()).hexdigest() != O.RIVAL_SHA256[arm]:
        raise RuntimeError(f"{arm}: cached text does not match the preregistered sha256")
    return t


def build():
    """{model: {arm: {case_id: [label per item]}}} scored from cached generations; raises RuntimeError("cache miss ...") on any miss, no network."""
    R3.D, R3.ARMS = R.D, R.ARMS  # same wiring as R.main(), without touching the frozen driver
    O.arm_text, O.chat = cached_arm_text, _no_call
    cases = O.parse_cases((R.D / "cases.txt").read_text())
    out = {}
    for m in MODELS:
        O.MODEL = m
        out[m] = {a: {c["id"]: O.score_case(c, O.generate(a, c)["text"]) for c in cases} for a in R.ARMS}
    return out


def dumps(labels):
    """Canonical serialization of build()'s result (compact separators, trailing newline)."""
    return json.dumps(labels, separators=(",", ":")) + "\n"


def main(out=R.D / "per-case-labels.json"):
    """Write the labels to `out` only after build() succeeded (a cache miss leaves no file)."""
    out.write_text(dumps(build()))


if __name__ == "__main__":
    main()
