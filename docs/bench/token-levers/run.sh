#!/usr/bin/env bash
# Offline, free, deterministic: run token_report.py on the synthetic fixture and assert the levers it finds, their order and amounts.
# Pinned numbers come from the fixture arithmetic (see gen.py); if token_report's estimators change on purpose, rerun and update them here.
# The "250" in the lane-cap lever name is read from this repo's shipped template (agentic-delivery/templates/operating-layer.settings.json, LANE_TOOL_CAP); run from a checkout that has it.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
report="$here/../../../.claude/skills/agentic-ceo/scripts/token_report.py"
python3 "$report" --session "$here/session.jsonl" --json | python3 -I -c '
import json, sys
r = json.load(sys.stdin)
rank = [(x["lever"], x["saving_ie"], x["share_of_session_ie"]) for x in r["lever_ranking"]]
want = [("pin main cache to 1h", 1284000.0, 0.3526),
        ("lower LANE_TOOL_CAP below 250", 475606.25, 0.1306),
        ("auto-compact at 200000", 217575.0, 0.0597),
        ("orchestrator tier", None, None)]
assert rank == want, f"lever ranking drifted:\n got  {rank}\n want {want}"
i, a, t = r["idle_rewrites"], r["auto_compact"], r["lane_tail"]
assert (i["idle_rewrite_share"], i["idle_rewrite_saving_share_of_main_ie"]) == (0.8514, 0.5069), i
assert (a["compactions"], a["saving_share_of_main_ie"]) == (1, 0.0859), a
assert (t["lanes_over_shipped_cap"], t["tail_share_over_shipped_cap"], t["p90_tool_calls"]) == (1, 0.4289, 600), t
assert r["orchestration_flag"] and r["subagents_count"] == 4, "orchestration flag or lane count drifted"
print("token-levers: ok (4 levers, ranked; " + ", ".join(f"{n} {s}" for n, _, s in rank if s) + " of session input-eq)")
'
python3 "$report" --session "$here/session.jsonl" | grep -q "Top levers (est. upper-bound saving, not a bill" || { echo "FAIL: text report has no Top levers block"; exit 1; }
