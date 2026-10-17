#!/usr/bin/env python3
"""Tests for scripts/rival_eval.py: scorer, CI math, split hygiene, --changed, quota/cap gates. Offline; no model is called."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rival_eval as r  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.name for p in (REPO / ".claude/skills").iterdir() if (p / "SKILL.md").is_file())


def fake_fixture(root, held, tune, sha_ok=True, name="alpha"):
    """Write a one-skill fixture tree under root; returns the skill name."""
    d = root / "scripts/eval-fixtures/rival" / name
    d.mkdir(parents=True)
    (root / ".claude/skills" / name).mkdir(parents=True)
    (root / ".claude/skills" / name / "SKILL.md").write_text("PERUN skill text")
    (d / "heldout.json").write_text(json.dumps(held))
    (d / "tune.json").write_text(json.dumps(tune))
    (root / "rival.txt").write_text("RIVAL text")
    (d / "rival.json").write_text(json.dumps({"perun": f".claude/skills/{name}/SKILL.md", "rival": {"name": "rv", "path": "rival.txt"},
                                              "heldout_sha256": r.sha((d / "heldout.json").read_bytes()) if sha_ok else "0" * 64}))
    return name


def scen(prefix, n, start=0):
    return [{"id": f"{start + i:02d}", "prompt": f"{prefix} distinct topic number {start + i} about " + " ".join(f"{prefix}word{start + i}x{j}" for j in range(12))} for i in range(n)]


class CiMath(unittest.TestCase):
    def test_constant_scores_collapse(self):
        self.assertEqual(r.boot([1.0] * 10), (1.0, 1.0))
        self.assertEqual(r.boot([0.5] * 10), (0.5, 0.5))

    def test_ci_contains_mean_and_is_reproducible(self):
        v = [1, 1, 1, 0.5, 0.5, 0, 1, 1, 0.5, 1]
        lo, hi = r.boot(v)
        self.assertLessEqual(lo, sum(v) / len(v))
        self.assertGreaterEqual(hi, sum(v) / len(v))
        self.assertEqual((lo, hi), r.boot(v))

    def test_ci_known_extreme(self):
        # 10 scenarios, 5 wins and 5 losses: mean 0.5, interval brackets 0.5 and is not PASS
        lo, hi = r.boot([1.0] * 5 + [0.0] * 5)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)

    def test_pass_needs_lower_bound_above_half(self):
        lo, _ = r.boot([1.0] * 9 + [0.0])
        self.assertGreater(lo, 0.5)
        lo, _ = r.boot([1.0] * 7 + [0.0] * 3)
        self.assertLessEqual(lo, 0.5 + 1e-9)


class Scorer(unittest.TestCase):
    def test_order_score(self):
        self.assertEqual(r.order_score("1", "PERUN"), 1.0)
        self.assertEqual(r.order_score("2", "PERUN"), 0.0)
        self.assertEqual(r.order_score("1", "RIVAL"), 0.0)
        self.assertEqual(r.order_score("2", "RIVAL"), 1.0)
        self.assertEqual(r.order_score("tie", "RIVAL"), 0.5)

    def test_scenario_score_split_is_half(self):
        self.assertEqual(r.scenario_score([1.0, 0.0]), 0.5)
        self.assertEqual(r.scenario_score([1.0, 1.0]), 1.0)
        self.assertEqual(r.scenario_score([0.0, 0.0]), 0.0)
        self.assertEqual(r.scenario_score([1.0, 0.5]), 0.5)  # a win plus a tie is not a win
        self.assertEqual(r.scenario_score([0.5, 0.5]), 0.5)

    def test_slot1_rate(self):
        self.assertEqual(r.slot1_rate(["1", "2", "tie", None]), 0.5)
        self.assertEqual(r.slot1_rate(["1", "1", "1", "2"]), 0.75)
        self.assertIsNone(r.slot1_rate(["tie", None]))

    def test_summary_row(self):
        row = r.summary([dict(skill="s", rival="r", n=10, win_rate=0.75, ci95=[0.5, 0.9], verdict="FAIL", spend_usd=0)])
        self.assertIn("| s | r | 10 | 0.750 [0.500, 0.900] | FAIL | $0.00 |", row)

    def test_judge_is_never_the_generator(self):
        self.assertNotIn(r.GEN_MODEL, r.JUDGES)
        self.assertNotEqual(r.JUDGE_MODEL, r.TIE_MODEL)


class EndToEnd(unittest.TestCase):
    """run_skill on a throwaway fixture with the model calls replaced by deterministic fakes."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.name = fake_fixture(self.tmp, scen("held", 10, 10), scen("tune", 5))
        self.p = [mock.patch.object(r, "ROOT", self.tmp), mock.patch.object(r, "FIX", self.tmp / "scripts/eval-fixtures/rival")]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def fake_chat(self, judge_rule, calls):
        def chat(model, system, user, **kw):
            calls.append(model)
            if system == r.JUDGE_SYSTEM:
                return json.dumps({"verdict": judge_rule(model, user), "reason": "x"})
            return ("PERUN-ANSWER" if "PERUN skill text" in system else "RIVAL-ANSWER") + " for " + user[-20:]
        return chat

    def test_perun_always_better_passes_and_judge_is_healthy(self):
        calls = []

        def rule(model, user):  # picks the response containing PERUN-ANSWER, whichever slot it is in
            return "1" if user.index("PERUN-ANSWER") < user.index("RIVAL-ANSWER") else "2"
        with mock.patch.object(r, "chat", self.fake_chat(rule, calls)):
            res = r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertEqual((res["n"], res["win_rate"], res["verdict"], res["spend_usd"]), (10, 1.0, "PASS", 0.0))
        self.assertEqual((res["judge"], res["slot1_rate"]), (r.JUDGE_MODEL, {r.JUDGE_MODEL: 0.5}))
        self.assertNotIn(r.TIE_MODEL, calls)
        self.assertEqual(res["ci95"], [1.0, 1.0])

    def test_position_biased_judge_is_dropped_and_fallback_judges(self):
        calls = []

        def rule(model, user):  # primary always says "Response 1"; fallback is order-consistent
            if model == r.JUDGE_MODEL:
                return "1"
            return "1" if user.index("PERUN-ANSWER") < user.index("RIVAL-ANSWER") else "2"
        with mock.patch.object(r, "chat", self.fake_chat(rule, calls)):
            res = r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertEqual((res["judge"], res["slot1_rate"][r.JUDGE_MODEL], res["slot1_rate"][r.TIE_MODEL]), (r.TIE_MODEL, 1.0, 0.5))
        self.assertEqual((res["win_rate"], res["verdict"]), (1.0, "PASS"))

    def test_every_judge_biased_gives_no_verdict(self):
        with mock.patch.object(r, "chat", self.fake_chat(lambda m, u: "1", [])):  # always "Response 1"
            res = r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertEqual((res["n"], res["judge"], res.get("verdict")), (0, None, None))
        self.assertTrue(any("slot-1 rate" in e for e in res["errors"]))
        self.assertIn("no data", r.summary([res]))

    def test_swap_both_orders_are_judged_and_split_is_a_tie(self):
        seen = []

        def rule(model, user):  # scenario 13: judge says "Response 1" in both orders (a split); the rest are order-consistent
            seen.append(user.index("PERUN-ANSWER") < user.index("RIVAL-ANSWER"))
            if "number 13 about" in user:
                return "1"
            return "1" if seen[-1] else "2"
        with mock.patch.object(r, "chat", self.fake_chat(rule, [])):
            res = r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 1, 0.5)
        self.assertEqual(seen.count(True), seen.count(False))  # every pair shown in both orders
        self.assertEqual(res["judge"], r.JUDGE_MODEL)  # slot-1 rate 0.55 is inside 0.4-0.6
        self.assertEqual(sorted(res["per_scenario"].values()), [0.5] + [1.0] * 9)  # the split is a tie, never a win
        self.assertEqual(res["win_rate"], 0.95)

    def test_tune_split_never_gives_a_verdict(self):
        def rule(model, user):  # healthy, order-consistent judge: Perun wins both orders
            return "1" if user.index("PERUN-ANSWER") < user.index("RIVAL-ANSWER") else "2"
        with mock.patch.object(r, "chat", self.fake_chat(rule, [])):
            res = r.run_skill(self.name, "tune", "pcss", self.tmp / "out", 2, 0.5)
        self.assertIn("tuning only", res["verdict"])

    def test_outputs_and_verdicts_are_cached(self):
        calls = []
        with mock.patch.object(r, "chat", self.fake_chat(lambda m, u: "tie", calls)):
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
            n = len(calls)
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertEqual(len(calls), n)

    def test_changed_skill_text_invalidates_cache(self):
        calls = []
        with mock.patch.object(r, "chat", self.fake_chat(lambda m, u: "tie", calls)):
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
            n = len(calls)
            (self.tmp / ".claude/skills" / self.name / "SKILL.md").write_text("PERUN skill text v2")
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertGreater(len(calls), n)

    def test_heldout_refused_when_hygiene_fails(self):
        (self.tmp / "scripts/eval-fixtures/rival" / self.name / "heldout.json").write_text(json.dumps(scen("held", 10, 10) + scen("extra", 1, 30)))
        with self.assertRaises(SystemExit) as e:
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertIn("heldout_sha256", str(e.exception))

    def test_failed_generation_is_reported_not_scored(self):
        def chat(model, system, user, **kw):
            raise RuntimeError("boom")
        with mock.patch.object(r, "chat", chat):
            res = r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertEqual(res["n"], 0)
        self.assertNotIn("win_rate", res)
        self.assertTrue(res["errors"])


