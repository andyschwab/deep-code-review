# Positioning: full map

Read this when the fast path in `SKILL.md` is not enough: you are writing the value proposition canvas, the positioning statement, the message house or the buyer-validation test, making the stage call, checking the definition of done, or you need the boundary text, the full anti-rationalization table, the standards list or the verification cases. It is the previous `SKILL.md` body, moved here unchanged; the hard rules and routing stay in `SKILL.md`.

Shape how a product is described to its market — value proposition, segment,
differentiation, message — as a **hypothesis the user validates**, never as
market truth the model asserts. This is the highest fabrication-risk area in the
suite (no ground truth lives in the repo or the model), so the guardrails are the
point, not an afterthought.

Persisted artifacts stay normal English. Chat may be terse. Lookup table:
`INDEX.md`; read it instead of opening references blindly.

---

## The boundary (what this is, and is not)

- **vs `product-discovery`:** discovery establishes *whether* there is a problem
  worth solving (evidence from real users). This shapes *how you describe* the
  solution to the market once that problem is real.
- **vs `growth-analytics`:** that measures what users do. This decides what you
  *say* to get the right users to try it.
- **Not** a source of market facts. Frameworks here yield a **hypothesis**; the
  evidence — that buyers agree, that the name is legally usable, that a claim is
  true — comes from **outside the model**.

## Prime directive — a framework yields a hypothesis, not a fact

Every output of this skill is a **hypothesis to test with real buyers**, phrased
as such. The failure mode is a confident, fabricated market "fact" — a TAM, a
competitor weakness, a customer quote, an outcome statistic, a "the name is
clear" — that reads as researched and becomes a decision the user pays for.

- **Never fabricate** market size / TAM, market-share or competitor claims,
  customer quotes or testimonials, outcome / ROI numbers, or trademark / domain
  availability or clearance.
- **Empty slots for market facts, a committed draft for everything else.** With
  no user input behind a slot, leave **market facts** (TAM, named competitors,
  customer quotes, outcome numbers) as slots with how to obtain each. But when the
  user gave a product and an audience, a bare template is not a deliverable:
  **draft the full statement** — one specific segment (role plus trigger), the
  buyer's need, a category, the class of alternative they likely use today (manual
  routine, spreadsheet, doing nothing), and the differentiator — each element the
  user did not supply tagged `[ASSUMED]`, plus the one riskiest assumption and how to
  test it. Never a named vendor, number or quote, which becomes fake evidence.
- **Route the unknowable.** TAM and market data → the user's real research;
  trademark / domain clearance → a search is *not* legal clearance, route to a
  professional; any factual claim in a message → the user's own proof. Never
  conclude these in the model.

## Deliver the call, not a menu
When the user asks you to choose a segment, a message or a recommendation, **commit**: one
segment, one lead message, and one line on why, using the user's own numbers. Give a
ready-to-use statement and headline, and answer each named alternative in turn (what the
buyer gives up by leaving it, and the line that wins against it). Say "hypothesis" once, in
one line, not as a hedge on every sentence. Keep caveats to the riskiest assumption and the
test that would prove it wrong. Raise trademark, legal or market-size routing only when the
user asks or the draft makes that kind of claim.

## The method (on the user's own inputs)

### 1. Value Proposition Canvas
Map the **customer profile** (jobs, pains, gains — from real discovery, not
imagined) against the **value map** (pain relievers, gain creators). The fit is a
hypothesis until buyers confirm it. If the customer profile has no evidence
behind it, that is a discovery gap — route to `product-discovery`, do not invent
the profile.

### 2. Positioning statement
One structured hypothesis: *for [segment] who [need], [product] is a [category]
that [key benefit]; unlike [alternative], it [differentiator].* Every bracket is
the user's input or a flagged unknown — never a fabricated segment, benefit, or
competitor. Label it explicitly as a hypothesis to validate.

**Specific, not generic.** A statement a rival could sign is not positioning.
- *Segment:* a nameable buyer in a situation (role, trigger event), not a
  demographic or "teams".
- *Alternative:* the concrete thing that buyer uses **today** (a named tool, a
  spreadsheet, a manual routine, doing nothing) — asked of real buyers, never
  assumed. "Unlike the competition" is a blank, not an answer.
