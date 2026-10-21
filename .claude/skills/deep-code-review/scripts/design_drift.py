#!/usr/bin/env python3
"""design_drift.py — zero-token check that UI code still uses the project's design tokens.

WHY THIS EXISTS
---------------
A restyle or a new screen drifts from the design system one hard-coded value at a time: a hex that is almost
the brand colour, a 13px gap between a 12px and a 16px step, a fourth radius, a font that is not the brand
font. A script finds these for free and names the nearest token to use instead. It never calls a model or the
network. `lint_ui_slop.py` checks hex colours only; this adds spacing, radius and font family, and takes the
git changed set.

USAGE
-----
  design_drift.py [--strict] [--json] [--tokens FILE] [--base REF] [PATH...]

PATH is a file or a directory (walked like lint_ui_slop.py); only .html .htm .css .jsx .tsx are scanned.
`--base REF` adds the files changed since the merge-base of REF and HEAD (committed or not, plus untracked
files that are not ignored; deleted files excluded). Output is `path:line: rule: message`, with the nearest token named; `--json` prints a list of
{path, line, rule, message}. Exit 0 always for findings, 2 for findings only with `--strict`, 1 for an
error (bad arguments, unreadable path, git failure).

RULES
-----
  off-token-color   a hex in a colour-bearing property (color, background, border, fill, shadow...) that is not a token
                    colour (nearest by RGB); selectors/hrefs like `#add` are not read; // comments in .jsx/.tsx are blanked when at line start or after whitespace (not a quoted //cdn or http://)
  off-token-space   a margin/padding/gap length in px or rem that is not a spacing token (nearest by size)
  off-token-radius  a border-radius length in px or rem that is not a radius token (nearest by size)
  off-token-font    the first font-family entry is not a token family (generic keywords and var() pass)

TOKENS. `--tokens FILE`, else the nearest tokens.css, tokens.json, design-tokens.json or DESIGN.md walking
up from each scanned file (lint_ui_slop.find_tokens: stops at the nearest .git). A token is a name and a
value: a CSS custom property (`--space-2: 8px`), a JSON leaf (nested keys join with "-"; `value`/`$value`
objects unwrap) or a `name: value` / `| name | value |` line in DESIGN.md. A hex value is a colour token;
a px/rem value whose name has the word "radius" or "round(ed)" is a radius token, with the word "space",
"spacing", "gap", "pad", "padding" or "margin" (not letter-spacing or whitespace) a spacing token; a name with
"font" (not size, weight, line, style) and a text value is a font token, its first entry the primary family.
A rule is silent when its token class is empty. A missing auto-found or empty token file prints a notice on stderr
and exits 0; an explicit `--tokens FILE` that is missing exits 1.

Edge cases: comments are blanked; 0, auto, %, em, calc() values, radii of 999px or more (pills) and spacing of
2px or less (hairlines) are never flagged; em is relative to the element, so it is neither a token nor
checked. var() (fallback included) and url() are removed from a value before it is checked, so only the
literal rest of `padding: var(--space-2) 13px` is flagged. JSX numbers in margin/padding/gap/borderRadius
count as px (unitless lineHeight, flex etc. are not in those props, so not read); Tailwind classes and multi-line values are not read; DTCG `$`-keys other than `$value` are
skipped. The token file itself is never scanned. Side effects: none (read-only,
runs `git merge-base` and `git diff` only with --base).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from lint_ui_slop import EXTS, HEX, TOKEN_NAMES, blank, files, find_tokens, line_finder, norm, px

NAMES = TOKEN_NAMES + ("DESIGN.md",)
PAIR = re.compile(r"([\w-]+)[*`\"']*\s*[:=|]\s*[`\"']*([^;|\n]+)")
DECL = re.compile(r"([\w-]+)['\"]?\s*:\s*((?:[^;{}\n,]|,(?!\s*['\"]?[A-Za-z-]+['\"]?\s*:))+)")
LEN = re.compile(r"-?[\d.]+(?:px|rem)")  # em is relative to the element's font size, so it is not comparable
IGNORED = re.compile(r"var\((?:[^()]|\([^()]*\))*\)|url\([^)]*\)")
COLOR_PROP = re.compile(r"color|background|fill|stroke|border|outline|shadow|gradient|decoration|accent|caret|filter|rule|mask|bg|tint|^--")  # not selectors/hrefs
SPACE = re.compile(r"(margin|padding)(-(top|right|bottom|left|inline|block)(-(start|end))?)?|(row-|column-)?gap")
RADIUS = re.compile(r"border(-[a-z]+)*-radius")
GENERIC = {"inherit", "initial", "unset", "revert", "sans-serif", "serif", "monospace", "system-ui", "cursive",
           "fantasy", "-apple-system", "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded"}


def flatten(node, path=""):
    """(dotted-name, value) pairs for every string/number leaf of a JSON token tree; {value}/{$value} unwrap."""
    if isinstance(node, dict):
        inner = node.get("$value", node.get("value"))
        if isinstance(inner, (str, int, float)):
            yield path, str(inner)
        else:
            for k, v in node.items():
                if k.startswith("$"):  # DTCG metadata ($type, $description, $schema), not tokens
                    continue
                yield from flatten(v, f"{path}-{k}" if path else k)
    elif isinstance(node, (str, int, float)) and not isinstance(node, bool):
        yield path, str(node)


def read_tokens(tf):
    """{"color","space","radius","font"} -> [(name, value, key)] from a tokens file (see module docstring)."""
    text = tf.read_text(errors="replace")
    if tf.suffix == ".json":
        pairs = list(flatten(json.loads(text)))
    else:
        pairs = [(m.group(1), m.group(2)) for m in PAIR.finditer(blank(text))]
        if tf.suffix == ".css":
            pairs = [p for p in pairs if p[0].startswith("--")]
    t = {"color": [], "space": [], "radius": [], "font": []}
    for name, val in pairs:
        n, h, d = re.sub(r"([a-z])([A-Z])", r"\1-\2", name).lower(), HEX.search(val), LEN.search(val)  # spaceMd -> space-md
        if h:
            t["color"].append((name, "#" + h.group(1), norm(h.group(1))))
        elif d and re.search(r"(?<![a-z])(radius|rounded?)(?![a-z])", n):
            t["radius"].append((name, d.group(0), px(d.group(0).lstrip("-"))))
        elif d and re.search(r"(?<![a-z])(space|spacing|gap|pad|padding|margin)(?![a-z])", n) and not re.search(r"letter|white", n):
            t["space"].append((name, d.group(0), px(d.group(0).lstrip("-"))))
        elif "font" in n and not re.search(r"size|weight|line|style", n) and re.search(r"[a-z]", val) and not d:
            fam = re.sub(r"[`'\"*]", "", val).split(",")[0].strip()
            t["font"].append((name, fam, fam.lower()))
    return t


def rgb(h):
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def nearest(kind, key, toks):
    """' (nearest --space-2 = 8px)' for the token closest to key (RGB distance, size gap, or first font)."""
    if kind == "color":
        best = min(toks, key=lambda t: sum((a - b) ** 2 for a, b in zip(rgb(t[2]), rgb(key))))
    elif kind == "font":
        best = toks[0]
    else:
        best = min(toks, key=lambda t: abs(t[2] - key))
    return f"; nearest {best[0]} = {best[1]}"


def drift_text(text, ext, tokens):
    """Findings [(line, rule, message)] for one file's text against read_tokens() output."""
    text = blank(text)
    if ext in (".jsx", ".tsx"):  # // comment: at line start or after whitespace (not a quoted '//cdn' or the // of http://)
        # ponytail: not quote-aware, so a string holding " //" (`'x // y', padding: 13`) hides its line tail; add a tokenizer if that shows up
        text = re.sub(r"(?m)(?:^|(?<=\s))//[^\n]*", lambda m: " " * len(m.group(0)), text)
    line_of, out = line_finder(text), []
    for m in DECL.finditer(text):
        prop = re.sub(r"([a-z])([A-Z])", r"\1-\2", m.group(1)).lower()
        if text[m.end():].lstrip().startswith("{"):  # `.a:focus #bad {` is a selector, not a declaration
            continue
        val, line = re.sub(r"['\"`]|!\s*important", "", m.group(2)).strip(), line_of(m.start())
        lit = IGNORED.sub(" ", val)  # var() (fallback included) and url() never count; the literal rest does
        for h in HEX.finditer(lit) if tokens["color"] and COLOR_PROP.search(prop) else ():
            if norm(h.group(1)) not in {t[2] for t in tokens["color"]}:
                out.append((line, "off-token-color", f"#{h.group(1)} is not a token colour" + nearest("color", norm(h.group(1)), tokens["color"])))
        for kind, pat, rule in (("space", SPACE, "off-token-space"), ("radius", RADIUS, "off-token-radius")):
            if not tokens[kind] or not pat.fullmatch(prop):
                continue
            for piece in re.split(r"[\s/]+", lit):
                n = px(piece.lstrip("-")) if LEN.fullmatch(piece) else None
                if n is None and ext in (".jsx", ".tsx") and re.fullmatch(r"\d+(\.\d+)?", piece):
                    n = float(piece)
                if n and not (kind == "radius" and n >= 999) and not (kind == "space" and n <= 2) and all(abs(n - t[2]) > 1e-6 for t in tokens[kind]):
                    out.append((line, rule, f"{piece} is not a {kind} token" + nearest(kind, n, tokens[kind])))
        if prop == "font-family" and tokens["font"]:
            fam = val.split(",")[0].strip().lower()
            if fam and not fam.startswith("var(") and fam not in GENERIC and fam not in {t[2] for t in tokens["font"]}:
                out.append((line, "off-token-font", f"font family {fam} is not a token family" + nearest("font", fam, tokens["font"])))
    return out