class SplitHygiene(unittest.TestCase):
    def test_committed_fixtures_cover_every_skill_and_are_clean(self):
        self.assertEqual(r.skills(), SKILLS)
        for s in SKILLS:
            self.assertEqual(r.check_split(s), [], s)

    def test_every_fixture_points_at_real_inputs(self):
        for s in SKILLS:
            cfg = r.config(s)
            self.assertTrue((REPO / cfg["perun"]).is_file(), s)
            rv = cfg["rival"]
            self.assertTrue("url" in rv or (REPO / rv["path"]).is_file(), s)
            self.assertTrue(rv["url"].startswith("https://raw.") if "url" in rv else True, s)
            for sc in r.load_scenarios(s, "heldout") + r.load_scenarios(s, "tune"):
                self.assertTrue(sc["prompt"].strip(), (s, sc["id"]))
            self.assertGreaterEqual(len(r.load_scenarios(s, "heldout")), r.MIN_HELDOUT, s)

    def check(self, held, tune, sha_ok=True):
        tmp = Path(tempfile.mkdtemp())
        name = fake_fixture(tmp, held, tune, sha_ok)
        with mock.patch.object(r, "ROOT", tmp), mock.patch.object(r, "FIX", tmp / "scripts/eval-fixtures/rival"):
            return r.check_split(name)

    def test_clean_split_passes(self):
        self.assertEqual(self.check(scen("held", 10, 10), scen("tune", 5)), [])

    def test_shared_id_and_duplicate_prompt_fail(self):
        held, tune = scen("held", 10, 10), scen("tune", 5, 8)  # ids 08..12 collide with 10..12
        self.assertTrue(any("share an id" in b for b in self.check(held, tune)))
        held, tune = scen("held", 10, 10), scen("tune", 5)
        tune[0]["prompt"] = held[0]["prompt"]
        bad = self.check(held, tune)
        self.assertTrue(any("overlaps a tune prompt" in b for b in bad))

    def test_edited_heldout_without_hash_update_fails(self):
        self.assertTrue(any("heldout_sha256" in b for b in self.check(scen("held", 10, 10), scen("tune", 5), sha_ok=False)))

    def test_too_small_sets_fail(self):
        bad = self.check(scen("held", 9, 10), scen("tune", 4))
        self.assertTrue(any("heldout n=9" in b for b in bad) and any("tune n=4" in b for b in bad))


