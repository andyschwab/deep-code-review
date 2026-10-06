# Data quality depth — entity resolution and identity clustering

Read this when the target or diff resolves or clusters entity identity without a stable id (name or fuzzy matching, an external identity cluster, clusters built from pairwise links), weights a shared value as a match key, changes the entity roster or resolution logic, or runs a connector / transform pivot graph. Split from `data-quality.md`, whose core checks (monotonic writes, provenance, units, nulls, joins and keys, dedupe, freshness, idempotent writes) apply to every data review.

## Identity changes and the non-regression gate (depth of `data-quality.md` §1)

- **An identity / roster change re-attributes cached signals — classify the drop, don't blind-ack
  or blind-block.** A change that improves the entity roster or resolution (fills anchors, corrects
  matches) **re-keys attribution** across every cached downstream signal, so a per-dimension
  **volume drop** can be a **correction** (a signal re-attributed to a better-matched entity, or
  poisoned as newly-ambiguous — one handle now known to belong to two entities) rather than a
  **regression** (a valid attribution wrongly lost); the count alone cannot tell them apart. When an
  identity / roster / entity-resolution change is in the diff or ran in the pipeline, **investigate
  the fold** (which signals moved or dropped, and why) before acking (blind-ack ships a possible
  regression) or blocking (blind-block rejects a correctness improvement). The volume floor (and the run-over-run drift guard in `data-quality.md` §1) is the
  **trigger**; the fold investigation is the **adjudication** — after an identity/roster/ER change,
  "beyond-attrition drop = regression" names what to **investigate**, not the automatic verdict.

## Entity resolution (depth of `data-quality.md` §3)

- **Consume an external pre-computed identity cluster instead of running a forbidden internal model.**
  When resolving identity would need a model or number you are not allowed to run (a no-ML constraint,
  a spend gate, a privacy limit), the clean escape is to consume an **external, pre-computed** cluster
  or id — plus its **public artifact** (an authoritative registry id, a published disambiguation) — as
  the resolver, rather than fall back to a name-only match or ship the forbidden model anyway. Treat
  the external cluster as a **corroborating source** (`data-quality.md` §2 independence): record its provenance, and do
  not promote a lone external cluster to certainty. It keeps "skip rather than guess" intact when the
  in-house resolver is off the table.
- **Grade a shared value by frequency; don't treat it as all-or-nothing.** A value's
  weight as a match / join key is **inversely related to how common it is**: a field
  shared by two entities is signal (two co-founders, one company); shared by forty it
  is a role / vendor / generic value to **demote** as a key. Binary include/exclude is
  wrong both ways — it drops legitimate rare-value signal and trusts generic-value
  collisions. Compute a **deterministic value-commonness table** (distinct entities per
  normalized value) from data on hand — below a small **named** frequency band a value
  still counts, above it is demoted — and **scale the required corroboration by
  commonness** (a rare value clears a lower bar; a common one demands more independent
  evidence, since the chance it silently collapses two distinct entities rises with
  frequency). Thresholds are named constants with a rationale, never a tuned magic
  number; route any demotion that empties a field through the non-regression gate (`data-quality.md` §1).
- Prefer revealed-preference, hard-to-game, multi-signal evidence over a single
  vanity/attention signal.
- **Don't trust raw connected components — a bridge edge signals a false merge.** When clustering
  identities from pairwise links, taking **raw connected components** silently over-merges: one
  spurious `A~B` link plus a real `B~C` collapses two distinct entities (the transitive-chaining
  case a shared-key-collision gate never sees). Run **graph metrics** over the merge graph — a
  **bridge** edge (removing it splits the cluster), especially one backed by a **single artifact**
  joining two otherwise well-connected sub-clusters, is a prime false positive: flag or skip it and
  log why (skip-rather-than-guess); **low neighborhood overlap** (few shared neighbors between the
  edge's two endpoints — the weak-tie indicator) is a further false-link signal.
  Pure false-merge insurance — it does not conflict with monotonic-quality (`data-quality.md` §1); it keeps a bad
  merge from ever entering the bundle.

- **Attribute identity only after discovery is complete.** A multi-claimant question ("this channel belongs to
  team X") can only be decided once every claimant has been seen. Publishing an attribution mid-discovery makes
  the answer depend on crawl order and later claimants silently lose. Finish discovery across the whole population,
  then attribute; until then report the candidates, not a winner. Finding: any attribution written or published
  inside the discovery loop.
- **Attribute each item by its own owner, never by the page it appeared on.** A source that lists other
  parties' items (a calendar page that also shows partner or featured events) makes page-level attribution
  wrong. Check each item's own host or owner ID against the claimed owner. Attribute an item from a side source (for example JSON-LD event listings) to an org only through a hard key such as an equal host website or owner ID, never through a name match: a live measurement found only 14 of 318 name matches were real. A live-page check of one such
  port found 6 of 6 listed events belonged to other calendars. Finding: items attributed from the page or
  feed owner with no per-item owner check.

## Connector pivot graphs (depth of `data-quality.md` §10)

- **A connector/transform *pivot graph* multiplies both risks per hop — gate every
  hop, not just the chain end.** A pivot engine (identifier → transform → new
  entities → next transform; the Maltego / SpiderFoot pattern) is powerful for
  coverage but compounds two hazards a single-source lane does not have. (1)
  **Attribution risk multiplies:** a wrong entity at hop 2 poisons every entity
  derived at hops 3+, so each transform's *output* entities must re-pass the
  identity / fanout gate (`data-quality.md` §1 fanout arm, §3 false-merge) **before** attribution —
  not once at the end of the chain. (2) **Identity-disclosure risk multiplies:**
  each hop contacts a new host directly, so a pivot toward a gated host routes
  through a contracted broker under a declared collection-identity policy
  (anonymous / identified / brokered) — never spoof (`data-quality.md` §10) — and a pivot must not become a
  rate-limit-evasion fan-out. A pivot graph without per-hop guards is both a
  fanout amplifier and an identity-exposure amplifier.

**🚩 red flags** (this file):
a join / corroboration key not weighted by value-commonness (a value shared by dozens treated as a confirming match);
a per-dimension volume-floor drop acked or blocked with no fold investigation after an identity/roster/entity-resolution change (a correction and a regression are identical from the count);
an identity cluster built from raw connected components with no bridge / centrality check (transitive over-merge);

### A dedupe key needs the fact's own identity

A key built only from a lineage label many rows share (for example a non-navigable source ID) collapses an entity's whole history into one row. Include the fact's own name or date in the key. Test with two distinct facts from the same source and assert two rows survive.
