# Phase 5 report and Phase 6 imprint — procedure

Read this when writing the Phase 5 report (delivery shape, out-of-tree vs in-repo, ledger and claim reconciliation, remediation split) or imprinting Phase 6 standards. Split from `method.md`; the Phase 0-4 procedure and the first-response block stay there, templates stay in `report-format.md`.

**Phase 5 — Report.** **Default delivery is two artifacts, and neither is a
commit into the reviewed repo:** (1) a **chat BLUF, ≤30 lines** — one-line
verdict, the top ≤5 **confirmed defects** in plain language, a one-line
`Decisions: N` pointer (not product ideas filling defect slots), and the path to
the full technical table; and (2) the **full report written out-of-tree**
(`~/Downloads/`, session scratch, or the PR comment). **The full report carries an
"Invariants verified to hold" section, co-equal with the findings table** — the
specific security/correctness properties each unit (and the lead's independent
read) opened the code and confirmed, each grounded at `file:line` with the same
snippet-or-drop rigor a defect gets. On a **hardened target this is the primary
deliverable**: a finding-count report has the least to say exactly when the owner
needs the most reassurance, and "here are the N properties we opened the code and
proved" is worth more than "we found nothing." An affirmative claim is as
falsifiable as a defect claim — drop any you cannot quote at `START_SHA`.
Product/redesign ideas go
under **Decisions needed (owner)** — they never carry Blocker/Critical gate
language. Severity still follows consequence: a product choice that creates a
Critical defect remains a defect. **Never paste the machine findings table as
the first chat bubble** — a 15-domain table buries the verdict it was supposed
to deliver. **The two-artifact report is owed on `FULL`;** on a `DIFF`/`FILE` you
are also fixing, a compact `found → root cause → fix → re-gate` trail may stand in
for the out-of-tree report (snippet-or-drop still applies).

**Fix the failing layer, not the first plausible one.** A "missing value / blank
field / missing tag" symptom on a rendered surface is not automatically a *render*
bug — the render path is often already correct and the gap is one layer down: the
field is empty **at the source**, or a **config / derivation / mapping** step never
ran. **Localize before patching** — prove which layer fails (*is the value present at
the source? does the derivation/mapping run? is it purely a render bug?*) and fix
**that** one; a presentation "fix" over a data gap is a no-op at best, and a
hard-coded view fallback is worse — it **masks** the gap and reads as resolved.
**Name the proven-failing layer in the finding** so a downstream implementer doesn't
re-patch the wrong one. And watch the **two-layer** case: a durable fix usually needs
both a **correct default going forward** *and* a **backfill of the existing records**
that already carry the gap — fix only the default and old data stays broken; fix only
the backfill and new data re-breaks. (The specific, high-frequency instance of
principle 9, *root-cause not symptom*.)

**Writing into the repo's `code-review/` directory is opt-in.** It requires the
user's explicit confirmation (or an explicit `--write-report`), *and* an unshared,
idle checkout; on an incident day or with a hotfix in flight, stay out-of-tree and
offer to commit on a **dedicated review branch** afterward. Never write into a
checkout another agent is committing from. When the report **is** committed, see
"Human-readable report" in `report-format.md` for the template and the post-write privacy re-scan.

**On a public remote, a fork, or any repo whose history strangers can read, a
committed report is disclosure.** Commit only **finding ID + severity + area** —
the reproduction, the payload, the exact route/parameter, and the sample of
exposed data stay in the session output or a **private security advisory/PR**
until the fix ships. A committed review that hands a reader a working exploit for
an unpatched hole is a net-negative deliverable (principle 4).

**Reconcile against Phase 0's coverage ledger before you close.** Every domain the
ledger called applicable is ruled on (finding, clean, or `unverified` + artifact),
every must-load reference was actually loaded, and the planned anon-GET /
two-principal probes either ran or are reported as not-run with the reason. A
ledger line with no verdict means the review is unfinished, and the verdict says so.
**When the audit fanned out, reconcile coverage per unit — who actually covered it
(finder id **and** lead-read `Y/N`) — and mark any unit whose finder did not
complete (slow, capped-out, crashed, refused) `unverified`, never absorbed into an
implied all-clear.** The "no silent caps" principle applies to the fan-out's own
completeness, not only to sampling inside a unit.

