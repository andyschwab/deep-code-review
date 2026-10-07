# Control-flow, parsing and boundary red flags — situational

Read this when the target or diff has `switch`/`case`/`match` control flow or unreachable code, a hand-rolled delimiter or frontmatter/multipart scanner, a minimum-size floor followed by a boundary clamp on the same value, or a partition / ring / segmentation validity gate. Split from `language-stack-redflags.md`, whose fast first pass and denial-of-service section apply to every review; each hit here is a signal, not a verdict.

## Switch/case control flow & unreachable code

A linter or compiler catches every pattern in this section on its first run — ESLint,
`go vet`, a C/C++ `-Wswitch`/`-Wimplicit-fallthrough` build flag, a Rust
`#[deny(unreachable_code)]` — which is exactly why a general review skips it. It survives
in an **AI-authored diff** (a model pattern-matches "add a `break`" without checking which
language it's in — see below), a **lint-exempted line** (`eslint-disable`, a suppressed
compiler warning), or **a language/toolchain the target's CI doesn't lint at all** (a
secondary service off the main gate). A hit in any of those three contexts is
higher-confidence, not lower.

- **Switch/case fallthrough is a cross-language reversal, not a universal rule — "add a
  `break`" is right in one family, a compiler error to even need in another, a no-op in a
  third, and meaningless in a fourth.** C, C++, and JavaScript/TypeScript — plus Java's
  classic colon-`case X:` form — fall through by default: omitting `break`/`return`/
  `throw` silently runs execution into the next case. ESLint's `no-fallthrough`
  ("Disallow fallthrough of case statements") flags any such case; the sanctioned
  intentional-fallthrough marker there is a comment matching `/falls?\s?through/i`
  (provided it isn't itself an ESLint directive comment), and C++17 gives the language
  itself a marker via the `[[fallthrough]];` statement attribute ("May only be applied to
  a null statement to create a fallthrough statement," cppreference) — don't assume
  either marker is recognized outside the tool/standard that defines it. **Go** is the
  reverse default: every case implicitly stops, and falling through requires the explicit
  `fallthrough` keyword as the case's last statement — the Go spec: "the last non-empty
  statement may be a … `fallthrough` statement to indicate that control should flow from
  the end of this clause to the first statement of the next clause. Otherwise control
  flows to the end of the `switch` statement." **Swift** shares Go's no-fallthrough
  default — "In Swift, `switch` statements don't fall through the bottom of each case and
  into the next one" — and, unrelated as the two languages are, spells its opt-in keyword
  identically: "you can opt in to this behavior on a case-by-case basis with the
  `fallthrough` keyword" (Apple's Swift Programming Language guide). **C# looks like the
  C family** — colon-`case`, braces, a trailing `break` — but the compiler rejects
  implicit fallthrough outright: "Within a switch statement, control can't fall through
  from one switch section to the next," and "Every switch section must end with a break,
  goto, or return. Falling through from one switch section to the next generates a
  compiler error" (Microsoft's C# reference). A missing `break` in C# cannot ship;
  deliberately reusing another section's logic takes an explicit `goto case` to a
  constant case label ("you can also use the goto statement in the switch statement to
  transfer control to a switch section with a constant case label," Microsoft's C#
  jump-statements reference) — C#'s differently-spelled answer to `fallthrough`. **Rust's
  `match`** has no fallthrough mechanism to opt into at all: "The first arm with a
  matching pattern is chosen as the branch target of the match … and control enters the
  block" (The Rust Reference) — exactly one arm ever runs. Even inside Java, the modern
  arrow form (`case L ->`, Java 14+) switched sides: Oracle's docs confirm arrow labels
  "eliminate the need for break statements to prevent fall through" — only the classic
  colon form keeps Java's C-style default. Confirm both the language **and** the switch
  syntax before treating a missing terminator as a bug, or its presence as a no-op. (This
  is switch/case control flow, not the `||`-falsy-skip "fall through" in `lang-js-ts.md`'s
  JavaScript section — that's operand short-circuiting, unrelated to case labels.)
- **Code after an unconditional `return`/`throw`/`break`/`continue` is unreachable** —
  almost always a logic error, not harmless dead code: a guard clause that stopped
  guarding after a refactor, or a merge artifact that pasted a stale block past the exit
  meant to precede it. ESLint's `no-unreachable` ("Disallow unreachable code after
  `return`, `throw`, `continue`, and `break` statements") and CodeQL's
  `js/unreachable-statement` (CWE-561) both flag it; CodeQL's rationale: "An unreachable
  statement almost always indicates missing code or a latent bug and should be examined
  carefully." Distinct from the unreferenced-code item in `domain-h.md` —
  that's a live, reachable function/import nobody calls; this is a dead *branch* inside a
  function that **is** called, where one path through it never runs.
- **A `let`/`const`/`class`/`function` declared inside one `case` without a block is
  visible to every sibling case, not scoped to the case that declares it** — it's
  hoisted (`function`) or sits in the temporal dead zone (`let`/`const`) for every other
  branch of the same `switch`, so a sibling case can read an uninitialized binding or
  collide with it. ESLint's `no-case-declarations` ("Disallow lexical declarations in
  case clauses") is the detector; the fix is to wrap each case body that declares one in
  its own `{ }` block.
- **A duplicate `case` label is a dead second branch, and a plain statement label sitting
  inside a `switch` body reads like a case label but isn't one.** CodeQL's
  `js/duplicate-switch-case` (CWE-561): "if two cases in a switch statement have the same
  label, the second case will never be executed. This most likely indicates a copy-paste
  error" (ESLint's equivalent: `no-duplicate-case`, "Disallow duplicate case labels").
  CodeQL's `js/label-in-switch`: a non-case label mixed into a switch body is "most
  likely the result of a typo" for `case N:`.

Grep lead: a `case` in a C-family file (`.c`/`.cc`/`.cpp`/`.java`/`.js`/`.ts`) with no
`break`/`return`/`throw`/`continue` before the next `case`/`default`/closing `}`; a
non-comment line immediately following a `return`/`throw` at the same indent level. Both
are leads, not verdicts — read the surrounding control flow before recording either as a
finding.

## Hand-rolled parsing & delimiter scanning

- **A "find the terminator" scanner that stops at the *first* line/token equal to the
  delimiter mis-parses when that delimiter can also occur *legitimately as content* before
  the real terminator.** Hand-rolled splitting of a structured header from a body — the
  closing `---` of a YAML/TOML frontmatter fence, an end-of-headers blank line, a `--boundary`
  in a multipart body, a here-doc terminator, a section separator — commonly scans for "the
  first line/token that equals `X`" and treats it as the end. It silently misparses the moment
  `X` can appear *inside* the content it scans over: a `---` on its own line within frontmatter
  (a horizontal rule, a `---` list item, a value that contains it), a blank line inside a
  folded block, a chosen multipart boundary that also occurs in a part's bytes. The scanner
  stops early, splits at the wrong point, and hands both halves downstream **without raising** —
  a truncated header parsed as "complete", body content swallowed into the header (or the
  reverse) — so the corruption surfaces far from the parse. It survives review because the
  happy-path fixture (no `X` in the content) passes; the bug needs content that *contains* the
  delimiter, which fixtures rarely include. Fixes, most robust first: **use a real parser** for
  the format (a YAML / MIME / multipart library) instead of a line scan; if hand-rolling,
  require the **open+close structure** (a frontmatter block must both open *and* close with the
  fence — a lone opening fence is an error, not an empty body), **count** paired fences rather
  than matching the first, pick a multipart boundary **proven absent** from the payload, and
  **raise on the ambiguous/malformed case** rather than returning a best-effort split. Grep
  lead: a `split`/`indexOf`/`find`/`readline` loop comparing a line against a literal delimiter
  (`=== '---'`, `== "---"`, `.startswith('---')`, `line == boundary`) with no bound, no fence
  count, and no error branch. (Distinct from the switch/case "missing terminator" above — that
  is a `break`/`fallthrough` control-flow default; this is a *data*-delimiter scan that ends the
  wrong span.)

## Composed numeric bounds — a floor and a later clamp

- **A min-size floor is silently undone by a *later* boundary clamp that re-bounds the same
  value against room computed from a dependent dimension.** One line enforces a floor —
  `size = Math.max(size, MIN)` ("keep a zero-length item visible", a minimum column width, a
  minimum touch-target) — and a later, independently-correct line bounds the same variable to
  the space that is left — `size = Math.min(size, TRACK_END - position)` (don't overflow the
  track / container / page). Each line is right on its own, but **composed** they violate the
  floor's own invariant: whenever `position` sits within `MIN` of the far edge,
  `TRACK_END - position < MIN`, the `Math.min` wins, and the result drops **below** `MIN`
  (often to `0` or negative) — exactly the state the floor existed to prevent, reachable only
  near a boundary the happy-path test rarely exercises. The two lines are usually far apart (the
  floor in a sizing helper, the clamp in a layout/paint pass), so neither reads as wrong in
  isolation and the item simply "disappears" or collapses near an edge. Fix: **re-assert the
  floor after the clamp** (`size = Math.max(Math.min(size, room), MIN)` — then decide explicitly
  whether the item overflows or the container grows, because you can no longer satisfy both), or
  **clamp `position` first** so `room >= MIN` holds by construction. Grep lead: the same variable
  passed through a `Math.max(…, K)` / `max(…, K)` **and** a later `Math.min(…, expr)` /
  `min(…, expr)` (or `clamp()` calls) where `expr` derives from a position/offset — read whether
  any later bound can fall under the earlier floor. Distinct from a single size-cap clamp
  (`security-api.md` clamps a requested size to a hard maximum — one bound, no floor for it to
  undo); the defect here is the **composition** of two individually-correct bounds, not either
  bound alone.

## Partition / segmentation validity gates — the minimal terminal segment

- **A validity gate that checks a partition/segmentation accepts every interior piece but
  rejects a *valid* decomposition whose **last** piece is the minimum allowed size — an
  off-by-one at the terminal (or wraparound) boundary.** A routine that carves a sequence
  or a **ring** (a directed cycle of `N` nodes indexed `0..N-1`, split into sub-cycles by
  "backward chord" edges) into contiguous pieces derives each interior piece's size the
  same way, but the **terminal** piece is computed from *what remains* — a remainder, or a
  wraparound index that must close back onto the start — so its size is a *different*
  expression from the interior ones. A check written and tested against interior pieces
  (`len > MIN`, `end - start > MIN`, `next = i + 1` with no `% N`) then mishandles the
  terminal piece at its smallest legal size: the strict `>` rejects a piece that is
  *exactly* `MIN` (it needed `>=`), or the un-wrapped `i + 1` runs off the end instead of
  returning to `0`. The result is a **false rejection** — a decomposition that is genuinely
  valid is reported invalid (or the routine throws / returns an out-of-range index), the
  mirror of the usual off-by-one that *admits one too many*. It survives because happy-path
  fixtures use uneven pieces where the last one sits comfortably above `MIN`; the boundary
  only bites when the terminal piece lands *at* the floor. **Fix:** make the terminal
  comparison inclusive (`>=` / `<=`, matching the interior pieces' true contract), compute
  every ring index modulo `N`, and assert the **partition invariant** — the piece sizes sum
  to `N` and each piece (the last included) is `>= MIN`. **Test** the degenerate boundaries
  explicitly: `N` and `N - 1`; the **all-minimal** decomposition (every piece exactly `MIN`,
  so the terminal piece is minimal too); and a decomposition whose *only* minimal piece is
  the terminal one. Distinct from the composed-floor-and-clamp defect above — that is two
  individually-correct numeric bounds whose *composition* violates a floor; this is a
  **single** boundary comparator one step too strict at the *terminal / wraparound*
  position, wrongly rejecting a valid input rather than admitting an invalid one.
