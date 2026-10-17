# Pre-registration v3: V1 held-out keep rule (supersedes the keep rule in PREREGISTERED.md v2)

Frozen before any held-out call. Goal: per-review token cost of the deep-code-review small-diff review at or below the rival's (pr-review-toolkit code-reviewer, arm TK) without losing F1.

## Frozen artifact
Variant V1 = output of `mk_v1.py` applied to the skill at origin/main 67166bf1 (skill content unchanged since the v2 tune base, version stamp aside). sha256 of the three files:
- SKILL.md (stub) ee93d6e633d9e53c88293d8b700db0522da9c54cd7b140ee9999ea2b67d0e34e
- references/compact-mode.md 1ef8db39f58248c115e66a3b2b4fb6ef7ee8c067475d93538ad080d3ac027add
- references/full-map.md b68e53f441488f974d97611b681e71c0f54787a525b4d50c07b97d19d01be560

## Runs
BASE (unedited skill copy via SKILL_DIR), TK and V1, once each on the 22 held-out cases in split.json, PCSS Qwen3.5-397B-A17B, driver.py and judges as in v2. No paid claude -p call. No re-run and no re-tuning after seeing held-out data. A case that errors after retry is dropped from all arms and reported.

## Keep rule (all must hold, n = held-out cases kept)
1. Quality: the lower bound of the 95% paired-bootstrap CI (10000 resamples, seed 1) of F1(V1) minus F1(BASE) is >= -0.02. This is the strict reading of "F1 >= BASE - 0.02, CI included"; the point estimate is reported as well but does not decide.
2. Cost: mean tokens per review of V1 <= mean tokens per review of TK on the same cases (tokens = sum over turns of prompt + completion tokens from the API usage field).

If either fails, the skill edit is reverted and only the bench ships. If both hold, the edit ships with size/mustload budget fixes, routing, a changelog.d fragment and an eval.

## Stated in advance
- Tune data (n=19) gave V1 20956 tokens against TK 5201, so rule 2 is expected to be hard to meet; it is kept because it is the owner's stated goal.
- n=22 gives a CI about 0.13 wide on F1, so rule 1 can fail by noise.
- Qwen host, not Claude; results may not transfer.
