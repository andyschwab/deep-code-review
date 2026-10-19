#!/usr/bin/env python3
"""Offline tests for docs/bench/comms-outcome-r2-1019: the real-fabrication judge plumbing, its committed validation, the held-out scenarios and the frozen arm texts.

No PCSS call is made (the judge's network call is stubbed). Each test fails if the guard drifts from the preregistered definition.
"""
import json, sys
from pathlib import Path

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent.parent / "docs/bench/comms-outcome-r2-1019"
sys.path.insert(0, str(D))
import fabjudge as f

b = f.b


def stub(text):
    """Make fabjudge.judge read `text` as the model reply instead of calling PCSS."""
    b.cached = lambda p, make: text


def test_regex_flags_a_derived_figure_the_judge_decides_on():
    assert f.flags("B costs 0.7M more", "A costs 2.4M, B costs 3.1M") == ["0.7"]
    assert f.flags("A costs $2,400,000", "A costs 2.4M") == ["2400000"]  # reformatting also flagged: why a judge is needed


def test_no_flagged_token_means_no_call_and_not_fabricated():
    assert f.judge("notes 5", "msg 5", []) == {}
    assert f.real_fab("msg 5", "notes 5") == (0, 0)


def test_one_fabricated_token_makes_the_message_fabricated():
    stub('{"checks": "a; b", "labels": {"0.7": "supported", "thu": "fabricated"}}')
    assert f.real_fab("B is 0.7M more, decide Thursday", "B 3.1M A 2.4M, decide Friday") == (1, 0)
    stub('{"checks": "x", "labels": {"0.7": "supported"}}')
    assert f.real_fab("B is 0.7M more", "B 3.1M A 2.4M") == (0, 0)


def test_malformed_checks_does_not_void_labels_and_unlabelled_is_counted():
    stub('{"checks": ["a", "b"], "labels": {"0.7": "supported"}}')  # invalid JSON overall (list in a string slot)
    assert f.judge("A 2.4M B 3.1M", "0.7 and 9", ["0.7", "9"]) == {"0.7": "supported"}
    assert f.real_fab("0.7 and 9", "A 2.4M B 3.1M") == (0, 1)
    stub('{"labels": {"0.7": "maybe"}}')
    assert f.judge("A 2.4M B 3.1M", "0.7", ["0.7"]) == {}


def test_committed_validation_clears_the_preregistered_bar():
    rows = [json.loads(l) for l in (D / "validation.jsonl").read_text().splitlines()]
    test = [r for r in rows if r["split"] == "test"][-1]
    assert test["accuracy"] >= 0.90 and test["recall"] >= 0.75 and test["unlabelled"] == 0
    lab = json.loads((D / "labels.json").read_text())
    sample = json.loads((D / "sample.json").read_text())
    assert len(sample) == len(lab) == 91 and {str(i["n"]) for i in sample} == set(lab)
    assert sum(v["label"] == "F" for v in lab.values()) == 11


def test_held_scenarios_are_fresh_and_valid():
    S = json.loads((D / "scenarios_held.json").read_text())
    r1 = {(s["kind"], s["domain"]) for sp in ("tune", "held") for s in json.loads((f.R1 / f"scenarios_{sp}.json").read_text())}
    assert len(S) >= 60 and len({s["id"] for s in S}) == len(S)
    assert not {(s["kind"], s["domain"]) for s in S} & r1
    for s in S:
        assert not b.dropped(s["prompt"], s["facts"]) and not f.fixed2.bad(s), s["id"]


def test_frozen_arm_texts_match_r1():
    for a in ("V0", "E4", "reader", "grader", "writer_brief"):
        assert (D / f"prompts/{a}.txt").read_bytes() == (f.R1 / f"prompts/{a}.txt").read_bytes(), a


def test_report_keep_rule_constants():
    import report
    assert (report.MARGIN, report.WORDS_X) == (0.02, 1.25)


def test_committed_verdict_follows_from_committed_scores():
    S = json.loads((D / "per_scenario_held.json").read_text())
    col = lambda a, k: [r[k] for r in S[a]]
    acc, fab = b.paired(col("E4", "acc"), col("V0", "acc")), b.paired(col("E4", "real_fab"), col("V0", "real_fab"))
    keep = acc[1] > 0 and fab[2] <= 0.02 and sum(col("E4", "words")) <= 1.25 * sum(col("V0", "words"))
    assert len(S["V0"]) >= 60 and ("-> KEEP" if keep else "-> REVERT") in (D / "report_held.txt").read_text().splitlines()[-1]
    assert not keep  # REVERT: the real-fab upper bound (+0.033) is above the +0.02 margin


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print(f"{sum(n.startswith('test_') for n in globals())}/{sum(n.startswith('test_') for n in globals())} passed")
