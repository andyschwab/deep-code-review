# Council: independent multi-lens verdict (`scripts/council.py`)

**Read this when** a verdict is high-blast or irreversible and one inline pass is
too weak: you want the three hats (see SKILL.md, Hats) run as independent calls,
optionally on different models, with a mechanical tally instead of one model's
judgment.

## Run

```text
python3 scripts/council.py --cmd "claude -p --strict-mcp-config" \
  --claim "<one sentence>" --steelman "<best version>" --packet evidence.txt --root .
```

- `--cmd` reads the prompt on stdin and prints the answer; repeat it for mixed
  models (lens *i* uses cmd *i* mod N). Default is solo-3: one cmd, three lenses
  in `scripts/lenses/*.txt` (plain text, no host tool names; edit them freely).
- Lens answers are independent: no lens sees another's. The critique round runs
  only when verdicts differ, with answers shuffled and relabelled A/B/C (seeded,
  recorded). A member changes its verdict only if its critique carries an
  evidenced attack.
- Claims need `path:line` (checked: file under `--root`, line in range) or a URL.
  URLs are recorded but never count as verified; failed citations land in
  `unsupported_claims` / `voided_objections`.
- Verdict = deterministic tally; ties go to the more cautious
  (`HOLD` > `REVISE` > `PASS_TO_USER`); `owner-request` + `HOLD` becomes `REVISE`.
  `confidence` = top-vote share x mean verified-claim share, never self-reported.
  Minority answers are kept verbatim in `dissent`.
- `--max-calls` (8), `--max-chars` (200000) and `--timeout` (120s per call) are
  checked before each call. Any cap hit, non-zero exit, timeout or unparseable
  answer yields `COULD_NOT_DECIDE` (exit 3), never a guessed verdict.
  `--dry-run` prints planned calls.
- Validate: `scripts/validate_verdict.py --file record.json` accepts the council
  record (it has `tally`) and `COULD_NOT_DECIDE` with a `reason`.

## Kill criterion

Debate-style councils often fail to beat plain self-consistency
(`docs/standards-index.md`, "Should we be going MAD?"). Keep the council only if,
at equal call budget, it beats self-consistency-3 (same cmd, three samples, vote)
on the bench by a margin that survives a bootstrap over TEST cases. Otherwise it
stays opt-in or is removed. Not yet measured; no accuracy claim is made here.