class Gates(unittest.TestCase):
    def claude_out(self, util, cost):
        ev = {"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": {"five_hour": {"utilization": util}, "seven_day": {"utilization": 0}}}}
        return "\n".join(json.dumps(x) for x in (ev, {"type": "result", "result": "ok", "total_cost_usd": cost})) + "\n"

    def test_quota_at_or_above_point_eight_stops_before_the_next_call(self):
        st = r.State(0.5)
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(stdout=self.claude_out(0.8, 0.01))) as run:
            r.claude_call("s", "u", st)
            self.assertEqual(st.util, 0.8)
            with self.assertRaises(r.Stop):
                r.claude_call("s", "u", st)
            self.assertEqual(run.call_count, 1)

    def test_quota_below_threshold_keeps_going_and_cost_accumulates(self):
        st = r.State(0.5)
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(stdout=self.claude_out(0.79, 0.02))):
            r.claude_call("s", "u", st)
            r.claude_call("s", "u", st)
        self.assertAlmostEqual(st.spent, 0.04)

    def test_cap_reserve_stops_run(self):
        st = r.State(0.5)
        st.spent = 0.45
        with self.assertRaises(r.Stop):
            r.claude_call("s", "u", st)

    def test_claude_call_has_no_tools_and_uses_cheap_model(self):
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(stdout=self.claude_out(0, 0))) as run:
            r.claude_call("s", "u", r.State(0.5))
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertEqual(cmd[cmd.index("--model") + 1], r.CLAUDE_MODEL)

    def test_pcss_error_never_leaks_the_key(self):
        with mock.patch.dict(os.environ, {"PCSS_KEY": "sekret-value-123"}), \
                mock.patch.object(r.urllib.request, "urlopen", side_effect=OSError("auth failed for sekret-value-123")), \
                mock.patch.object(r.time, "sleep"):
            with self.assertRaises(RuntimeError) as e:
                r.chat("m", "s", "u")
        self.assertNotIn("sekret-value-123", str(e.exception))

    def test_chat_strips_think_block(self):
        body = json.dumps({"choices": [{"message": {"content": "<think>hidden</think>answer"}}]}).encode()
        resp = mock.Mock(read=lambda: body)
        with mock.patch.dict(os.environ, {"PCSS_KEY": "k"}), mock.patch.object(r.json, "load", return_value=json.loads(body)), \
                mock.patch.object(r.urllib.request, "urlopen", return_value=resp):
            self.assertEqual(r.chat("m", "s", "u"), "answer")


