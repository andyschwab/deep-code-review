#!/usr/bin/env python3
"""Held-out keep-rule read (PREREGISTERED-V1-heldout.md): F1(V1)-F1(BASE) paired CI and mean tokens of V1, BASE, TK on the cases all three completed.
usage: compare.py V1 heldout"""
import json, sys
import driver as d

arm, half = sys.argv[1:3]
rows = [(d.loadt(arm, c), d.loadt("BASE", c), d.loadt("TK", c), c) for c in d.SPLIT[half]]
H = [r for r in rows if r[0] and r[1] and r[2]]
A, B, T = ([r[i] for r in H] for i in range(3))
mean = lambda X: round(sum(r["tokens"] for r in X) / max(1, len(X)), 1)  # noqa: E731
f1 = lambda X: round(d.stats(X)[2], 3)  # noqa: E731
n = ("precision", "recall", "f1")
out = dict(arm=arm, half=half, n=len(H), dropped=[r[3] for r in rows if r not in H],
           f1=dict(ARM=f1(A), BASE=f1(B), TK=f1(T)), tokens=dict(ARM=mean(A), BASE=mean(B), TK=mean(T)),
           ARM_minus_BASE=dict(zip(n, d.boot(A, B))), ARM_minus_TK=dict(zip(n, d.boot(A, T))))
k = out["ARM_minus_BASE"]["f1"]["ci"][0] >= -0.02
t = out["tokens"]["ARM"] <= out["tokens"]["TK"]
out["keep"] = dict(quality_ci_lower_ge_minus_0_02=k, tokens_le_TK=t, decision="keep" if k and t else "revert")
(d.D / f"results-{arm}-{half}-vs-BASE.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
