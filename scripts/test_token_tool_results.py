#!/usr/bin/env python3
"""Tests for token_report.py `tool_results` (tool results over 10000 chars, bounded carry estimate, `tool_results` in --json, ranked lever).

Synthetic sessions only. The result text is a sentinel that must never reach any output: only its length is read.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/agentic-ceo/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import token_report as tr  # noqa: E402
from test_token_lever_rank import rep  # noqa: E402

SENTINEL = "SENTINEL_TOOL_RESULT_BODY"


def ts(m, s=0):
    return f"2026-01-01T00:{m:02d}:{s:02d}Z"


def asst(i, read, tools=None, **kw):
    u = {"input_tokens": 0, "cache_read_input_tokens": read, "output_tokens": 1}
    blocks = [{"type": "tool_use", "id": k, "name": v} for k, v in (tools or {}).items()]
    return {"type": "assistant", "requestId": f"r{i}", "timestamp": ts(i), "message": {"model": "m", "usage": u, "content": blocks}, **kw}


def result(m, chars, content=None, tid="t", **kw):
    body = content if content is not None else (SENTINEL * (chars // len(SENTINEL) + 1))[:chars]
    return {"type": "user", "timestamp": ts(m, 30), "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": body}]}, **kw}


def session(reads, results, tools=None):
    """Assistant turn i has context reads[i] (turn 0 carries the `tools` id -> name tool_use blocks); `results` are user entries."""
    return sorted([asst(i, r, tools if i == 0 else None) for i, r in enumerate(reads)] + results, key=lambda e: e["timestamp"])


def run(entries, main=True, ie=None):
    turns = tr.extract_turns(entries, main=main)
    return tr.tool_results(entries, turns, tr.sum_turns(turns)["input_equivalent"] if ie is None else ie, main=main)


class ToolResults(unittest.TestCase):
    def test_threshold_and_content_shapes(self):
        lst = {"type": "user", "timestamp": ts(1, 40), "message": {"content": [
            {"type": "tool_result", "content": [{"type": "text", "text": "x" * 6000}, {"type": "text", "text": "y" * 6000}]},
            {"type": "tool_result", "content": None}, {"type": "text", "text": "z" * 50000}]}}
        r = run(session([100_000] * 4, [result(1, 10_000), result(1, 10_001), lst]))
        self.assertEqual((r["count"], r["chars"]), (2, 10_001 + 12_000))

    def test_carry_hand_computed(self):
        # 40000 chars = 10000 tokens, arrives after turn 1 (turns 2..9 = 8 left), 0.1 weight: 10000 x 8 x 0.1 = 8000.
        r = run(session([100_000] * 10, [result(1, 40_000)]))
        self.assertEqual((r["count"], r["chars"], r["carry_ie_upper"], r["clamped"]), (1, 40_000, 8000.0, False))

    def test_carry_stops_at_next_compaction(self):
        # context 100k x5 then 30k: the drop is turn 5, so the result is carried by turns 2..4 only: 10000 x 3 x 0.1 = 3000.
        r = run(session([100_000] * 5 + [30_000] * 5, [result(1, 40_000)]))
        self.assertEqual((r["carry_ie_upper"], r["clamped"]), (3000.0, False))

    def test_bash_counts_only_past_the_cap_and_read_other_are_info(self):
        # Bash 40000 chars: only 30000 past the cap = 7500 tok x 8 x 0.1 = 6000. Read 40000: 10000 x 8 x 0.1 = 8000. Unknown id: other, 8000.
        e = session([100_000] * 10, [result(1, 40_000, tid="b"), result(1, 40_000, tid="r"), result(1, 40_000, tid="x"), result(1, 40_000, tid="m")],
                    {"b": "Bash", "r": "Read", "m": "mcp__srv__tool"})
        bt = run(e)["by_tool"]
        self.assertEqual({k: (v["count"], v["chars"], v["carry_ie_upper"]) for k, v in bt.items()},
                         {"bash": (1, 40_000, 6000.0), "read": (1, 40_000, 8000.0), "other": (2, 80_000, 16000.0)})
        self.assertEqual(run(e)["carry_ie_upper"], 30_000.0)
        pw = run(session([100_000] * 10, [result(1, 40_000, tid="p")], {"p": "PowerShell"}))
        self.assertEqual(pw["by_tool"]["bash"]["count"], 1)

    def test_result_after_last_turn_carries_nothing(self):
        self.assertEqual(run(session([100_000] * 3, [result(5, 40_000)]))["carry_ie_upper"], 0.0)

    def test_carry_is_clamped_to_input_eq_and_says_so(self):
        r = run(session([1000] * 10, [result(1, 40_000)]))  # raw carry 8000 > ie 1000
        self.assertEqual((r["carry_ie_upper"], r["clamped"]), (1000.0, True))

    def test_main_skips_sidechain_lines(self):
        e = session([100_000] * 4, [result(1, 40_000, isSidechain=True)])
        self.assertEqual(run(e, main=True)["count"], 0)
        self.assertEqual(run(e, main=False)["count"], 1)


def tres(bash_ie, bash_share, read=0, other=0):
    """tool_results dict shaped like build_report's: Bash carry drives the lever; Read/other counts only add info lines."""
    c = lambda n, ie=0.0: {"count": n, "chars": n * 20_000, "carry_ie_upper": ie}  # noqa: E731
    return {"carry_ie_upper": bash_ie, "share_of_session_ie": bash_share, "bash_share_of_session_ie": bash_share, "count": 3 + read + other,
            "chars": 90_000, "clamped": False, "main": {"count": 3}, "lanes": {"count": 0},
            "by_tool": {"bash": c(3, bash_ie), "read": c(read), "other": c(other)}}


