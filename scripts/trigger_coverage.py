#!/usr/bin/env python3
"""Trigger coverage: do skill descriptions name the moments each skill should fire?

Reads `.claude/skills/<skill>/evals/triggers.json`:
  {"triggers": [{"id", "prompt", "should_trigger": bool,
                 "moments": [alt phrases, any one counts],   # positives only
                 "ceo_route": "phrase"?,                      # optional, positives
                 "route_to": "<skill>"?}]}                    # negatives only

Metrics (all deterministic, repo-measurable, no LLM):
  desc_cap   skills whose folded frontmatter description is <= 300 chars (host cap)
  moments    should_trigger cases with >=1 moment phrase inside the FIRST 300 chars
  ceo_route  cases with a `ceo_route` phrase present in agentic-ceo SKILL.md
  pairs      skills with >=1 should_trigger and >=1 should_not case
  routes     should_not cases whose `route_to` names a real skill directory
  rank       PROXY (not a real model's activation): prompts ranked against every skill's
             description by IDF-weighted word overlap. A should_trigger prompt must rank
             its own skill strictly first; a should_not prompt must not. Each skill needs
             >=3 positives and >=2 negatives.

Usage: trigger_coverage.py [ROOT] [--ref GITREF]   (--ref reads SKILL.md files as of GITREF,
       to measure a baseline; triggers.json always comes from the working tree)
Exit 0 when every metric is full, 1 otherwise, 2 no skills dir.
Side effects: none (read-only; --ref runs `git show`).
"""
import glob
import json
import math
import os
import re
import subprocess
import sys

CAP = 300


def read(root, rel, ref):
    if ref:
        r = subprocess.run(["git", "-C", root, "show", f"{ref}:{rel}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""
    p = os.path.join(root, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def description(text):
    fm = text.split("---")[1] if text.count("---") >= 2 else ""
    m = re.search(r"^description:\s*(.*?)(?=^\S)", fm + "\nx:", re.S | re.M)
    return " ".join((m.group(1) if m else "").replace(">-", "").split())


STOP = set("a an and any are as at be before by for from in into is it my of on or our the this to up us we with you your".split())


def words(text):
    """Content words, crude plural stem (trailing s dropped when len>3)."""
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w
            for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def rank_failures(descs, cases):
    """PROXY: (skill, id) pairs whose IDF-overlap rank contradicts should_trigger. Ties are not 'first'."""
    dw = {s: words(d) for s, d in descs.items()}
    idf = {w: math.log(len(dw) / sum(w in v for v in dw.values())) for v in dw.values() for w in v}
    bad = []
    for s, c in cases:
        p = words(c["prompt"])
        sc = {k: sum(idf[w] for w in p & v) for k, v in dw.items()}
        first = sc[s] > 0 and all(sc[s] > x for k, x in sc.items() if k != s)
        if first != c["should_trigger"]:
            bad.append(f"{s}:{c['id']}")
    return bad


def measure(root, ref=None):
    skills = sorted(os.path.basename(os.path.dirname(os.path.dirname(p)))
                    for p in glob.glob(os.path.join(root, ".claude/skills/*/evals/triggers.json")))
    allskills = [os.path.basename(d.rstrip("/")) for d in glob.glob(os.path.join(root, ".claude/skills/*/"))]
    ceo = " ".join(read(root, ".claude/skills/agentic-ceo/SKILL.md", ref).lower().split())
    cap = mom = momt = cr = crt = pairs = rt = rtt = 0
    miss = []
    descs = {s: description(read(root, f".claude/skills/{s}/SKILL.md", ref)) for s in allskills}
    rcases = []
    for s in skills:
        desc = description(read(root, f".claude/skills/{s}/SKILL.md", ref)).lower()
        cap += len(desc) <= CAP
        cases = json.load(open(os.path.join(root, f".claude/skills/{s}/evals/triggers.json")))["triggers"]
        pos = [c for c in cases if c["should_trigger"]]
        neg = [c for c in cases if not c["should_trigger"]]
        pairs += bool(pos and neg)
        rcases += [(s, c) for c in cases]
        if len(pos) < 3 or len(neg) < 2:
            miss.append(f"{s}:needs>=3 should_trigger and >=2 should_not ({len(pos)}/{len(neg)})")
        for c in pos:
            momt += 1
            ok = any(m.lower() in desc[:CAP] for m in c["moments"])
            mom += ok
            if not ok:
                miss.append(f"{s}:{c['id']}")
            if "ceo_route" in c:
                crt += 1
                cr += c["ceo_route"].lower() in ceo
        for c in neg:
            rtt += 1
            rt += c.get("route_to") in allskills
    rbad = rank_failures(descs, rcases)
    miss += [f"RANK {b}" for b in rbad]
    return dict(skills=len(skills), rank=(len(rcases) - len(rbad), len(rcases)), desc_cap=cap, moments=(mom, momt), ceo_route=(cr, crt),
                pairs=pairs, routes=(rt, rtt), missed=miss)


def main(argv):
    ref = argv[argv.index("--ref") + 1] if "--ref" in argv else None
    args = [a for a in argv[1:] if not a.startswith("--") and a != ref]
    root = args[0] if args else "."
    if not glob.glob(os.path.join(root, ".claude/skills")):
        print("no skills directory", file=sys.stderr)
        return 2
    r = measure(root, ref)
    n = r["skills"]
    print(f"desc_cap  {r['desc_cap']}/{n}\nmoments   {r['moments'][0]}/{r['moments'][1]}\n"
          f"ceo_route {r['ceo_route'][0]}/{r['ceo_route'][1]}\npairs     {r['pairs']}/{n}\n"
          f"routes    {r['routes'][0]}/{r['routes'][1]}\nrank(proxy) {r['rank'][0]}/{r['rank'][1]}")
    for m in r["missed"]:
        print("MISS", m)
    full = (r["desc_cap"] == n and r["moments"][0] == r["moments"][1] and r["ceo_route"][0] == r["ceo_route"][1]
            and r["pairs"] == n and r["routes"][0] == r["routes"][1] and not r["missed"] and r["rank"][0] == r["rank"][1] and n > 0)
    return 0 if full else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