class Changed(unittest.TestCase):
    def git(self, d, *a):
        subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True,
                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})

    def test_only_touched_skills_are_scored(self):
        tmp = Path(tempfile.mkdtemp())
        a = fake_fixture(tmp, scen("held", 10, 10), scen("tune", 5), name="alpha")
        b = fake_fixture(tmp, scen("held", 10, 10), scen("tune", 5), name="beta")
        self.git(tmp, "init", "-q", "-b", "main")
        self.git(tmp, "add", "-A")
        self.git(tmp, "commit", "-qm", "base")
        with mock.patch.object(r, "ROOT", tmp), mock.patch.object(r, "FIX", tmp / "scripts/eval-fixtures/rival"):
            self.assertEqual(r.changed_skills("HEAD"), [])
            (tmp / ".claude/skills" / a / "SKILL.md").write_text("changed")  # working-tree edit
            (tmp / ".claude/skills" / "unrelated").mkdir()
            (tmp / ".claude/skills/unrelated/SKILL.md").write_text("x")  # not a fixture skill
            self.assertEqual(r.changed_skills("HEAD"), [a])
            self.git(tmp, "add", "-A")
            self.git(tmp, "commit", "-qm", "edit")
            (tmp / "scripts/eval-fixtures/rival" / b / "tune.json").write_text(json.dumps(scen("t2", 5)))  # fixture edit
            self.assertEqual(r.changed_skills("HEAD~1"), [a, b])

    def test_unknown_base_fails_closed(self):
        with self.assertRaises(SystemExit):
            r.changed_skills("no-such-ref-xyz")