class Wiring(unittest.TestCase):
    def test_read_and_mcp_are_info_lines_not_ranked(self):
        r = {**rep(main_ie=1000.0, lane_ie=1000.0), "tool_results": tres(0.0, 0.0, read=2, other=1)}
        self.assertEqual(tr.lever_ranking(r), [])
        text = "\n".join(tr._gap_tier_lines({**r, "lever_ranking": []}))
        self.assertIn("read with offset/limit", text)
        self.assertIn("check MCP output size", text)
        self.assertNotIn("Lever: cap Bash output", text)

    def test_lever_fires_above_floor_with_estimate_flag_and_tip(self):
        r = {**rep(main_ie=1000.0, lane_ie=1000.0), "tool_results": tres(60.0, 0.06)}
        rank = tr.lever_ranking(r)
        self.assertEqual([(x["lever"], x.get("estimate"), x["saving_ie"]) for x in rank], [(tr.TOOL_LEVER, True, 60.0)])
        text = "\n".join(tr._gap_tier_lines({**r, "lever_ranking": rank}))
        self.assertIn("Lever: cap Bash output (`bashOutputMaxChars`", text)
        self.assertIn("docs/token-cost-tips.md", text)
        self.assertIn("(estimate)", text)

    def test_quiet_below_floor_and_when_muted(self):
        base = {**rep(main_ie=1000.0, lane_ie=1000.0), "tool_results": tres(40.0, 0.04)}
        self.assertEqual(tr.lever_ranking(base), [])
        fired = {**base, "tool_results": tres(500.0, 0.5)}
        self.assertEqual(tr.lever_ranking({**fired, "advice": {"muted": ["tooloutput"]}}), [])

    def test_end_to_end_json_key_lane_sum_and_sentinel_never_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            path.write_text("\n".join(json.dumps(e) for e in session([100_000] * 10, [result(1, 40_000, tid="b"), result(1, 40_000, tid="r")], {"b": "Bash", "r": "Read"})) + "\n")
            sub = Path(tmp) / "s" / "subagents"
            sub.mkdir(parents=True)
            lane = session([100_000] * 10, [result(1, 40_000, tid="b")], {"b": "Bash"})
            (sub / "agent-a.jsonl").write_text("\n".join(json.dumps({**e, "isSidechain": True}) for e in lane) + "\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(tr.main(["--session", str(path), "--json"]), 0)
                tr.main(["--session", str(path)])
            self.assertNotIn(SENTINEL, buf.getvalue())
            report = tr.build_report(str(path), None)
        t = report["tool_results"]
        # main: Bash 6000 + Read 8000; lane: Bash 6000 -> Bash-only 12000 of 200000 session ie = 6%.
        self.assertEqual((t["count"], t["chars"], t["carry_ie_upper"], t["clamped"]), (3, 120_000, 20000.0, False))
        self.assertEqual((t["by_tool"]["bash"]["carry_ie_upper"], t["bash_share_of_session_ie"]), (12000.0, 0.06))
        self.assertEqual((t["main"]["count"], t["lanes"]["count"]), (2, 1))
        self.assertEqual(report["all_subagents"][0]["tool_results"]["count"], 1)
        self.assertLessEqual(t["carry_ie_upper"], report["main"]["input_equivalent"] + report["subagents_totals"]["input_equivalent"])
        self.assertEqual([x["lever"] for x in report["lever_ranking"]], [tr.TOOL_LEVER])  # Bash-only 6% >= 5%


if __name__ == "__main__":
    unittest.main()
