# Merge-train bench re-run on the 1.584.0 scripts

Scripts under test: the Perun repository at commit b9e423199ec5f8a66b36d10e1074abb073fbcb35 (origin/main when 1.584.0 shipped), copied unmodified into a fresh run dir. The same commit's `scripts/test-train-flake-rate.sh` produced `flake-rate.txt`. Driver: `run.py` (offline: a bare origin plus a `gh` stub, so git is real and forge responses are simulated). Zero model spend, no network. Absolute paths in the logs are replaced by `$REPO`, `$HOME` and `$TMP`.

## Train bench (`run.py A normal|rev <flake offset> <id>`, logs in `A0 A1 A2 R0`)

6 PRs: G1, G2 (independent greens), C1, C2 (conflict on one file), S (passes alone, breaks the gate after G1 lands), F (1-in-3 simulated flaky test). R0 numbers S as #1 and G1 as #5.

| run | flake offset | landed | main green at all 5 commits | train test runs | CACHED hits in log |
|-----|--------------|--------|-----------------------------|-----------------|--------------------|
| A0 | 0 | G1 G2 C1 F | yes | 10 | 0 |
| A1 | 1 | G1 G2 C1 F | yes | 10 | 0 |
| A2 | 2 | G1 G2 C1 F | yes | 11 | 0 |
| R0 | 0, S and G1 numbers swapped | S G2 C1 F | yes | 10 | 0 |

- 4 of 6 landed in each run. C2 is parked at union build on the conflict, with no test run spent on it. The semantic conflict is caught in all 4 runs before the first merge (`PARK #5 breaks gate after #1,#2,#3`, see `out.txt`). Blame goes to the later PR number, so in R0 G1 (numbered 5) is parked and S lands.
- "Main green" is the oracle check of every first-parent commit of the origin `main` from base to tip, with the flake disabled; the train's `merge` step runs no tests.
- The verdict cache logged 0 hits in every run, so it saved 0 test runs on this fixture. Run counts 10, 10, 11, 10 are the actual counts in `runs.txt` (the driver writes it as `runs.log`; renamed because `*.log` is gitignored).
- Not re-run here: `train_land.sh` (B runs), the Monte Carlo classifier runs, and any pre-fix baseline.

## Flake and regression simulations (`flake-rate.txt`, `bash scripts/test-train-flake-rate.sh`: 16 passed, 0 failed)

- Seeded, 1000 trials on the real `train_flake.sh`, flake p = 1/3 per run: 31 blamed (3.1%); the retired 2-of-3 rule on the same draws would blame 248 (24.8%). Analytic: 1/27 = 3.7% against 7/27 = 25.9%.
- Regression that never fails on the base, 300 trials per rate, landed as a flake: at p = 2/3, 0 against 73 under the old rule (p = 0.5: 0 against 161; p = 0.9: 0 against 6). The old rule is counted on the drawn sequences, not by running the old script.
- A genuinely flaky test that is also flaky on the base (p = 1/3 both) still lands 210 of 300.
