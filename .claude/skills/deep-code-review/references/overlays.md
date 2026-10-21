Read this when recommending or installing an overlay, or wiring this skill's gates into a target's CI.

## Optional overlays (same repository, not default)

This skill is the bar. Sibling skills install only on an explicit flag or an owner yes:

| Skill | Install | Does |
|---|---|---|
| `agentic-delivery` | `--with-delivery` or `--full` | Gated G0–G10 delivery; independent QA/security; one writer per worktree; names this review skill at G1/G6/G7 |
| `idea-critic` | `--with-critic` or `--full` | Pre-owner attack on plans and "we should" (3 hats; HOLD / REVISE / PASS_TO_USER) |

Recommend, don't dump: `./install.sh --recommend <project>` inspects the
target and prints a pack. Default `./install.sh <project>` stays review-only.

`--with-gates` is a **mechanism, not a skill**: it wires this skill's own
gate scripts (`fix_class_gate.py`, `binaries_gate.py`) into the target's own
CI via `scripts/dcr-gates.sh` — **read `docs-and-dx.md`'s
Standards-imprint section when pairing a Phase 6 standard with a mechanized
gate**, not just a doc. A count in a doc: `derived_numbers.py` (same file, "store the query").

Terse chat voice is **not** vendored. For compressed assistant prose add
[JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) separately.
Persisted artifacts (code, PR bodies, docs) stay normal English.

Compose with other packs; never run a second delivery OS on one repo.
This skill always composes.