**Reconcile the report's *claims* against the delivered artifact, not only its
coverage.** The ledger reconciliation above asks *did every applicable surface get
ruled on*; this asks the sibling question — *does the artifact contain everything the
report says it does*. Enumerate the report's own claims — each finding's asserted
fix-state, each definition-of-done line, each "changed X" — as a list, and join every
one to the artifact that would prove it (a committed hunk, a passing test, a file that
exists), reporting **present, partial, or absent** and surfacing your own misses, not
only confirming hits. Join to the **committed diff**, never to a sub-agent's or a
lane's *report* of what it did — the per-unit rule in `method.md` records the lead's own
independent read (`lead-read Y/N`), not the finder's word that a unit is clean, and the
same holds for what a delegate claims it changed. Run this
**before you close, unprompted**: a completeness audit that only fires after the owner
asks "did you actually do all of it?" is not a control but a retrofit, and the
question itself is the signal the audit was owed earlier. It is cheap — the claim list
already exists and the diff is already in hand. This is the *set-completeness* question
that precedes per-claim verification: whether every claimed item is present at all,
before asking whether each is backed by a real surface rather than a favorable proxy.

**For a `DIFF` of a PR/MR** (often
a fork or an API-fetched change with no writable checkout) **the deliverable is
the review comment on the PR itself, not a committed file** — never add
`code-review/…` inside the very diff under review. **After writing it into the
repo, re-run the project's own privacy/name gate and link-check over the new
file** — it is untracked content the gate scans, and writing it can turn a clean
tree red. Surface every decision that needs a human owner. **Advise fixes; do
not auto-implement security/authz gates in this phase** — "helpful middleware"
is how outages ship when the Identity Arrival Map was skipped; security changes
ride a **separate** PR. **Split the remediation by risk surface:** when the
review yields both routine fixes and a change to a security/permission/authz
boundary, land them in **separate PRs** — the security-critical diff on its own,
small, flagged for a decorrelated reviewer, never buried under nit commits. Fixes
ride on a branch + PR (gated on approval), never a direct push to the default
branch. **For a FULL / repo-level review with open branches, also emit the
branch & merge triage** (domain S) — one recommendation per branch with the
exact command; acting on any of it (merge, delete, push, rebase) is
destructive/shared-state and runs only on explicit approval.

**A `mechanism-unproven` fix does not close its finding.** Report it as *mitigation
applied, cause unconfirmed*, keep the finding open at its original severity, and
name what would settle it (N green runs on the same job; the repro landing
red-first). For an intermittent failure "the symptom stopped" is not evidence —
never write "fixed" where the mechanism was only inferred.

**Phase 6 — Imprint standards (opt-in; writes to the repo).** Offer to persist a
tailored standards set so the bar holds on future iterations — a canonical
cross-vendor `AGENTS.md` (with `CLAUDE.md` and any peer agent files as thin
pointers to it), the pre-commit/CI gates, templates, and — where the repo will be
reviewed by a first-party bot — an optional **review-scoped rules block**
(`REVIEW.md` or a `## Code Review Rules` section, `references/docs-and-dx.md`),
distilled from this review's findings and the project's actual stack. This phase **writes**, so
it requires confirmation and must be net-positive and non-destructive:
**idempotent and additive** — detect-and-stop if present, create-if-missing
(never silently overwrite a good file), add only missing lines to a shared file,
and print what changed; defer to an existing style guide. **Pair each imprinted
standard with the gate that enforces it** — a doc alone is advisory — and if the
repo carries more than one agent-instruction file (`CLAUDE.md`/`AGENTS.md`/peers),
keep them from diverging. See `references/docs-and-dx.md`.
