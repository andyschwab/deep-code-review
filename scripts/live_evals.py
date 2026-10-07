#!/usr/bin/env python3
"""Live eval harness: run skill evals against any OpenAI-compatible chat endpoint.

Env (no vendor or model id is hardcoded; the key is never printed or written):
  LLM_BASE_URL   endpoint root, e.g. https://host/v1  (POST {base}/chat/completions)
  LLM_API_KEY    bearer token
  LLM_MODEL      subject model id
  LLM_JUDGE_MODEL  optional judge model id; must differ from LLM_MODEL (decorrelation by id).
                   Without it, evals with no deterministic predicate are reported "ungraded".

Two case kinds per skill:
  refusal  evals/evals.json: the skill's SKILL.md is the system prompt, the eval prompt the user turn.
           Graded by the deterministic predicate bound in eval_predicates.BINDINGS where one exists,
           else by the judge against the chat-checkable expectations, else "ungraded".
  trigger  evals/triggers.json: the model sees every skill's name+description and must name the skill
           (or NONE) for the prompt; graded against should_trigger. Always programmatic.

--budget-tokens N is required. Before each call the worst case (prompt estimate + max_tokens) is added
to tokens already used; if that would exceed N the run stops (fail closed, report still written,
exit 3). Usage reported by the server replaces the estimate once a call returns.
--per-skill N caps refusal evals per skill (hard-bound evals always run first, then file order).
--max-tokens N per-call output cap (default 6000). A call ending finish_reason=="length" is "invalid"
(truncated), counted separately and excluded from pass rates; it is never a fail.
Exit: 0 ok, 1 any graded case failed, 2 usage/config error, 3 budget exhausted.
Stdlib only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import eval_predicates as ep  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_evals", SCRIPT_DIR / "run-evals.py")
_re = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_re)  # reuse decorrelation_error + chat_expectations

MAX_OUT = 6000  # reasoning models spend most of this thinking; <5000 truncates answers


class BudgetExceeded(Exception):
    pass


class Client:
    """Minimal chat client with a hard token budget. The key lives only in the request header."""

    def __init__(self, base: str, key: str, budget: int, timeout: int = 180):
        self.url, self.key, self.budget, self.used, self.timeout = base.rstrip("/") + "/chat/completions", key, budget, 0, timeout

    def chat(self, model: str, system: str, user: str, max_tokens: int = MAX_OUT) -> "tuple[str, str]":
        worst = (len(system) + len(user)) // 3 + max_tokens  # ponytail: chars/3 over-estimates tokens; fine as a guard
        body = json.dumps({"model": model, "max_tokens": max_tokens, "temperature": 0,
                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.url, body, {"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        for attempt in (1, 2):  # one retry: a single network blip must not discard a long run
            if self.used + worst > self.budget:  # re-checked per attempt: a failed attempt is charged
                raise BudgetExceeded(f"used={self.used} + worst-case {worst} > budget {self.budget}")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.load(r)
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                self.used += worst  # unknown spend: charge the worst case per failed attempt
                if attempt == 2:
                    raise RuntimeError(f"request failed: {type(e).__name__}") from None  # never echo headers/URL details
        used = (data.get("usage") or {}).get("total_tokens")
        self.used += used if isinstance(used, int) else worst
        print(f"live_evals: call ok, tokens {self.used}/{self.budget}", file=sys.stderr)  # progress; long runs are otherwise silent
        ch = data["choices"][0]
        return ch["message"].get("content") or "", ch.get("finish_reason") or "unknown"


def _frontmatter(skill_md: str) -> "tuple[str, str]":
    m = re.match(r"---\n(.*?)\n---", skill_md, re.S)
    fm = m.group(1) if m else ""
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    desc = re.search(r"^description:\s*>-?\n((?:[ ]+.*\n?)+)", fm, re.M)
    return (name.group(1) if name else ""), " ".join(desc.group(1).split()) if desc else ""


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def grade_trigger(answer: str, skill: str, should: bool) -> bool:
    got = re.sub(r"[^a-z0-9-]", " ", _strip_think(answer).lower()).split()
    hit = skill in got
    return hit == should


JUDGE_SYS = "You grade an assistant answer against expectations. Reply with exactly one word: PASS if every expectation is met, else FAIL."


def run(repo: Path, client: Client, subject: str, judge: "str | None", per_skill: int, only: "set[str] | None", max_tokens: int = MAX_OUT) -> dict:
    skills_dir = repo / ".claude" / "skills"
    skills = sorted(p.parent.parent.name for p in skills_dir.glob("*/evals/evals.json") if not only or p.parent.parent.name in only)
    texts = {s: (skills_dir / s / "SKILL.md").read_text(encoding="utf-8") for s in skills}
    catalog = "\n".join(f"- {n}: {d}" for n, d in (_frontmatter(t) for t in texts.values()))
    route_sys = ("You route a user task to the one skill that should handle it.\nSkills:\n" + catalog +
                 "\nReply with only the skill name, or NONE if no skill applies.")
    hard = {(b["skill"], b["eval_id"]): ep.PREDICATES[b["predicate"]] for b in ep.BINDINGS}
    cases, stopped = [], None
    try:
        for s in skills:
            evals = json.loads((skills_dir / s / "evals" / "evals.json").read_text(encoding="utf-8"))["evals"]
            evals = sorted(evals, key=lambda e: (s, e["id"]) not in hard)[:per_skill] if per_skill else evals  # stable: hard first
            for e in evals:
                raw, fin = client.chat(subject, texts[s], e["prompt"], max_tokens)
                ans = _strip_think(raw)
                case = {"kind": "refusal", "skill": s, "id": e["id"], "finish_reason": fin}
                if fin == "length":
                    case |= {"grader": "none", "result": "invalid"}  # truncated: not a fail, rerun with higher max_tokens
                elif (s, e["id"]) in hard:
                    ok, why = hard[(s, e["id"])](ans)
                    case |= {"grader": "predicate", "result": "pass" if ok else "fail", "why": why}
                elif judge and (exp := _re.chat_expectations(e.get("expectations", []))):
                    prompt = f"Task:\n{e['prompt']}\n\nAnswer:\n{ans[:6000]}\n\nExpectations:\n" + "\n".join(f"- {x}" for x in exp)
                    v = _strip_think(client.chat(judge, JUDGE_SYS, prompt, max_tokens)[0]).upper()
                    case |= {"grader": "judge", "result": "pass" if re.match(r"\W*PASS\b", v) else "fail"}
                else:
                    case |= {"grader": "none", "result": "ungraded"}
                cases.append(case)
            for t in json.loads((skills_dir / s / "evals" / "triggers.json").read_text(encoding="utf-8"))["triggers"]:
                ans, fin = client.chat(subject, route_sys, t["prompt"], max_tokens)
                ok = grade_trigger(ans, s, bool(t["should_trigger"]))
                res = "invalid" if fin == "length" else "pass" if ok else "fail"
                cases.append({"kind": "trigger", "skill": s, "id": t["id"], "finish_reason": fin, "grader": "programmatic", "result": res})
    except BudgetExceeded as e:
        stopped = str(e)
    graded = [c for c in cases if c["result"] not in ("ungraded", "invalid")]
    truncated = sum(c["result"] == "invalid" for c in cases)
    passed = sum(c["result"] == "pass" for c in graded)
    return {"subject_model": subject, "judge_model": judge, "tokens_used": client.used, "token_budget": client.budget,
            "stopped_budget": stopped, "max_tokens": max_tokens, "truncated": truncated, "total": len(cases), "graded": len(graded), "passed": passed,
            "pass_rate": round(passed / len(graded), 4) if graded else None,
            "by_kind": {k: {"graded": sum(c["kind"] == k and c["result"] in ("pass", "fail") for c in cases),
                            "passed": sum(c["kind"] == k and c["result"] == "pass" for c in cases)} for k in ("refusal", "trigger")},
            "cases": cases}


def main(argv: "list[str]") -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--budget-tokens", type=int, required=True)
    ap.add_argument("--per-skill", type=int, default=3, help="refusal evals per skill (0 = all)")
    ap.add_argument("--max-tokens", type=int, default=MAX_OUT, help="per-call output cap (default %(default)s)")
    ap.add_argument("--skill", action="append", help="limit to a skill (repeatable)")
    ap.add_argument("--out", help="write JSON report here (default stdout)")
    ap.add_argument("--repo", default=str(SCRIPT_DIR.parent))
    a = ap.parse_args(argv)
    env = {k: os.environ.get(k, "").strip() for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "LLM_JUDGE_MODEL")}
    missing = [k for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL") if not env[k]]
    if missing or a.budget_tokens <= 0:
        print(f"live_evals: need env {missing or ''} and a positive --budget-tokens", file=sys.stderr)
        return 2
    judge = env["LLM_JUDGE_MODEL"] or None
    if judge and (err := _re.decorrelation_error(env["LLM_MODEL"], judge)):
        print(f"live_evals: {err}", file=sys.stderr)
        return 2
    rep = run(Path(a.repo), Client(env["LLM_BASE_URL"], env["LLM_API_KEY"], a.budget_tokens), env["LLM_MODEL"], judge,
              a.per_skill, set(a.skill) if a.skill else None, a.max_tokens)
    out = json.dumps(rep, indent=1)
    Path(a.out).write_text(out + "\n", encoding="utf-8") if a.out else print(out)
    print(f"live_evals: {rep['passed']}/{rep['graded']} graded passed, {rep['total'] - rep['graded'] - rep['truncated']} ungraded, "
          f"{rep['truncated']} truncated (invalid run), "
          f"tokens {rep['tokens_used']}/{rep['token_budget']}", file=sys.stderr)
    if rep["stopped_budget"]:
        return 3
    return 0 if rep["passed"] == rep["graded"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