def changed(base):
    """Absolute paths of files changed since the merge-base of base and HEAD, deleted files excluded."""
    git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout.strip()
    top = Path(git("rev-parse", "--show-toplevel"))
    out = subprocess.run(["git", "diff", "-z", "--name-only", "--diff-filter=d", git("merge-base", base, "HEAD")],
                         capture_output=True, text=True, check=True).stdout  # -z: no quoting of odd file names
    out += subprocess.run(["git", "-C", str(top), "ls-files", "-o", "--exclude-standard", "-z"], capture_output=True, text=True, check=True).stdout  # root-relative, like diff
    return [top / n for n in out.split("\0") if n and (top / n).suffix in EXTS and (top / n).is_file()]


def scan(paths, tokens_file=None):
    if tokens_file and not Path(tokens_file).is_file():  # an explicit file that is missing fails closed
        raise OSError(f"--tokens {tokens_file}: not a file")
    out, cache, notes = [], {}, set()
    for p in files(paths):
        tf = Path(tokens_file) if tokens_file else find_tokens(p.resolve(), NAMES)
        if tf is not None and tf.resolve() == p.resolve():
            continue
        if tf is None or not tf.is_file():
            notes.add(f"no tokens file ({', '.join(NAMES)}) found for {p}; nothing to compare")
            continue
        if tf not in cache:
            cache[tf] = read_tokens(tf)
            if not any(cache[tf].values()):
                notes.add(f"tokens file {tf} has no readable tokens; nothing to compare")
        for line, rule, msg in drift_text(p.read_text(errors="replace"), p.suffix, cache[tf]):
            out.append({"path": str(p), "line": line, "rule": rule, "message": msg})
    return sorted(out, key=lambda x: (x["path"], x["line"])), sorted(notes)


def main(argv):
    flags, tokens, base, paths, it = set(), None, None, [], iter(argv)
    for a in it:
        if a in ("--strict", "--json"):
            flags.add(a)
        elif a in ("--tokens", "--base"):
            v = next(it, None)
            if v is None:
                print(f"design_drift: {a} needs a value", file=sys.stderr)
                return 1
            tokens, base = (v, base) if a == "--tokens" else (tokens, v)
        elif a.startswith("-"):
            print(f"design_drift: unknown option {a}", file=sys.stderr)
            return 1
        else:
            paths.append(a)
    if not paths and base is None:
        print("usage: design_drift.py [--strict] [--json] [--tokens FILE] [--base REF] [PATH...]", file=sys.stderr)
        return 1
    try:
        found, notes = scan(paths + (changed(base) if base else []), tokens)
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f"design_drift: {e}", file=sys.stderr)
        return 1
    for n in notes:
        print(f"design_drift: {n}", file=sys.stderr)
    if "--json" in flags:
        print(json.dumps(found, indent=1))
    else:
        for x in found:
            print(f"{x['path']}:{x['line']}: {x['rule']}: {x['message']}")
    return 2 if found and "--strict" in flags else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