class Cli(unittest.TestCase):
    def test_check_subcommand_is_clean_on_the_repo(self):
        p = subprocess.run([sys.executable, str(REPO / "scripts/rival_eval.py"), "check"], capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_premerge_hook_skips_without_a_key_and_never_fails(self):
        env = {k: v for k, v in os.environ.items() if k != "PCSS_KEY"}
        p = subprocess.run(["bash", str(REPO / "scripts/rival-eval-premerge.sh")], capture_output=True, text=True,
                           env={**env, "PCSS_ENV_FILE": "/nonexistent/.env", "RIVAL_EVAL_BASE": "HEAD"})
        self.assertEqual(p.returncode, 0)
        self.assertIn("skipped", p.stdout + p.stderr)


class ReviewFixes(unittest.TestCase):
    """Regression tests for the PR review findings: key check, cap reserve, quota fail-closed, judge health, cache keys, freeze."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.name = fake_fixture(self.tmp, scen("held", 10, 10), scen("tune", 5))
        self.p = [mock.patch.object(r, "ROOT", self.tmp), mock.patch.object(r, "FIX", self.tmp / "scripts/eval-fixtures/rival")]
        for p in self.p:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.p])

    def fake_chat(self, rule, log):
        def chat(model, system, user, **kw):
            log.append(("judge" if system == r.JUDGE_SYSTEM else "gen", model, user))
            if system == r.JUDGE_SYSTEM:
                return json.dumps({"verdict": rule(model, user), "reason": "x"})
            return ("PERUN-ANSWER" if "PERUN skill text" in system else "RIVAL-ANSWER") + " for " + user[-20:]
        return chat

    @staticmethod
    def perun_wins(model, user):
        return "1" if user.index("PERUN-ANSWER") < user.index("RIVAL-ANSWER") else "2"

    def claude_ok(self, util=0.1, cost=0.01):
        ev = {"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": {"five_hour": {"utilization": util}}}}
        return "\n".join(json.dumps(x) for x in (ev, {"type": "result", "result": "ok", "total_cost_usd": cost})) + "\n"

    def test_1_run_needs_the_judge_key_even_with_the_claude_generator(self):
        with mock.patch.object(r, "load_key", side_effect=SystemExit("no key")) as lk, mock.patch.object(r, "run_skill") as rs:
            with self.assertRaises(SystemExit):
                r.main(["run", "--gen", "claude", "--skills", self.name])
        self.assertEqual((lk.call_count, rs.call_count), (1, 0))

    def test_2_cap_counts_in_flight_reserves_and_timeouts_are_charged(self):
        st = r.State(0.15)

        def nested(*a, **k):  # a second call while the first is in flight must not fit under the cap
            self.assertAlmostEqual(st.reserved, 0.10)
            with self.assertRaises(r.Stop):
                r.claude_call("s", "u", st)
            return mock.Mock(stdout=self.claude_ok())
        with mock.patch.object(subprocess, "run", side_effect=nested):
            r.claude_call("s", "u", st)
        self.assertEqual(st.reserved, 0)
        st = r.State(0.5)
        with mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("claude", 900)):
            with self.assertRaises(RuntimeError):
                r.claude_call("s", "u", st)
        self.assertEqual((st.spent, st.reserved), (0.10, 0))  # unknown spend: the whole reserve is charged
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError("claude")):
            with self.assertRaises(RuntimeError):
                r.claude_call("s", "u", st)
        self.assertEqual((st.spent, st.reserved), (0.10, 0))

    def test_3_no_utilization_reading_fails_closed(self):
        st = r.State(0.5)
        out = json.dumps({"type": "result", "result": "ok", "total_cost_usd": 0.02}) + "\n"
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(stdout=out)) as run:
            with self.assertRaises(r.Stop):
                r.claude_call("s", "u", st)
            self.assertAlmostEqual(st.spent, 0.02)  # the spend is still recorded
            with self.assertRaises(r.Stop):  # and the quota now reads as exhausted: no further call
                r.claude_call("s", "u", st)
            self.assertEqual(run.call_count, 1)

    def test_4_a_judge_with_no_decisive_verdicts_is_unhealthy_and_falls_back(self):
        def rule(model, user):
            return "tie" if model == r.JUDGE_MODEL else self.perun_wins(model, user)
        with mock.patch.object(r, "chat", self.fake_chat(rule, [])):
            res = r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        self.assertEqual((res["judge"], res["slot1_rate"][r.JUDGE_MODEL], res["verdict"]), (r.TIE_MODEL, None, "PASS"))
        with mock.patch.object(r, "chat", self.fake_chat(lambda m, u: "tie", [])):
            res = r.run_skill(self.name, "heldout", "pcss", self.tmp / "out2", 2, 0.5)
        self.assertEqual((res["n"], res["judge"], res.get("verdict")), (0, None, None))

    def test_5_cache_key_covers_scenario_rubric_and_judge(self):
        log = []
        with mock.patch.object(r, "chat", self.fake_chat(self.perun_wins, log)):
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
            n = len(log)
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
            self.assertEqual(len(log), n)  # unchanged inputs: all cached
            with mock.patch.object(r, "JUDGE_SYSTEM", r.JUDGE_SYSTEM + " Be strict."):
                r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
            self.assertEqual([k for k, *_ in log[n:]].count("judge"), 20)  # new rubric: every verdict re-judged, answers reused
            self.assertNotIn("gen", [k for k, *_ in log[n:]])
            n = len(log)
            held = scen("held", 10, 10)
            held[0]["prompt"] += " plus a changed requirement"
            (self.tmp / "scripts/eval-fixtures/rival" / self.name / "heldout.json").write_text(json.dumps(held))
            cfgp = self.tmp / "scripts/eval-fixtures/rival" / self.name / "rival.json"
            cfg = json.loads(cfgp.read_text())
            cfg["heldout_sha256"] = r.digest(self.name)
            cfgp.write_text(json.dumps(cfg))
            r.run_skill(self.name, "heldout", "pcss", self.tmp / "out", 2, 0.5)
        kinds = [k for k, *_ in log[n:]]
        self.assertEqual((kinds.count("gen"), kinds.count("judge")), (2, 2))  # only the edited scenario is regenerated and re-judged

    def test_6_frozen_heldout_needs_force_to_overwrite(self):
        d = self.tmp / "scripts/eval-fixtures/rival" / self.name
        cfg = json.loads((d / "rival.json").read_text())
        cfg["writer"] = {"brief": "brief.txt", "seeds": "seeds.txt"}
        (d / "rival.json").write_text(json.dumps(cfg))
        (self.tmp / "brief.txt").write_text("Write {N} scenarios.")
        (self.tmp / "seeds.txt").write_text("01 alpha\n02 beta\n")
        before = (d / "heldout.json").read_bytes()
        writer = mock.Mock(return_value=json.dumps([{"id": "01", "prompt": "new one"}, {"id": "02", "prompt": "new two"}]))
        with mock.patch.object(r, "chat", writer):
            with self.assertRaises(SystemExit):
                r.write_set(self.name, "heldout")
            self.assertEqual((writer.call_count, (d / "heldout.json").read_bytes()), (0, before))
            r.write_set(self.name, "heldout", force=True)
        self.assertEqual([x["id"] for x in json.loads((d / "heldout.json").read_text())], ["h01", "h02"])
        self.assertEqual(json.loads((d / "rival.json").read_text())["heldout_sha256"], r.digest(self.name))

    def test_7_referenced_files_are_part_of_the_frozen_hash(self):
        d = self.tmp / "scripts/eval-fixtures/rival" / self.name
        (self.tmp / "change.patch").write_text("--- a\n+++ b\n")
        held = scen("held", 9, 10) + [{"id": "19", "file": "change.patch"}]
        (d / "heldout.json").write_text(json.dumps(held))
        cfg = json.loads((d / "rival.json").read_text())
        cfg["heldout_sha256"] = r.digest(self.name)
        (d / "rival.json").write_text(json.dumps(cfg))
        self.assertEqual(r.check_split(self.name), [])
        (self.tmp / "change.patch").write_text("--- a\n+++ b\n+swapped\n")  # json untouched, referenced file swapped
        self.assertTrue(any("heldout_sha256" in b for b in r.check_split(self.name)))


if __name__ == "__main__":
    unittest.main()
