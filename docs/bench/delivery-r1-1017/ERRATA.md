# Errata (2026-10-17): held-out ids collided with the tune split

`bench.py` here defines `TUNE_IDS = ["01b", "02a", "03b", "05b", "06b", "09b", "11a", "11b", "12a", "12b"]` (tune tickets taken from `../delivery-1017/tickets.json`). The held-out tickets in `tickets.json` use ids `01a` to `20b`, so ten ids exist in both splits: `01b 02a 03b 05b 06b 09b 11a 11b 12a 12b`. Both `gen` and `judge` skip files that already exist, so for those ten ids the held-out run reused the tune-ticket plans and judge records (sp, v0 and e1) instead of generating on the held-out ticket text. The held-out set is therefore 30 clean tickets, not 40, and the 10 collided ones were not independent of the tune pass that chose e1.

Recomputed on the 30 clean tickets (same per-ticket majority scores, same bootstrap, seed 1), win rate vs Superpowers:

| Arm | Win rate [95% CI] |
|---|---|
| v0 (origin/main) | 0.633 [0.533, 0.733] |
| e1 | 0.633 [0.533, 0.733] |
| ship | 0.583 [0.483, 0.683] |

Paired difference vs v0 on the clean 30: ship minus v0 = -0.050 [-0.183, 0.083] (6 up, 8 down); e1 minus v0 = 0.000 [-0.133, 0.150] (7 up, 8 down). The ship lower bound against Superpowers (0.483) is below 0.5, so the keep rule, as written in `PREREGISTERED.md` (Amendment A2), fails on the clean tickets. The 40-ticket figures in `README.md` and `PREREGISTERED.md` (ship 0.688 [0.588, 0.775]) are contaminated and must not be cited.

Follow-up: `../delivery-r2-1017` repeats the test on 40 new tickets (ids `h2-01` to `h2-40`, new output directories) under a preregistered rule.

Files affected: `results/ship__sp__held.json`, `results/v0__sp__held.json` and `results/e1__sp__held.json` are computed over all 40 held ids, including the 10 collided ones, so they carry the contaminated figures (for example ship 0.6875). They are kept unchanged as the record of what was run; cite the clean-30 numbers above instead.
