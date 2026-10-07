# Language & stack red flags — grep-able footguns

Read this to turn the abstract checks in `SKILL.md` into concrete patterns you
can grep for in the target's language(s). These are **signals, not verdicts**:
each hit needs the surrounding context read before it becomes a finding. Tune
paths to the repo; exclude vendored/`node_modules`/generated code.

A fast first pass across any repo:

```bash
# secrets in tree or history (install gitleaks/trufflehog if available)
gitleaks detect --no-banner 2>/dev/null || grep -rInE \
  'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|-----BEGIN [A-Z ]*PRIVATE KEY-----' .
# leftover debug + markers
grep -rInE 'TODO|FIXME|HACK|XXX|@ts-ignore|eslint-disable|type: ignore|nolint' .
grep -rInE 'console\.log|print\(|dbg!|System\.out\.print|fmt\.Print' .
```

---

## Per-language red flags — load only the languages present

Each language family has its own file. Load the file for every language the target contains (Phase 0 detects them) and skip the rest:

| Language(s) present | Load |
|---|---|
| Python | `lang-python.md` |
| JavaScript / TypeScript | `lang-js-ts.md` |
| Go | `lang-go.md` |
| Java / Kotlin | `lang-jvm.md` |
| Ruby, PHP | `lang-ruby-php.md` |
| C / C++, Rust | `lang-c-cpp-rust.md` |
| Shell — any shell run by CI (`run:`), hooks, Dockerfile `RUN`, Makefile recipes, or scripts | `lang-shell.md` |
| SQL — any SQL string, ORM query, or migration | `lang-sql.md` |

