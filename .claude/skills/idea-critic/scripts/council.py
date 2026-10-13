#!/usr/bin/env python3
"""Council: independent multi-lens verdict for idea-critic, any model, stdlib only.

Each --cmd is a command template that reads the prompt on stdin and prints the
answer on stdout (e.g. `claude -p`, `codex exec -`, `ollama run X`); repeat it for
mixed models. Default: 3 lenses, answers independent (no lens sees another's). A
deterministic tally fixes the verdict; a critique round runs ONLY on disagreement,
with anonymized answers. Claims need path:line (checked against --root) or a URL
(recorded, never counted as verified). Caps are checked BEFORE each call; any
failure fails closed with verdict COULD_NOT_DECIDE (exit 3), never a guess.
Side effects: spawns the given commands, reads files under --root. Exit 0 decided.
"""
from __future__ import annotations

import argparse, json, random, re, shlex, subprocess, sys, time
from pathlib import Path

VERDICTS = ("HOLD", "REVISE", "PASS_TO_USER")  # most cautious first: ties go left
LENSES = ("skeptic", "better-way", "kill-criteria")
CITE = re.compile(r"^(?P<p>[^\s:][^:]*):(?P<a>\d+)(?:-(?P<b>\d+))?$")
CONTRACT = (
    'Reply with ONE JSON object: {"verdict": "HOLD|REVISE|PASS_TO_USER", '
    '"claims": [{"text": "...", "evidence": "path:line or URL"}], '
    '"would_change_it": "a checkable fact that would flip your verdict"}. '
    "Every claim needs evidence; claims without it are discarded."
)
CRITIQUE = (
    "STAGE: CRITIQUE\nOther reviewers answered independently and disagree. Attack "
    "any answer you think is wrong, with evidence (path:line or URL); unevidenced "
    'attacks are discarded. Reply with ONE JSON object: {"verdict": "HOLD|REVISE|'
    'PASS_TO_USER", "attacks": [{"target": "A", "text": "...", "evidence": "..."}]}. '
    "Change your verdict only if an evidenced attack justifies it."
)


class Stop(Exception):
    pass


def cite_ok(ev: str, root: Path) -> bool:
    m = CITE.match(ev.strip()) if isinstance(ev, str) else None
    if not m:
        return False
    try:
        f = (root / m["p"]).resolve()
        f.relative_to(root.resolve())
        n = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
    except (OSError, ValueError):
        return False
    a, b = int(m["a"]), int(m["b"] or m["a"])
    return 1 <= a <= b <= n


def parse(text: str) -> dict:
    d = json.loads(text[text.index("{") : text.rindex("}") + 1])
    if d.get("verdict") not in VERDICTS:
        raise ValueError("bad verdict")
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cmd", action="append", required=True)
    ap.add_argument("--claim", required=True)
    ap.add_argument("--steelman", required=True)
    ap.add_argument("--packet", help="file with evidence/context given to every lens")
    ap.add_argument("--origin", default="agent-originated", choices=("owner-request", "agent-originated"))
    ap.add_argument("--root", default=".")
    ap.add_argument("--max-calls", type=int, default=8)
    ap.add_argument("--max-chars", type=int, default=200000)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    lens_dir = Path(__file__).parent / "lenses"
    packet = Path(a.packet).read_text(encoding="utf-8") if a.packet else ""
    body = f"CLAIM:\n{a.claim}\n\nSTEELMAN:\n{a.steelman}\n\nPACKET:\n{packet}\n\n"
    # lens i runs on cmd i mod len(cmds): one cmd = solo-3, several = mixed
    plan = [(c, (lens_dir / f"{l}.txt").read_text(encoding="utf-8")) for c, l in
            zip((a.cmd[i % len(a.cmd)] for i in range(3)), LENSES)]
    st = {"calls": 0, "chars": 0}
    rec = {"verdict": "COULD_NOT_DECIDE", "independence": "independent", "origin": a.origin,
           "claim": a.claim, "steelman": a.steelman, "tally": {}, "confidence": 0.0,
           "dissent": [], "voided_objections": [], "unsupported_claims": [],
           "what_would_change_it": [], "cost": st, "seed": a.seed, "critique_ran": False}

    def call(cmd: str, prompt: str) -> str:
        if st["calls"] + 1 > a.max_calls or st["chars"] + len(prompt) > a.max_chars:
            raise Stop("cap reached before call")
        st["calls"] += 1
        st["chars"] += len(prompt)
        try:
            r = subprocess.run(shlex.split(cmd), input=prompt, capture_output=True,
                               text=True, timeout=a.timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise Stop(f"cmd failed: {type(e).__name__}")
        if r.returncode:
            raise Stop(f"cmd exit {r.returncode}")
        return r.stdout

    if a.dry_run:
        print(json.dumps({"planned_calls": 3, "max_extra_if_disagree": 3,
                          "prompt_chars": sum(len(body + l + CONTRACT) for _, l in plan)}))
        return 0
    t0 = time.time()
    try:
        answers = []
        for cmd, lens in plan:
            raw = call(cmd, f"{lens}\n\n{body}{CONTRACT}\n")
            try:
                d = parse(raw)
            except (ValueError, KeyError):
                raise Stop("unparseable answer")
            ok = [c for c in d.get("claims", []) if isinstance(c, dict) and cite_ok(c.get("evidence"), root)]
            bad = [c for c in d.get("claims", []) if c not in ok]
            rec["unsupported_claims"] += bad
            answers.append({"raw": raw.strip(), "verdict": d["verdict"], "share": len(ok) / max(1, len(ok) + len(bad)),
                            "would": d.get("would_change_it")})
        final = [x["verdict"] for x in answers]
        if len(set(final)) > 1:
            rec["critique_ran"] = True
            order = list(range(3))
            random.Random(a.seed).shuffle(order)
            label = {i: "ABC"[k] for k, i in enumerate(order)}
            for i, (cmd, _) in enumerate(plan):
                others = "\n\n".join(f"ANSWER {label[j]}:\n{answers[j]['raw']}" for j in sorted(order, key=label.get) if j != i)
                raw = call(cmd, f"{CRITIQUE}\n\n{body}{others}\n")
                try:
                    d = parse(raw)
                except (ValueError, KeyError):
                    raise Stop("unparseable critique")
                atk = [x for x in d.get("attacks", []) if isinstance(x, dict)]
                good = [x for x in atk if cite_ok(x.get("evidence"), root)]
                rec["voided_objections"] += [x for x in atk if x not in good]
                if good:
                    final[i] = d["verdict"]
        tally = {v: final.count(v) for v in VERDICTS}
        top = max(tally.values())
        verdict = next(v for v in VERDICTS if tally[v] == top)
        if a.origin == "owner-request" and verdict == "HOLD":
            verdict = "REVISE"  # schema: owner-request + HOLD is illegal
        rec.update(verdict=verdict, tally=tally,
                   confidence=round(top / 3 * sum(x["share"] for x in answers) / 3, 3),
                   dissent=[x["raw"] for x, f in zip(answers, final) if f != verdict],
                   what_would_change_it=[x["would"] for x in answers if x["would"]] or
                   ["UNVERIFIED: no reviewer stated a checkable condition"])
    except Stop as e:
        rec["reason"] = str(e)
        rec["what_would_change_it"] = [f"rerun after fixing: {e}"]
    rec["cost"] = {**st, "wall_s": round(time.time() - t0, 2)}
    print(json.dumps(rec, indent=2))
    return 0 if rec["verdict"] != "COULD_NOT_DECIDE" else 3


if __name__ == "__main__":
    sys.exit(main())
