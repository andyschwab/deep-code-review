Read this when the review scope is a `DIFF` or `FILE` (a large or blast-radius-flagged DIFF, a fix that is itself the review target). Split verbatim from `method.md` Phase 2 and Phase 4; the phases every review runs stay there.

# Review method: DIFF and fix lenses

**On a `DIFF`, classify each changed hunk by *kind* before walking
domains — the PR's title and line-count are not the review's depth budget.** Bucket
the change into **mechanical** (a rename, a format-only reflow), **behavioral** (logic
changed on an *existing* path), and
**new-surface** (a brand-new route / endpoint / handler / consumer / permission — a new
trust boundary), and route each at matched depth: a mechanical hunk gets a fast
*confirm-it-is-mechanical* read (no behavior rode in on the rename — a moved guard, a
flipped default, a widened type); a behavioral hunk gets the full domain audit for the
paths it touches; and a **new-surface hunk gets the full Phase 3 adversarial opener set
(below) — every opener, not a subset (the dual-surface caller check is the one most
easily skipped) — regardless of the PR's stated size or title** — a new endpoint buried
in a PR titled "refactor" is both the highest-risk change and the easiest to wave through
at the diff's face value. The bucket, not the PR's framing, sets the depth. A hunk that
fits none cleanly — a pure deletion, a test-only or config-only change — defaults to the
**behavioral** read (toward more scrutiny, not less). (Distinct from Phase 0's blast-radius
*ordering*, which ranks what to review *first*; this sets what *depth* each hunk earns.)
**Multi-file or contract-changing `DIFF`: out-of-diff tracing is mandatory** (`method-situational.md`:
`impact_map.py`, `context_pack.py`).

**Intent-conformance — a lens distinct from correctness.** Besides "is the
code right," ask "does the change do what it *claimed*": does the diff satisfy its PR
description, linked issue, or stated acceptance criteria? A flawless implementation that does
X while the ticket asked for Y, or silently drops a stated requirement, is a finding — cited
to the **stated intent** available in context (the PR / issue text), and where no intent is
stated, say so rather than infer one. This is the review-side counterpart to the delivery
spec gate (`agentic-delivery` G1); it catches a whole class the domain audits, which ask only
"is it correct," miss. **Count-invariant for a claimed add/remove:** a diff that says it
*adds* an item — a list entry, a `case`, a config key, a test — is falsified by an unchanged
count. `git show <base>:<file> | grep -cE '<item shape>'` against the working copy must move by
the number claimed; a delta of **zero on an "add"** means the new text was spliced into an
existing item and silently **replaced** it (two items fused into one), and the mirror case
falsifies a claimed removal. The bytes stay valid, so lint, format, and checksums pass over the
fusion — only the count delta or a human read catches it (this review's own worked near-miss).

**Sweep-scope issue → enumerate the target set, diff it against the files touched.** When an issue's
scope is a sweep ("every page", "all mentions", "each handler"), do not accept "closes #N" on the
author's say-so: enumerate the target set yourself (a route list, a directory glob, a grep) and diff it
against the files the change touched. Any target not touched is a finding, or an explicit,
reasoned exclusion in the PR; the issue stays open for the remainder. A lane that covers 7 of roughly 20
pages and reports "done" is the failure this catches. Same discipline as **audit-every-implementation**
(Phase 4), applied to the issue's stated scope instead of one function's call sites.

**Rewritten browser spec → account for the retired coverage.** When a `DIFF` rewrites an
existing browser/E2E spec because its target surface became unreachable in the test
environment, do not pass the rewrite on its new-surface green: check that the coverage
the old spec provided is named as a gap and pinned by a source-level structural fallback,
and flag its absence as a finding. Procedure: `references/testing-ui.md` (*A
rewritten browser spec names its retired coverage*).

**A fix that already scoped itself to an
enumerated list is judged against that list — but a green test pinning the list proves
non-regression, not completeness.** The same class discipline runs in reverse when the
fix is the review *target*: a change that lands as *apply treatment T to instances
[named list]* — the routes a bug report named, the handlers an investigation walked —
ships a regression test over exactly those entries, and that test can only prove the
**named** instances do not regress; it is structurally incapable of proving the list
complete against the rest of the tree (the *a green gate clears only the surface it
enumerated* rule above, at remediation scope). The report enumerates the symptoms
someone hit — a **sample** of the qualifying shape, not its population — so re-derive the
shape precisely (a shared wrapper, a fetch shape, a missing guard) and run the same
independent sweep this bullet prescribes, then **diff the full match set against the
fix's named list**: whatever the sweep finds that the list omits is the gap, named. Such
a fix passes intent-conformance against the ticket and is still incomplete against the
code — the Phase 2 / Phase 4 seam. Separate an **acknowledged** boundary from a
**silent** one: a *category X stays a follow-up* note is legitimate when drawn after a
full enumeration, a real gap only when the search never left the ticket; and an
**easier**-to-fix sibling skipped while harder ones were fixed is the tell of an
accidental miss, not a deliberate deferral. (The field-shape version — patching a shared
request-body builder only where reported — is `domain-h.md`.) **The same completeness discipline also runs *inward*, into the file the
fix just landed in.** The sweeps above go *outward*, across the tree — grepping the fixed idiom (or the
re-derived shape) to land every instance, then re-grepping to confirm none survive. Two routine ways
of *verifying* a hardening fix defeat that check while leaving the fixed file's own other
paths unswept — paths that hold **no instance of the fixed idiom for a grep to reach**. A
fix justified by **parity with a sibling/twin file** (*"the other handler already guards
this; this one now matches it"*) supplies no idiom to grep at all, and proves only that
the fixed file is *as broad as* that sibling — never that it lacks a **second path to the
same data or sink**: an inner helper, a self-recursive branch, or another function
independently interpreting the same untrusted input, for which a flatter sibling has no
counterpart to match. A fix justified by a **top-level/outermost guard** (an
`isinstance`/type/auth/escaping check on the whole input) closes only the outer layer —
every `.get`/subscript/`for ... in`/decode on a *field beneath* it, in **any other
function of the same file**, is a separate, still-unguarded read of that value (not the
one-function rule in `reliability-error-handling.md`, which is other throwing calls
*inside a single function*; this is other functions across the file). So after matching
the twin or landing the outer check, **sweep the fixed file itself**: grep it for every
function, branch, and nested access reaching the same sink over the same input, name each,
and confirm the new guard's *actual scope* reaches it — the class is closed only when the
fixed file's own remaining paths are accounted for, not when the diff reaches parity with
a sibling or an outer check goes green. This is the **inward companion** to the outward
instance-set/named-list sweep: that one lands the siblings a fix skipped; this lands the
fixed file's own deeper paths the *verification method* skipped.