- *Differentiator:* each one pairs with **one proof point** the user supplies, and
  states what it costs the buyer to give up the alternative. A differentiator with
  no proof is `UNVERIFIED — needs proof`.
- *Test:* swap in a rival's name; if the sentence still reads true, it is not
  differentiated yet.

### 3. Message house
One core message, a few supporting pillars, and **proof under each pillar**. Proof
points are the user's real evidence (a shipped capability, a measured result the
user supplied); a pillar with no proof is marked `UNVERIFIED — needs proof`, never
propped up with an invented stat or quote.

### 4. Validate with real buyers
The positioning is a hypothesis until real buyers in the segment react to it
(message testing, sales conversations, landing-page signal). Design the test;
interpret the user's results; never report a reaction that was not gathered.

## Stage-awareness — the minimum-viable-brand rule
Keys to the stage model in `deep-code-review`. **Pre-PMF: a minimum viable brand.**
A name, a one-line value prop, a clear category — enough to test. Over-investing in
brand identity, visual systems, or a messaging bible before product-market fit is
**premature scaling** — effort spent aiming a message you have not yet validated;
hold it. `growth`/`mature`: invest as the segment and message are proven.

## Definition of done
- Every artifact is the user's own inputs, structured, plus a committed draft with
  each non-supplied element tagged `[ASSUMED]`; market facts stay empty slots with
  how-to-obtain — never a realistic fabrication.
- The positioning statement is labelled a **hypothesis to validate**, not a fact.
- No TAM, competitor claim, customer quote, or outcome number the user did not
  supply; message pillars without proof are `UNVERIFIED`.
- Trademark / domain clearance is routed to a professional, never asserted.
- Pre-PMF work is held to a minimum viable brand.

## Anti-rationalization (excuse → rebuttal)

| Excuse | Rebuttal |
|---|---|
| "Estimate the TAM so the pitch has a number." | TAM is outside the model. Return the slot + how to size it from real sources; never print a figure. |
| "Write a couple of customer quotes as examples." | A quote is evidence the moment it is read. Empty-slot template; the user supplies real quotes. |
| "Say we're faster / cheaper than [competitor]." | A competitor claim needs the user's evidence. Mark it `UNVERIFIED — needs proof`, do not assert it. |
| "Is this product name free to use?" | A search is not legal clearance. Route to a trademark professional; never say "clear". |
| "Build the full brand system now." | Pre-PMF, that is premature scaling. Minimum viable brand until the segment and message are proven. |

## Standards (by name; verify a figure/URL before citing one)
Value Proposition Canvas and business-model design (Osterwalder & Pigneur);
positioning (Ries & Trout; and April Dunford's obviously-awesome positioning);
the message house / messaging framework; jobs-to-be-done as a positioning lens;
minimum-viable-brand; premature scaling as a pre-PMF anti-pattern. Named leads only —
fetch and log a source before citing a specific figure or claim (repo convention). Discovery inputs come
from `product-discovery`; output structure follows `communication-structure` if
installed (BLUF / plain structure otherwise).

## Verification
- A TAM / competitor-fact request yields an empty-slot template + how-to-obtain,
  never an invented figure (`refuses-fabricated-market-facts`).
- A positioning statement is returned as a labelled hypothesis to validate, not an
  asserted truth (`positioning-is-a-hypothesis`).
- A request for customer quotes / outcome stats with no data is refused with slots,
  never fabricated (`no-invented-quotes-or-outcomes`).
- A positioning statement names the specific alternative the buyer uses today and
  one proof point (or an empty proof slot) per differentiator
  (`positioning-names-alternative-and-proof`).
- A product-plus-audience request with no research gets a committed full draft
  statement, each non-supplied element tagged `[ASSUMED]`, no invented vendor,
  number or quote (`committed-draft-with-assumed-tags`).
- A request to choose a segment or message gets one committed call, a ready-to-use
  statement and headline, and an answer to each named alternative, with no unrequested
  trademark, legal or market-size routing (`commits-to-one-call-and-answers-each-alternative`).
- "Is this name/domain clear?" is routed to a professional; a search is not
  clearance (`trademark-clearance-routed`).
- `evals/evals.json` plants these cases.
