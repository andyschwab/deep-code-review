Read this when `method.md` routes here: a call site may bypass or re-derive a shared helper, component or predicate, or a new or changed correctness-bearing unit has no test that reaches it. Split verbatim from `method.md` Phase 2 and Phase 3.

# Review method: bypass and probe lenses

**Mine the code's own comments for admitted deviations — a class of finding a
structural search cannot reach.** The drift searches elsewhere in this method key on
*structure*: a duplicated component, a copied string or markup block, a repeated
scaffolding cluster (`ux-components.md`'s *one component per concept*
twin-search), or the inverse sweep that greps a hand-rolled `aria-modal` / skeleton and
diffs it against the shared primitive's importers (`a11y-focus.md`, `a11y-live.md`). All of them are
blind to a call site that **reimplemented** a shared component/helper/guard from
scratch and therefore shares no literal with it. But a developer who deliberately
bypassed a shared abstraction often **says so in a comment** — *"not using the shared
`<Select>`, it can't do X"*, *"hand-rolled instead of the DS modal because …"*,
*"inlined the fetch, the shared client doesn't fit here."* Grep those admissions as
their own pass — the phrasings cluster around a small set of tells (`instead of`, `not
using` / `not the shared`, `can't use`, `rather than`, `hand-rolled`, `workaround`)
sitting next to an import or a shared symbol's name — because each hit is worth **two**
findings at once: (1) this call site has drifted from the shared abstraction and may
have shed whatever correctness the shared version bakes in — an a11y behavior, a guard,
a dedup — the exact regression `a11y-live.md`'s bypass-the-shared-component family
names; and (2) the shared abstraction has a **real gap** its author already hit, so the
root-cause fix (principle 9) is usually to close that gap at the source rather than
bless the workaround. It is higher-confidence than a cold duplicate search because the
author **pre-verified** the deviation for you: the comment is a first-party admission
that the shared path did not fit. **Opposite polarity from the two other
comment-as-claim rules in this method** — the carried-forward suppression-reason (Phase
1, `method-situational.md`) and the incident-narrating comment (Phase 4) warn you *not to over-trust* a comment
as still-true; this *harvests* a class of comment that **is** a finding you would
otherwise miss. And distinct from `ux-components.md`'s adoption-is-total move,
which reads the **shared component's own** doc-comment (it names the call sites it
fixed) to hunt stragglers — this reads the **call site's** comment to find the bespoke
bypass that never touched the shared component at all. Treat a match as a finding to
confirm at source (read the workaround; confirm it still bypasses the shared thing at
HEAD), not as proof on its face — the comment may itself have drifted, per the Phase 1
rule (`method-situational.md`).

**Diff every ad-hoc re-derivation of a *canonical* predicate against the canonical — a
partial reimplementation reads real fields yet tests a *subset* of the conditions.** A
specific, high-frequency case both the comment-mining pass above and the copyable-idiom
sweep (Phase 4) miss: the project **correctly centralizes** a boolean — *is this fully
configured / wired / eligible / complete* — in one shared helper that legitimately requires
**A and B** (`isWired = x => x.hasKey && x.hasWebhook`), but somewhere else a **count,
filter, badge, or percentage** re-derives the *same* concept inline and implements only
**part** of it (`items.filter(x => x.hasKey).length`, dropping `hasWebhook`). Every field it
reads is genuine and the code looks right in isolation; the only symptom is that a
**user-facing count/percentage silently disagrees with the canonical predicate** — the
dashboard says "8 of 10 configured" while the helper that actually gates behaviour counts 6.
A grep for the *idiom* (Phase 4) will not find it — the re-derivation shares no literal with
the helper — and no comment admits the bypass (the comment-mining pass above), because the
author did not think they were bypassing anything; they re-expressed a "simple" check.
**Technique: start from the canonical predicate, not from a duplicated string.** Enumerate
the fields/conditions the shared helper reads (`hasKey`, `hasWebhook`), then grep every site
that reads **any** of them in a boolean/count/filter context and diff its condition set
against the canonical's — a site that tests a **proper subset** is the finding. **Fix: call
the shared predicate; never reimplement a subset of it** — a count over
`items.filter(isWired)` cannot drift from the gate. **Adjudication vs the nearest rules:**
distinct from `testing-situational.md`'s *diff-the-guard-conditions-across-N-sibling-copies*
(that has **no** canonical — N peer copies drifting from one another, fixed by reconciling or
extracting them; here a **designated canonical exists** and the bug is one **narrower**
re-derivation of it, fixed by calling it); distinct from a **value-set** subset (a data set
missing members, not a predicate missing a conjunct); and distinct from the
**audit-every-implementation** sweep (Phase 4, which fans a fix across every call site of one
function — here the re-derivation is **not** a call site of the helper at all, which is
exactly why a call-site audit skips it). It is the **structural-search complement** to the
comment-mining pass above: that pass catches a bespoke reimplementation via the developer's
*admission comment*; this catches one that shares neither a literal nor a comment, by keying
on the **fields the canonical predicate reads**.

**Beyond the security openers, author a disposable probe test to *discover* an
unsuspected defect in changed logic — do not stop at the tests that already exist.**
Each dynamic move so far leans on something already present: the planted-defect
probe (Phase 1) mutates code to prove a *gate* catches a *known, injected* defect;
fix-verification (Phase 4 below) runs the *existing* suite against a *suspected*
finding; the openers above attack a *running* security surface. None exercises a
new or changed **correctness-bearing** unit — a calculation, a state transition, a
parser/validator, an off-by-one boundary — when no test reaches it. For such logic,
write a **minimal, disposable** test that calls it at its stated boundary conditions
in the same throwaway worktree at `START_SHA` the planted-defect probe uses — the
same transient-worktree-probe mechanism principle 7 permits, never the working tree.
As Phase 1 reverts and confirms its planted defect, **delete the probe and confirm it
is gone** when done, so no unprompted write is left standing. A
**red** result is a finding with a real repro attached — a stronger claim than a
static read. A **green** result records only *"no defect at the inputs probed,"*
with the probe and its inputs; it is **not** an invariant, and is promoted to a
`checked_sound` / *Invariants verified to hold* row (`report-format.md`) **only if
the test pins the property** across the input class, not one example. **Bound the
blast radius before you run it:** the throwaway worktree contains *filesystem*
effects, not *outbound* ones — if the unit cannot be exercised without a network,
paid, or stateful call (a payment or model-calling handler, a live DB write),
**stub that boundary or skip**, and record `could-not-check` (distinct from
found-nothing) rather than fire a real side effect to get a result. The
confirm-before-billable-or-shared-state caution and the could-not-check-vs-found-nothing
discipline bind the reviewer's own probe, not only the target's gates.
