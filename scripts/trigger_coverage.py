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

Usage: trigger_coverage.py [ROOT] [--ref GITREF]   (--ref reads SKILL.md files as of GITREF,
       to measure a baseline; triggers.json always comes from the working tree)
Exit 0 when every metric is full, 1 otherwise, 2 no skills dir.
Side effects: none (read-only; --ref runs `git show`).
"""
import glob
import json
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


def measure(root, ref=None):
    skills = sorted(os.path.basename(os.path.dirname(os.path.dirname(p)))
                    for p in glob.glob(os.path.join(root, ".claude/skills/*/evals/triggers.json")))
    allskills = [os.path.basename(d.rstrip("/")) for d in glob.glob(os.path.join(root, ".claude/skills/*/"))]
    ceo = " ".join(read(root, ".claude/skills/agentic-ceo/SKILL.md", ref).lower().split())
    cap = mom = momt = cr = crt = pairs = rt = rtt = 0
    miss = []
    for s in skills:
        desc = description(read(root, f".claude/skills/{s}/SKILL.md", ref)).lower()
        cap += len(desc) <= CAP
        cases = json.load(open(os.path.join(root, f".claude/skills/{s}/evals/triggers.json")))["triggers"]
        pos = [c for c in cases if c["should_trigger"]]
        neg = [c for c in cases if not c["should_trigger"]]
        pairs += bool(pos and neg)
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
    return dict(skills=len(skills), desc_cap=cap, moments=(mom, momt), ceo_route=(cr, crt),
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
          f"routes    {r['routes'][0]}/{r['routes'][1]}")
    for m in r["missed"]:
        print("MISS", m)
    full = (r["desc_cap"] == n and r["moments"][0] == r["moments"][1] and r["ceo_route"][0] == r["ceo_route"][1]
            and r["pairs"] == n and r["routes"][0] == r["routes"][1] and n > 0)
    return 0 if full else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