The cross-language sections below (denial of service, the reviewer's own verification shell) apply to every review. The control-flow and arithmetic patterns (switch/case fallthrough and unreachable code, hand-rolled delimiter scanning, a floor undone by a later clamp, partition / ring validity gates) live in `redflags-situational.md` — load it on its trigger.

## Denial of service / resource amplification

- **ReDoS** — catastrophic backtracking from nested/overlapping quantifiers
  (`(a+)+`, `(.*)*`, `(\d+)*$`) on untrusted input, or an untrusted string
  compiled into a pattern (`new RegExp(userInput)`, `re.compile(userInput)`).
  Bound input length, prefer a linear-time engine (RE2), or apply a match timeout.
- **Null/nil dereference on a reachable path (CWE-476)** — a value from an external call, an
  optional/nullable lookup, or an unchecked cast that can be `null`/`nil`/`None`/`undefined` is
  dereferenced, called, or indexed **before a null check**, on an attacker- or upstream-reachable
  path: a **crash / DoS**, not merely a wrong-answer bug. Per language: a Go `nil` pointer/interface
  panic, a Java/Kotlin NPE (a `!!` on a nullable), a Python `AttributeError` on `None`, a JS/TS deref
  of `undefined` (a `!` non-null assertion papering over it), a C/C++ deref of a failed
  allocation/lookup return. Guard the unhappy path before the deref; cross-ref
  `reliability-error-handling.md` for the fail-closed + resource-release angle on the same crash.
- **Decompression / entity-expansion bombs** — an archive (`zip`/`gzip`/`tar`)
  extracted with no size or ratio cap, or XML parsed with entity expansion enabled
  (billion-laughs): a small input that inflates to gigabytes. Cap the decompressed
  size and disable external/DTD entity resolution.
- **Algorithmic-complexity / hash-flooding on attacker-chosen keys (CWE-407)** — a
  keyed structure (`dict`/`Map`/`HashMap`/`HashSet`) fed attacker-*chosen* keys, or
  a user-suppliable sort/dedup/group-by comparator (`sorted(data, key=...)`,
  `.sort((a, b) => …)`, a custom `Comparator`/`Comparable` driven by request data),
  degrades from amortized O(1) to O(n) per operation — O(n²) total — when the keys
  are crafted to collide into the same bucket, **even under a normal-looking
  item-count cap**: the count is fine, the *keys* are the attack (CWE-407's own
  observed examples, verbatim: "CPU consumption via inputs that cause many hash
  table collisions."). `performance-db-cost.md`'s count/iteration cap does not
  defend against this. Distinct from the GraphQL query-cost/batching/aliasing item
  in `security-api.md` — that's request-*multiplication* (more fields/operations
  than a per-request budget allows); this is worst-case complexity from
  attacker-*chosen values* inside one, already count-bounded request. Verify the
  target's hash-map implementation before prescribing a fix: a randomized hash
  seed/SipHash or a treeified-bucket fallback are known mitigation shapes for this
  class in general, but are **not** stated on the CWE-407 page and may already be
  the runtime's default — don't assert either way without checking.
- **Uncontrolled recursion on nested untrusted input (CWE-674, alternate term
  "Stack Exhaustion")** — a recursive-descent parser (hand-rolled, or a
  JSON/YAML/XML/protobuf library whose depth handling you haven't confirmed)
  walking attacker-supplied nesting (`[[[[[…]]]]]`, deeply nested objects) exhausts
  the call stack on a payload of a few KB (CWE-674's own observed example,
  verbatim: "Deeply nested arrays trigger stack exhaustion."). Distinct from the
  decompression bomb above — that's *byte-size* amplification, caught by an
  output-size cap; this is *call-stack depth*, which a tiny, low-byte payload sails
  through that same cap to reach. Distinct too from `security-api.md`'s API10
  "bound size and recursion" clause — that's the app **consuming an upstream
  response** (outbound/client direction); this bullet is the **inbound** direction,
  a public endpoint parsing an attacker-supplied request body. Distinct, too, from
  the generic "max depth" cost-cap in `performance-db-cost.md` (an efficiency bound,
  not a stack-crash defense) and from `security-api.md`'s GraphQL query-depth
  limit (which bounds resolver depth over a parsed query AST at the application
  layer, not a raw deserializer's call-stack depth at the syntax layer). Grep the inbound
  parse call itself (`json.loads(`, `JSON.parse(`, `yaml.safe_load(`, an XML
  tree-builder call, `Unmarshal(`, a protobuf `parseFrom`/`ParseFrom`) and check
  whether a max-depth/recursion-limit option is set **on that specific call** —
  don't assume a library's default nesting-depth behavior is either safe or unsafe
  without reading its docs for the version in use. Fix: set or confirm the
  library's max-depth option, or add an explicit fail-closed recursion counter, on
  the inbound-parsing path specifically.
- **Unbounded allocation from a declared/untrusted size value (CWE-789)** — code
  reads a size, count, or dimension *from inside the payload itself* (a JSON
  `"count"` field, an image's declared width×height, a multipart part-count) and
  pre-allocates a buffer/array to that size **before** validating the real bytes
  received, so a tiny request can claim a multi-gigabyte allocation (CWE-789's own
  observed examples: "a large value for number of records to return, leading to
  allocation of a large array"; "memory consumption and daemon exit by specifying a
  large value in a length field"). Grep an allocation call fed straight from a
  parsed field — `malloc(declared_size)`, `new byte[declared_size]`,
  `Buffer.alloc(declared_size)`, `make([]T, declared_len)` — and read backward to
  confirm whether that size traces to an unclamped value inside the payload.
  Distinct from the wire-level upload-size cap and the API10 "bound size" clause in
  `security-api.md` — both bound bytes actually *transferred*/received, not a
  size *claimed inside* a payload before those bytes arrive. Distinct too from the
  C/C++ "integer overflow before `malloc`" bullet in `lang-c-cpp-rust.md` — that's an *undersized*
  allocation from an overflowed calculation, leading to a buffer overflow (memory
  corruption); this is an *oversized* allocation from a value trusted as-is,
  leading to memory exhaustion (availability) — different consequence, different
  fix. Clamp the declared size to a sane ceiling before allocating, or allocate
  incrementally as bytes actually arrive.

## Shell / Bash

Reviewed-code shell footguns (unquoted expansions, `set -u` on empty arrays, locale-dependent bracket ranges) live in `lang-shell.md` — load it per the Shell row of the table above.

### The reviewer's own verification shell (measuring, not reviewing)

`lang-shell.md` hunts `pipefail` in *reviewed* code; these hazards apply to the
commands **you** run to establish ground truth, where an empty or wrong exit is
read as a pass (SKILL.md Phase 1). All measured, not asserted:

- **A pipe hands you the last stage's status.** `gate | tail`/`| head`/`| grep`/
  `| less` report the *reader's* exit, so a failing gate reads `0`. Preference
  order: (1) **capture then echo** — `./gate >/tmp/g.log 2>&1; echo "exit=$?";
  tail -20 /tmp/g.log` (no shell-dialect difference); (2) `set -o pipefail` before
  the pipeline; (3) read the array **on the very next command** — bash
  `${PIPESTATUS[0]}`, zsh `${pipestatus[1]}` (1-indexed, different name) — **any**
  intervening command, including a bare `:` no-op, resets it.
- **SIGPIPE reads as `141`, not the gate's code.** Under `pipefail`, a reader that
  exits early (`… | head -1`) makes the pipeline `141` — looks like a real failure
  and is not the gate's.
- **`grep -q` inverts success.** `grep` exits `0` when it *finds* the string —
  which may be the failure message, so `cmd | grep -q ERROR` "passes" on error.
- **Never `2>/dev/null` in a fact-establishing step.** It converts "the thing does
  not exist" into "the measurement came back clean." A classic trap:
  `git show <ref>:missing.sh >/tmp/x.sh 2>/dev/null; bash /tmp/x.sh; echo $?` —
  `git show` fails (path untracked), the capture is 0 bytes, `bash` on an empty
  file exits `0`, and the absent gate reads as a passing one. Assert non-empty
  output (or a known sentinel) before trusting any exit code.

## Infrastructure as code

Terraform / Kubernetes / Docker / cloud config have their own catalog — see
`infra-iac-containers.md`.

---

**Reminder**: a grep hit is a lead. Read the context, confirm the data flow from
an untrusted source to the dangerous sink, and only then record a finding with
`file:line`, impact, and fix. No fabricated line numbers.
