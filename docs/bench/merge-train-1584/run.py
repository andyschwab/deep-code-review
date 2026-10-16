#!/usr/bin/env python3
"""Offline merge-train bench driver. Usage: run.py <A|B|T|MC> <normal|rev> <offset> <id>. Writes work/<id>/."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).parent.resolve()
SC = HERE / "src/.claude/skills/agentic-delivery/scripts"
FXS = HERE / "fixture"
BASE = {
    "app/__init__.py": "", "tests/__init__.py": "",
    "app/util.py": 'def fmt(x):\n    return "<%s>" % x\n',
    "app/calc.py": "from app.util import fmt\n\n\ndef add(a, b):\n    return a + b\n\n\ndef label(a, b):\n    return fmt(add(a, b))\n",
    "tests/test_calc.py": 'import unittest\nfrom app.calc import add, label\n\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n\n    def test_label(self):\n        self.assertEqual(label(1, 2), "<3>")\n',
}
FLAKY = '''import os, random, unittes


class T(unittest.TestCase):
    def test_flaky(self):
        mode = os.environ.get("FLAKE_MODE", "counter")
        if mode == "never":
            return
        p = os.environ["FLAKE_COUNTER"]
        n = 1
        if os.path.exists(p):
            with open(p) as fh:
                n = int(fh.read()) + 1
        with open(p, "w") as fh:
            fh.write(str(n))
        if mode == "random":
            self.assertGreaterEqual(random.Random("%s:%d" % (os.environ["FLAKE_SEED"], n)).random(), 1 / 3, "simulated flake")
        else:
            self.assertNotEqual((n + int(os.environ.get("FLAKE_OFFSET", "0"))) % 3, 0, "simulated 1-in-3 failure")
'''


def role_files(role):
    calc = BASE["app/calc.py"]
    return {
        "G1": {"app/util.py": 'def fmt(x, width):\n    return "<%s>" % str(x).rjust(width)\n',
               "app/calc.py": calc.replace("fmt(add(a, b))", "fmt(add(a, b), 1)")},
        "G2": {"app/g2.py": "def double(x):\n    return 2 * x\n",
               "tests/test_g2.py": "import unittest\nfrom app.g2 import double\n\n\nclass T(unittest.TestCase):\n    def test_double(self):\n        self.assertEqual(double(2), 4)\n"},
        "C1": {"app/calc.py": calc.replace("return a + b", "return int(a) + int(b)"),
               "tests/test_c1.py": 'import unittest\nfrom app.calc import add\n\n\nclass T(unittest.TestCase):\n    def test_c1(self):\n        self.assertEqual(add("1", "2"), 3)\n'},
        "C2": {"app/calc.py": calc.replace("return a + b", "return sum((a, b))"),
               "tests/test_c2.py": 'import unittest\nfrom app.calc import add\n\n\nclass T(unittest.TestCase):\n    def test_c2(self):\n        self.assertEqual(add(2, 2), 4)\n'},
        "S": {"app/report.py": "from app.util import fmt\n\n\ndef report(x):\n    return fmt(x)\n",
              "tests/test_report.py": 'import unittest\nfrom app.report import report\n\n\nclass T(unittest.TestCase):\n    def test_report(self):\n        self.assertEqual(report(5), "<5>")\n'},
        "F": {"app/f.py": "VALUE = 1\n", "tests/test_flaky.py": FLAKY},
    }[role]


def run(cmd, cwd=None, env=None, out=None):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if out:
        open(out, "a").write(f"$ {' '.join(map(str, cmd))}\n{p.stdout}{p.stderr}[rc={p.returncode}]\n")
    return p


def build(W, order, offset):
    W.mkdir(parents=True)
    (W / "bin").mkdir()
    (W / "bin/gh").symlink_to(FXS / "gh")
    origin, clone = W / "origin.git", W / "clone"
    G = lambda *a, cwd=clone: subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "init", "-q", "--template=", "--bare", "-b", "main", str(origin)], check=True)
    clone.mkdir()  # sandbox denies writing <dir>/.git/config, so the git dir lives beside the work tree
    subprocess.run(["git", "init", "-q", "-b", "main", "--template=", f"--separate-git-dir={W/'clone.git'}", str(clone)], check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=clone, check=True)
    def write(files):
        for p, c in files.items():
            (clone / p).parent.mkdir(parents=True, exist_ok=True); (clone / p).write_text(c)
    write(BASE); G("add", "-A"); G("commit", "-qm", "base"); G("push", "-q", "origin", "HEAD:main")
    base = G("rev-parse", "HEAD")
    roles = {"normal": ["G1", "G2", "C1", "C2", "S", "F"], "rev": ["S", "G2", "C1", "C2", "G1", "F"]}[order]
    prs, ci = {}, {}
    for i, role in enumerate(roles, 1):
        G("checkout", "-q", "-b", f"br{i}", base); write(role_files(role)); G("add", "-A"); G("commit", "-qm", f"{role}: change");
        sha = G("rev-parse", "HEAD"); G("push", "-q", "origin", f"br{i}:refs/pull/{i}/head"); prs[str(i)] = {"role": role, "state": "OPEN"}
        G("checkout", "-q", "--detach", base)
    G("checkout", "-q", "main"); G("fetch", "-q", "origin")
    env = {**os.environ, "RUNLOG": str(W / "ci.log"), "FLAKE_COUNTER": str(W / "ci.counter"), "FLAKE_OFFSET": str(offset), "PYTHONDONTWRITEBYTECODE": "1"}
    for i in prs:  # pre-train per-PR CI: head alone, up to 3 attempts
        sha = G("rev-parse", f"br{i}"); wt = W / f"ci{i}"
        G("worktree", "add", "-q", "--detach", str(wt), sha)
        n = 0
        for n in (1, 2, 3):
            if subprocess.run([str(FXS / "testrun.sh"), "ci"], cwd=wt, env=env).returncode == 0:
                break
        else:
            n = 4
        G("worktree", "remove", "--force", str(wt))
        ci[sha] = [{"name": "ci", "status": "completed", "conclusion": "success" if n < 4 else "failure", "started_at": "2026-01-01T00:00:00Z", "id": 1}]
        prs[i]["ci_attempts"] = n
    json.dump({"prs": prs, "base": base}, open(W / "state.json", "w")); json.dump(ci, open(W / "ci.json", "w"))
    return base, prs


def trainenv(W, offset, extra=None):
    e = {**os.environ, "FX": str(W), "RUNLOG": str(W / "runs.log"), "FLAKE_COUNTER": str(W / "train.counter"), "FLAKE_OFFSET": str(offset),
         "PATH": f"{W/'bin'}:{os.environ['PATH']}", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "PYTHONDONTWRITEBYTECODE": "1",
         "SC": str(SC), "FXSRC": str(FXS), "GH": str(W / "bin/gh"), "PERUN_HEAVY_DIR": str(W / "heavy")}
    e.update(extra or {})
    return e


def timed(cmd, cwd, env, out):
    t = time.perf_counter(); p = run(cmd, cwd, env, out); return round(time.perf_counter() - t, 3), p


def oracle(W, base):
    origin = W / "origin.git"
    shas = [base] + subprocess.run(["git", "-C", str(origin), "rev-list", "--first-parent", "--reverse", f"{base}..main"], capture_output=True, text=True).stdout.split()
    res = []
    for s in shas:
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(f"git -C {origin} archive {s} | tar -x -C {d}", shell=True, check=True)
            rc = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"], cwd=d, capture_output=True,
                                env={**os.environ, "FLAKE_MODE": "never", "PYTHONDONTWRITEBYTECODE": "1"}).returncode
        res.append((s[:7], rc))
    return res


def metrics(W, base, prs, times):
    st = json.load(open(W / "state.json"))
    landed = sorted(f"{st['prs'][n]['role']}(#{n})" for n in st["prs"] if st["prs"][n]["state"] == "MERGED")
    runs = [l.split() for l in open(W / "runs.log")] if (W / "runs.log").exists() else []
    kinds = {}
    for k, _, rc in runs:
        kinds[k] = kinds.get(k, 0) + 1
    # extra wall under default --backoff 30: per verify worktree, sleep before attempt i>=1 is min(30*2^(i-1),300)
    groups = {}
    for k, cwd, rc in runs:
        if k == "verify":
            groups[cwd] = groups.get(cwd, 0) + 1
    extra = sum(min(30 * 2 ** (i - 1), 300) for n in groups.values() for i in range(1, n))
    o = oracle(W, base)
    return {"landed": landed, "main_commits_checked": len(o), "oracle_rc": o, "main_green_every_commit": all(rc == 0 for _, rc in o),
            "test_runs": kinds, "test_runs_total": len(runs), "default_backoff_extra_s": extra, "wall_s": times,
            "ci_attempts": {n: prs[n]["ci_attempts"] for n in prs}}


def main():
    mode, order, offset, rid = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    W = HERE / "work" / rid
    if W.exists() and W.parent == HERE / "work":
        shutil.rmtree(W)  # own bench dir only
    base, prs = build(W, order, offset)
    clone = W / "clone"; out = W / "out.txt"; times = {}
    if mode == "A":
        env = trainenv(W, offset)
        vc = f"{FXS/'testrun.sh'} verify"
        for name, cmd in [("plan", ["plan", "--base", "main"]),
                          ("verify", ["verify", "--base", "main", "--verify-cmd", vc, "--retries", "2", "--backoff", "0"]),
                          ("merge", ["merge", "--base", "main", "--apply", "--grant", "bench"])]:
            times[name], p = timed(["python3", "-I", str(SC / "merge_train.py"), *cmd], clone, env, out)
            if name == "verify" and p.returncode not in (0, 1):
                break
    elif mode == "B":
        env = trainenv(W, offset, {"VERIFY_CMD": f"bash {FXS/'adapter.sh'}", "UNION_DIRS": f"{W/'uw'} {clone}", "BROWSER_CMD": str(FXS / "browser.sh"),
                                   "RERUN_CMD": str(FXS / "rerun.sh"), "LOG_DIR": str(W), "BACKFILL_FILE": str(W / "backfill.txt"), "WAIT_SECS": "0"})
        times["train_land"], p = timed(["bash", str(SC / "train_land.sh"), "B", *prs.keys()], clone, env, out)
    elif mode == "T":
        env = trainenv(W, offset)
        G = lambda *a, cwd=clone: run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *a], cwd, env, out)
        G("fetch", "-q", "origin", "refs/pull/*/head:refs/pull/*/head")
        for a, b in [("3", "4"), ("1", "3"), ("1", "5")]:
            run(["python3", "-I", str(SC / "union_overlap.py"), "--repo", str(clone), "--base", "main", "--mine", a, "--other", b], clone, env, out)
        tw = W / "tw"; G("worktree", "add", "-q", "--detach", str(tw), "br5"); G("merge", "-q", "--no-edit", "br1", "br6", cwd=tw)
        (W / "ids.txt").write_text("tests.test_flaky.T.test_flaky\ntests.test_report.T.test_report\n")
        env.update(RERUN_CMD=str(FXS / "rerun.sh"), FLAKE_INVOCATION="bench")
        times["train_flake"], p = timed(["bash", str(SC / "train_flake.sh"), str(W / "ids.txt")], tw, env, out)
    elif mode == "MC":
        n = offset  # trials
        env = trainenv(W, 0, {"FLAKE_MODE": "random", "RERUN_CMD": str(FXS / "rerun.sh"), "FLAKE_INVOCATION": "bench"})
        G = lambda *a, cwd=clone: run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *a], cwd, env, out)
        tw = W / "tw"; G("worktree", "add", "-q", "--detach", str(tw), "br6")
        (W / "ids.txt").write_text("tests.test_flaky.T.test_flaky\n")
        a = {"REAL": 0, "FLAKE": 0}; b = {"FLAKY": 0, "DET_FAIL": 0, "GREEN": 0, "other": 0}
        for i in range(n):
            e = {**env, "FLAKE_SEED": str(i), "FLAKE_COUNTER": str(W / f"mca{i}.counter")}
            o = run(["bash", str(SC / "train_flake.sh"), str(W / "ids.txt")], tw, e).stdou
            a["REAL" if o.startswith("REAL") else "FLAKE"] += 1
        for i in range(n):
            e = {**env, "FLAKE_SEED": str(i), "FLAKE_COUNTER": str(W / f"mcb{i}.counter"), "ONLY": "2,6"}
            o = run(["python3", "-I", str(SC / "merge_train.py"), "verify", "--base", "main", "--state", str(W / f"mcb{i}.json"), "--verify-cmd",
                     f"{FXS/'testrun.sh'} verify", "--retries", "2", "--backoff", "0"], clone, e).stdou
            b["FLAKY" if "FLAKY" in o else "DET_FAIL" if "deterministic" in o else "GREEN" if "GREEN" in o else "other"] += 1
        m = {"id": rid, "trials": n, "train_flake_verdicts": a, "union_gate_outcomes": b, "analytic": {"REAL": 7 / 27, "DET_FAIL": 1 / 27, "FLAKY": 8 / 27}}
        json.dump(m, open(W / "result.json", "w"), indent=1); print(json.dumps(m)); return
    m = metrics(W, base, prs, times) if mode in "AB" else {}
    m["id"] = rid
    json.dump(m, open(W / "result.json", "w"), indent=1)
    print(json.dumps(m))


main()
