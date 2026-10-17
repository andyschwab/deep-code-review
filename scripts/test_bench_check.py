#!/usr/bin/env python3
"""Offline tests for scripts/bench_check.py: one fixture bench, then one defect at a time."""
import hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bench_check as bc

W = lambda n, k: " ".join(f"{k}{i}" for i in range(n))  # n distinct words


def bench(root, name, tune_text, held_text):
    d = root / name
    (d / "outputs").mkdir(parents=True)
    (d / "SHA256-frozen.txt").write_text(f"{'0' * 64}  PREREGISTERED.md\n")
    (d / "PREREGISTERED.md").write_text("Hashed in SHA256-frozen.txt before any call.\n")
    h = hashlib.sha256((d / "SHA256-frozen.txt").read_bytes()).hexdigest()
    ev = [{"event": "preregistered", "sha256": h[:16], "ts": 1}, {"model": "m", "ts": 2}]
    (d / "ledger.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\n")
    (d / "scenarios_tune.json").write_text(json.dumps([{"id": "t1", "prompt": tune_text}]))
    (d / "scenarios_held.json").write_text(json.dumps([{"id": "h1", "prompt": held_text}]))
    return d


def errs(root, d, **kw):
    return bc.check(d, [x for x in root.iterdir() if x.is_dir() and x != d], **kw)


root = Path(tempfile.mkdtemp())
try:
    old = bench(root, "old", W(30, "a"), W(30, "b"))
    (old / "outputs" / "t1.txt").write_text("x")
    new = bench(root, "new", W(30, "c"), W(30, "d"))
    assert errs(root, new) == [], errs(root, new)

    # a. tune/held id collision
    (new / "scenarios_held.json").write_text(json.dumps([{"id": "t1", "prompt": W(30, "d")}]))
    assert any("both tune and held" in e for e in errs(root, new))
    (new / "scenarios_held.json").write_text(json.dumps([{"id": "h1", "prompt": W(30, "d")}]))
    # a. byte-identical output reuse, and its allowlist
    (new / "outputs" / "t1.txt").write_text("x")
    assert any("byte-identical" in e for e in errs(root, new))
    (new / "reuse-allow.txt").write_text("outputs/t1\n")
    assert errs(root, new) == []
    (new / "outputs" / "t1.txt").write_text("y")  # same name, new content is fine
    (new / "reuse-allow.txt").unlink()
    assert errs(root, new) == []

    # b. ledger: missing, hash rewritten after prereg, hash after generation, prefix too short
    led = (new / "ledger.jsonl").read_text()
    (new / "ledger.jsonl").unlink()
    assert any("both required" in e for e in errs(root, new))
    (new / "ledger.jsonl").write_text(led)
    (new / "SHA256-frozen.txt").write_text("rewritten after the ledger hash\n")
    assert any("no preregistered event" in e for e in errs(root, new))
    (new / "SHA256-frozen.txt").write_text(f"{'0' * 64}  PREREGISTERED.md\n")
    lines = led.splitlines()
    (new / "ledger.jsonl").write_text("\n".join(lines[::-1]) + "\n")
    assert any("not earlier" in e for e in errs(root, new))
    h = json.loads(lines[0])["sha256"]
    (new / "ledger.jsonl").write_text(json.dumps({"event": "preregistered", "sha256": h[:6]}) + "\n" + lines[1] + "\n")
    assert any("no preregistered event" in e for e in errs(root, new))
    (new / "ledger.jsonl").write_text(led)
    assert errs(root, new) == []

    # c. prereg doc naming a missing hash file
    (new / "PREREGISTERED.md").write_text("See SHA256-frozen.txt and SHA256-amend.txt.\n")
    assert any("SHA256-amend.txt" in e for e in errs(root, new))
    (new / "PREREGISTERED.md").write_text("See SHA256-frozen.txt.\n")

    # d. 10-word shingle overlap, and the template allowlist
    shared = W(12, "tpl")
    (new / "scenarios_tune.json").write_text(json.dumps([{"id": "t1", "prompt": shared + " " + W(8, "n")}]))
    (old / "scenarios_tune.json").write_text(json.dumps([{"id": "t1", "prompt": shared + " " + W(8, "o")}]))
    assert any("shingles" in e for e in errs(root, new))
    (new / "overlap-allow.txt").write_text(shared + "\n")
    assert errs(root, new) == [], errs(root, new)
    # 9 shared words never form a 10-word shingle, so a short template is not flagged
    (old / "scenarios_tune.json").write_text(json.dumps([{"id": "t1", "prompt": W(9, "tpl") + " " + W(20, "o")}]))
    (new / "overlap-allow.txt").unlink()
    (new / "scenarios_tune.json").write_text(json.dumps([{"id": "t1", "prompt": W(9, "tpl") + " " + W(20, "n")}]))
    assert errs(root, new) == []

    # --changed: only dirs absent from the base ref are checked; CLI exit codes
    r = Path(tempfile.mkdtemp())
    try:
        g = lambda *a: subprocess.run(["git", "-C", str(r), "-c", "user.name=t", "-c", "user.email=t@example.com", *a],
                                      check=True, capture_output=True)
        g("init", "-q", "-b", "main")
        shutil.copytree(old, r / "docs/bench/old")
        (r / "docs/bench/old/ledger.jsonl").unlink()  # legacy bench: no ledger
        g("add", "-A"); g("commit", "-qm", "base")
        shutil.copytree(new, r / "docs/bench/new")
        g("add", "-A"); g("commit", "-qm", "pr")
        run = lambda *a: subprocess.run([sys.executable, str(Path(bc.__file__)), *a], cwd=r, capture_output=True, text=True)
        p = run("--changed", "HEAD~1")
        assert p.returncode == 0 and "1 dir(s) clean" in p.stdout, p.stdout
        assert run("docs/bench/old").returncode == 1  # explicit dir is checked even if legacy
        (r / "docs/bench/new/ledger.jsonl").unlink()
        assert run("--changed", "HEAD~1").returncode == 1
    finally:
        shutil.rmtree(r)
finally:
    shutil.rmtree(root)
print("test_bench_check: ok")
