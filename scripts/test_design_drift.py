#!/usr/bin/env python3
"""Contract tests for design_drift.py over fictional fixtures built in a temp dir.

Covers the three token sources (CSS vars, JSON, DESIGN.md), each rule's flag and pass cases, the nearest-token
text, exit codes (2 only with --strict), the missing/empty token notice, --base, --json and bad arguments.
Prints "Tests: P/N".
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRIFT = ROOT / ".claude/skills/deep-code-review/scripts/design_drift.py"
sys.path.insert(0, str(DRIFT.parent))
import lint_ui_slop  # noqa: E402

results = []

CSS_TOKENS = """:root {
  --color-brand: #112233;
  --color-ink: #000000;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 1rem;
  --radius-md: 8px;
  --font-body: "Inter", sans-serif;
  --font-weight-bold: 700;
}
"""
JSON_TOKENS = {"color": {"brand": {"$value": "#112233"}}, "space": {"1": "4px", "2": {"value": "8px"}, "3": "1rem"}, "radius": {"md": "8px"},
               "font": {"body": "Inter, sans-serif"}}
DESIGN_MD = """# Acme design
- **color-brand**: `#112233`
| name | value |
| --- | --- |
| space-1 | 4px |
| space-2 | 8px |
| space-3 | 1rem |
| radius-md | 8px |
- font-body: Inter, sans-serif
"""
BAD_CSS = """.a { color: #112234; }
.b { padding: 13px 8px; margin: 0 auto; }
.c { border-radius: 7px; }
.d { font-family: Georgia, serif; }
.ok { color: #112233; background: var(--x); padding: 8px 1rem; gap: 4px; border-radius: 8px; font-family: Inter, sans-serif; }
.pill { border-radius: 9999px; font-family: system-ui; }
/* .hidden { color: #abcdef; } */
"""


def check(ok, name):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name)


def run(*args, cwd):
    return subprocess.run([sys.executable, str(DRIFT), *map(str, args)], capture_output=True, text=True, cwd=cwd)


def rows(p):
    return [(x["line"], x["rule"]) for x in json.loads(p.stdout)]


EXPECT = [(1, "off-token-color"), (2, "off-token-space"), (3, "off-token-radius"), (4, "off-token-font")]

with tempfile.TemporaryDirectory() as td:
    tmp = Path(td).resolve()
    for name, tok in (("css", None), ("json", None), ("md", None)):
        d = tmp / name
        (d / ".git").mkdir(parents=True)
        (d / "a.css").write_text(BAD_CSS)
    (tmp / "css/tokens.css").write_text(CSS_TOKENS)
    (tmp / "json/design-tokens.json").write_text(json.dumps(JSON_TOKENS))
    (tmp / "md/DESIGN.md").write_text(DESIGN_MD)

    for name in ("css", "json", "md"):
        p = run("--json", "a.css", cwd=tmp / name)
        check(p.returncode == 0 and rows(p) == EXPECT, f"{name} tokens: 4 rules flag lines 1-4, on-token/var/auto/pill/comment pass, exit 0")
    msgs = [x["message"] for x in json.loads(run("--json", "a.css", cwd=tmp / "css").stdout)]
    check("nearest --color-brand = #112233" in msgs[0] and "nearest --space-3 = 1rem" in msgs[1]
          and "nearest --radius-md = 8px" in msgs[2] and "nearest --font-body = Inter" in msgs[3], "each finding names the nearest token")
    p = run("a.css", cwd=tmp / "css")
    check(p.stdout.splitlines()[0].startswith("a.css:1: off-token-color: #112234"), "text output is path:line: rule: message")
    check(run("--strict", "a.css", cwd=tmp / "css").returncode == 2, "--strict with findings exits 2")
    (tmp / "css/ok.css").write_text(".ok { color: #112233; padding: 8px; }\n")
    p = run("--strict", "ok.css", cwd=tmp / "css")
    check(p.returncode == 0 and not p.stdout, "--strict on a clean file exits 0")

    (tmp / "css/b.tsx").write_text("const s = { padding: 12, margin: 8, borderRadius: 5, color: '#ABCDEF' };\n")
    got = rows(run("--json", "b.tsx", cwd=tmp / "css"))
    check(sorted(r for _, r in got) == ["off-token-color", "off-token-radius", "off-token-space"],
          "JSX numbers count as px: padding 12 and radius 5 flagged, margin 8 passes")

    (tmp / "css/tokens.css").write_text(CSS_TOKENS + ".x { padding: 13px; color: #abcdef; }\n")  # would be flagged if scanned
    p = run("--json", "tokens.css", cwd=tmp / "css")
    check(p.returncode == 0 and json.loads(p.stdout) == [], "the token file itself is never scanned (discriminates: its own content has findings)")
    (tmp / "css/tokens.css").write_text(CSS_TOKENS)

    # probes: one per review finding (each fails on the pre-fix code)
    def probe(name, tokens, src, ext=".css", tfile="tokens.css"):
        d = tmp / f"probe-{name}"
        (d / ".git").mkdir(parents=True)
        (d / tfile).write_text(tokens)
        (d / f"p{ext}").write_text(src)
        return rows(run("--json", f"p{ext}", cwd=d))

    SP = ":root { --space-2: 8px; --radius-md: 8px; }\n"
    check(probe("round", SP + ":root { --background-size: 3px; --rounded-lg: 12px; }\n", ".a { border-radius: 3px; }\n.b { border-radius: 12px; }\n")
          == [(1, "off-token-radius")], "radius token needs the word radius/round(ed): --background-size is not one")
    check(probe("letter", SP + ":root { --letter-spacing-wide: 3px; --whitespace-x: 5px; }\n", ".a { padding: 3px; }\n.b { padding: 5px; }\n")
          == [(1, "off-token-space"), (2, "off-token-space")], "letter-spacing and whitespace names are not spacing tokens")
    check(probe("em", ":root { --space-8: 8px; --space-em: 2em; }\n",
                ".a { padding: 0.5em; }\n.b { padding: 1.5em; }\n.c { padding: 13px; }\n.d { padding: 32px; }\n")
          == [(3, "off-token-space"), (4, "off-token-space")],
          "em is neither a token (--space-em: 2em is not 32px) nor checked (0.5em is not 8px, 1.5em is not 24px)")
    camel = {"spaceMd": "8px", "radiusLg": "12px", "borderRadius": {"sm": "4px"}, "padding": {"x": "16px"}, "gapSm": "6px", "spacing": {"lg": "24px"}}
    check(probe("camel", json.dumps(camel), ".a{padding:8px;border-radius:12px}\n.b{padding:16px;gap:6px;margin:24px;border-radius:4px}\n",
                tfile="tokens.json") == []
          and probe("camel2", json.dumps(camel), ".a{padding:9px;border-radius:5px}\n", tfile="tokens.json")
          == [(1, "off-token-space"), (1, "off-token-radius")], "camelCase token names (spaceMd, radiusLg, borderRadius.sm) are recognised and still checked")
    check(probe("hair", SP, ".a { padding: 1px 2px; }\n.b { padding: 3px; }\n.c { margin: -1px; }\n") == [(2, "off-token-space")],
          "1px and 2px hairlines are exempt from the spacing check")
    check(probe("var", SP + ":root { --color-brand: #112233; --font-body: Inter, sans-serif; }\n",
                ".a { padding: var(--space-2) 13px; }\n.b { padding: var(--space-2) 8px; }\n.c { color: var(--c, #abcdef); }\n"
                ".d { background: url(img.svg#fee); }\n.e { font-family: var(--f), Georgia; }\n") == [(1, "off-token-space")],
          "mixed var() declaration flags only the literal part; var() fallback, url(#frag) and a var() font pass")
    check(probe("neg", SP, ".a { margin: -13px; }\n.b { margin: -8px; }\n") == [(1, "off-token-space")],
          "negative margins compare by magnitude (-13px flagged, -8px passes)")
    (tmp / "dtcg").mkdir()
    (tmp / "dtcg/.git").mkdir()
    (tmp / "dtcg/tokens.json").write_text(json.dumps({"$schema": "x", "font": {"$type": "fontFamily", "$description": "type", "body": {"$value": "Inter", "$type": "fontFamily"}},
                                                      "color": {"$type": "color", "brand": {"$type": "color", "$value": "#112233"}}}))
    (tmp / "dtcg/a.css").write_text(".a { color: #112234; font-family: Georgia; }\n")
    msgs = [x["message"] for x in json.loads(run("--json", "a.css", cwd=tmp / "dtcg").stdout)]
    check(len(msgs) == 2 and "nearest color-brand = #112233" in msgs[0] and "nearest font-body = Inter" in msgs[1],
          "DTCG $value tokens give plain nearest names and $type/$description keys are not tokens")
    p = run("--tokens", tmp / "md/DESIGN.md", "--json", "a.css", cwd=tmp / "css")
    check(rows(p) == EXPECT, "--tokens FILE overrides the auto-found file")

    # missing and empty token file: stderr notice, exit 0, even with --strict
    (tmp / "none/.git").mkdir(parents=True)
    (tmp / "none/a.css").write_text(BAD_CSS)
    p = run("--strict", "a.css", cwd=tmp / "none")
    check(p.returncode == 0 and not p.stdout and "no tokens file" in p.stderr, "missing token file: notice on stderr, exit 0")
    (tmp / "none/tokens.css").write_text("/* nothing here */\n")
    p = run("--strict", "a.css", cwd=tmp / "none")
    check(p.returncode == 0 and not p.stdout and "no readable tokens" in p.stderr, "empty token file: notice on stderr, exit 0")

    # a class with no tokens stays silent
    (tmp / "none/tokens.css").write_text(":root { --color-brand: #112233; }\n")
    check(rows(run("--json", "a.css", cwd=tmp / "none")) == [(1, "off-token-color")], "rules with no tokens of their class are silent")

    # --base: only files changed since the merge-base are scanned
    g = tmp / "repo"
    g.mkdir()
    git = lambda *a: subprocess.run(["git", "-c", "user.name=Jane Smith", "-c", "user.email=jane@example.com", "-c", "commit.gpgsign=false", *a],
                                    cwd=g, capture_output=True, text=True, check=True)
    git("init", "-q", "-b", "main")
    (g / "tokens.css").write_text(CSS_TOKENS)
    (g / "old.css").write_text(BAD_CSS)
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "feat")
    (g / "new.css").write_text(".n { color: #fedcba; }\n")
    (g / "notes.txt").write_text("color: #fedcba\n")
    (g / "über ui.css").write_text(".o { color: #fedcba; }\n")  # git quotes this name without -z
    git("add", ".")
    git("commit", "-q", "-m", "feat")
    (g / "wip.css").write_text(".w { padding: 3px; }\n")  # untracked (not ignored) and tracked edits both count
    (g / "old.css").write_text(BAD_CSS + ".z { gap: 5px; }\n")
    p = run("--base", "main", "--json", cwd=g)
    got = sorted({Path(x["path"]).name for x in json.loads(p.stdout)})
    check(p.returncode == 0 and len(got) == 4 and got[:3] == ["new.css", "old.css", "wip.css"] and got[3].endswith(" ui.css"),
          f"--base scans changed UI files only (committed, tracked edits and untracked) {got}")
    git("rm", "-q", "-f", "new.css")
    check(run("--base", "main", cwd=g).returncode == 0, "--base skips files deleted since the base")
    check(run("--base", "no-such-ref", cwd=g).returncode == 1, "--base with a bad ref exits 1")

    # review fixes: hex only in colour props, // comments, explicit --tokens fails closed, 3/8-digit and mixed-case hex
    check(probe("sel", ":root { --color-brand: #112233; }\n", "li:hover #add { padding: 8px; }\n.a { color: #112234; }\n") == [(2, "off-token-color")]
          and probe("href", ":root { --color-brand: #112233; }\n", "const l = { href: '#add', color: '#112234' };\n", ".tsx") == [(1, "off-token-color")],
          "hex in a selector or href is not a colour; hex in a colour prop still is")
    check(probe("slash", SP, "// padding: 13px\nconst a = { padding: 13 }; // gap: 5px\nconst u = { padding: 'x', backgroundImage: 'http://x.test/a' };\n", ".tsx")
          == [(2, "off-token-space")], "// comments are blanked in .tsx (URL // is not a comment)")
    q = run("--tokens", tmp / "no-such-tokens.css", "a.css", cwd=tmp / "css")
    check(q.returncode == 1 and "not a file" in q.stderr and not q.stdout, "explicit --tokens FILE that is missing exits 1")
    check(probe("hex", ":root { --a: #ABC; --b: #11223344; --color-c: #AaBbCc; }\n",
                ".a { color: #aabbcc; }\n.b { color: #AABBCC; }\n.c { color: #abc; }\n.d { color: #112233; }\n.e { color: #11223344; }\n.f { color: #123456; }\n"
                ".g { color: #ABC; }\n") == [(6, "off-token-color")],
          "hex tokens match case-insensitively and across 3-, 6- and 8-digit forms (alpha ignored)")

    # review round 2: hex in filter/rule/mask/custom props/JSX bg+tint, quoted // is not a comment, selector FP, --base from a subdirectory
    T = ":root { --color-brand: #112233; }\n"
    for nm, src, ext in (("filter", ".a { filter: drop-shadow(0 1px 2px #abcdef); }\n", ".css"), ("colrule", ".a { column-rule: 1px solid #abcdef; }\n", ".css"),
                         ("mask", ".a { mask: linear-gradient(#abcdef, #112233); }\n", ".css"), ("custom", ":root { --x: #abcdef; }\n", ".css"),
                         ("bg", "const s = { bg: '#abcdef' };\n", ".tsx"), ("tint", "const s = { tint: '#abcdef' };\n", ".tsx")):
        check(probe(f"hex-{nm}", T, src, ext) == [(1, "off-token-color")], f"off-token hex in {nm} is flagged")
    check(probe("hex-ok", T, ".a { filter: drop-shadow(0 1px 2px #112233); }\n.b { --x: #112233; }\n", ".css") == [], "on-token hex in filter and custom props passes")
    check(probe("qslash", SP, "const s = { backgroundImage: '//cdn.test/a.png', padding: 13 };\n", ".tsx") == [(1, "off-token-space")],
          "protocol-relative URL in quotes is not a // comment: padding on the same line still flags")
    check(probe("apos", SP + T, "const a = <p>Don't</p>; // color: #abcdef; x='z'\nconst b = { padding: 13 };\n", ".tsx") == [(2, "off-token-space")]
          and probe("apos2", SP + T, "const a = <p>Note:'s</p>; // it's color: #abcdef\nconst b = { padding: 13 };\n", ".tsx") == [(2, "off-token-space")],
          "JSX text apostrophes (Don't, Note:'s) do not hide a trailing // comment")
    check(all(probe(f"q-{k}", SP, f"const s = {{ u: {e}, padding: 13 }};\n", ".tsx") == [(1, "off-token-space")]
              for k, e in (("tern", "c ? '//cdn.test/a.png' : x"), ("and", "a && '//cdn.test/a.png'"), ("plus", "base + '//cdn.test/a.png'"), ("tick", "`//cdn.test/a.png`"))),
          "quoted // after ?, &&, + or a backtick is not a comment: padding on the same line still flags")
    check(probe("selfp", T, ".border-x:focus #bad {\n  color: #112233;\n}\n.a:hover #bad2 { padding: 8px; }\n") == [],
          "selector `.border-x:focus #bad {` is not a declaration")
    sub = g / "sub"
    sub.mkdir()
    (sub / "deep.css").write_text(".d { color: #fedcba; }\n")
    p = run("--base", "main", "--json", cwd=sub)
    check(p.returncode == 0 and "deep.css" in p.stdout and "wip.css" in p.stdout, "--base from a subdirectory still scans untracked files (root-relative paths)")

    # arguments and defaults
    check(run(cwd=tmp).returncode == 1 and run("--nope", cwd=tmp).returncode == 1, "no input and unknown option exit 1")
    check(run("--tokens", cwd=tmp).returncode == 1 and run("--base", cwd=tmp).returncode == 1, "--tokens/--base without a value exit 1")
    check(run("missing.css", cwd=tmp).returncode == 1, "missing path exits 1")

    # find_tokens: default names unchanged, names argument finds DESIGN.md
    f = tmp / "md/a.css"
    check(lint_ui_slop.find_tokens(f) is None and lint_ui_slop.find_tokens(f, ("DESIGN.md",)) == tmp / "md/DESIGN.md",
          "find_tokens(names=...) finds DESIGN.md; the default still ignores it")

print(f"Tests: {sum(results)}/{len(results)}")
sys.exit(0 if all(results) else 1)
