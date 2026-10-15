#!/usr/bin/env python3
"""Bench gate for the static pass of vacuous_test_gate.py: on the 20 vacuous + 20 genuine fixture tests it must
catch >= 15 vacuous files with <= 1 false positive, with no model and no report. Run: python3 scripts/test_vacuous_static.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".claude", "skills", "agentic-delivery", "scripts"))
import vacuous_test_gate as g  # noqa: E402

FIX = os.path.join(ROOT, "scripts", "eval-fixtures", "vacuous-static")
manifest = json.load(open(os.path.join(FIX, "manifest.json")))
flagged = {m["file"]: bool([r for r in g.static_check(os.path.join(FIX, m["file"])) if r[0] == "VACUOUS"]) for m in manifest}
unparsed = [m["file"] for m in manifest if any(r[0] == "COULD_NOT_CHECK" for r in g.static_check(os.path.join(FIX, m["file"])))]
vac = [m["file"] for m in manifest if m["vacuous"]]
gen = [m["file"] for m in manifest if not m["vacuous"]]
recall, fp = sum(flagged[f] for f in vac), sum(flagged[f] for f in gen)
print(f"recall {recall}/{len(vac)}  false-positives {fp}/{len(gen)}")
assert (len(vac), len(gen)) == (20, 20) and not unparsed, (len(vac), len(gen), unparsed)
assert recall >= 15 and fp <= 1, f"bar not met: recall {recall}/20 (need >= 15), FP {fp}/20 (need <= 1)"
print("ok")
