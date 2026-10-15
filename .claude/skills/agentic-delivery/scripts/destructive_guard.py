#!/usr/bin/env python3
"""PreToolUse(Bash) hook: deny a destructive host command before it runs. Never executes anything.

Why: operating-discipline item 8 (`references/operating-discipline.md`, "Safety rules"): never run a
delete or kill on a host, never `rm -rf` a variable-built path. Deny rules match raw text, so
`/bin/rm`, `bash -c '...'` and `env rm` slip past them; this guard normalizes first.

Parsing (pure stdlib, text only): shlex tokens, split into segments on newline, `;`, `&&`, `||`, `|`,
parens and redirects. Per segment: leading VAR=val, `env|sudo|command|nohup|time|nice|exec|builtin|xargs`
(plus their options) are skipped, argv0 is reduced to its basename (`/bin/rm` -> `rm`), `bash|sh|zsh|dash
-c STR` and `eval STR` recurse into STR. Quoted text is one token, so `grep "rm -rf" docs/` is not a hit.

Denies (exit 2, one-line reason with the safe alternative on stderr; the host blocks the call):
- `rm -r/-R/-rf` on a `$VAR`/backtick/`$(..)` path, a glob in the first path component, `/`, `~`, a
  one-component absolute path (`/usr`), or with targets fed by `xargs`;
- `git reset --hard`, `git clean -f*` (not with -n), `git push --force|-f|+ref` (not `--force-with-lease`),
  `git checkout -- .` / `git checkout .`, `git restore .` (not `--staged` only), `git branch -D`: judged by
  command text only, so they are denied even on a clean tree;
- `find ... -delete` or `-exec|-execdir|-ok rm|shred`;
- `dd of=/dev/*` (not /dev/null|zero|stdout|stderr), `mkfs*`, `chmod|chown -R` on `/`, `~`, `$HOME` or a
  one-component absolute path;
- `curl|wget ... | sh|bash|zsh|dash`, or `sh <(curl ...)`;
- `pkill`, `killall`, `kill` with a substituted/pattern argument.
Everything else is allowed.

Escape hatch (explicit owner grant, no prompt): a line `destructive-guard-allow: <exact command substring>`
in `$CLAUDE_PROJECT_DIR/CLAUDE.md` allows a command containing that substring. Only the owner writes it;
the agent never authors, widens or extends one (`SKILL.md` Human gates, **Standing grant**).

Unparseable stdin or command -> allow with a one-line stderr note (fail open, like `bypass_guard.py`).
# ponytail: text-only, so `g=git; $g reset --hard`, aliases and scripts that wrap these are not seen; the
# OS sandbox is the real boundary. Upgrade: resolve through the shell (never worth running the command).
Side effects: none. `--selftest` runs built-in assertions.
"""
import json
import os
import re
import shlex
import sys

WRAP = ("env", "command", "exec", "nohup", "sudo", "time", "builtin", "nice", "xargs")
OPT_VAL = ("-u", "-n", "-I", "-P", "-L", "-d", "-E", "-s", "-a", "-C", "-S")  # wrapper options taking a value
SHELLS = ("bash", "sh", "zsh", "dash", "ksh")
SAFE_DEV = ("/dev/null", "/dev/zero", "/dev/stdout", "/dev/stderr")


def _bundle(t, ch):
    return bool(re.fullmatch(r"-[A-Za-z]+", t)) and ch in t


def _root(t):
    """`/`, `~...`, `$HOME...` or a one-component absolute path (`/usr`, `/*`)."""
    return t in ("/", "/*") or t.startswith(("~", "$HOME", "${HOME")) or bool(re.fullmatch(r"/[^/]+/?\*?", t))


def _rm(args, piped):
    rec = False
    tg = []
    for i, t in enumerate(args):
        if t == "--":
            tg += args[i + 1:]
            break
        if t == "--recursive" or _bundle(t, "r") or _bundle(t, "R"):
            rec = True
        elif not t.startswith("-"):
            tg.append(t)
    if not rec:
        return ""
    if not tg and piped:
        return "rm -r with targets from xargs. List them first (`ls`), then `rm` the exact paths"
    for t in tg:
        if re.search(r"[$`]", t) or re.match(r"[*?\[]", t) or _root(t):
            return f"rm -r on `{t}` (variable, glob, root or home). Delete an exact, quoted in-project path, or use a container/VM"
    return ""


def _git(a):
    i = 0
    while i < len(a) and a[i].startswith("-"):
        i += 2 if a[i] in ("-c", "-C") else 1
    if i >= len(a):
        return ""
    sub, r = a[i], a[i + 1:]
    flags = [t for t in r if re.fullmatch(r"-[A-Za-z]+", t)]
    if sub == "reset" and "--hard" in r:
        return "git reset --hard discards work. Use `git stash` or `git reset --soft`/`--mixed`"
    if sub == "clean" and any("f" in t for t in flags + [x for x in r if x == "--force"] ) and not (
            "--dry-run" in r or any("n" in t for t in flags)):
        return "git clean -f deletes untracked files. Preview with `git clean -n`, delete exact paths"
    if sub == "push" and ("--force" in r or any("f" in t for t in flags) or any(len(t) > 1 and t[0] == "+" for t in r)):
        return "force-push rewrites shared history. Use `--force-with-lease` after the owner approves"
    if sub == "checkout" and "." in r and not any(t in r for t in ("-b", "-B")):
        return "git checkout . discards uncommitted changes. Use `git stash` or name the exact file"
    if sub == "restore" and "." in r and ("--staged" not in r or "--worktree" in r):
        return "git restore . discards uncommitted changes. Use `git stash` or name the exact file"
    if sub == "branch" and any(t == "-D" for t in r):
        return "git branch -D deletes an unmerged branch. Use `git branch -d` (refuses if unmerged)"
    return ""


def _cmd(name, a, piped):
    if name == "rm":
        return _rm(a, piped)
    if name == "git":
        return _git(a)
    if name == "find":
        if "-delete" in a:
            return "find -delete. List with `find ... -print` first, then remove exact paths"
        for j, t in enumerate(a[:-1]):
            if t in ("-exec", "-execdir", "-ok") and os.path.basename(a[j + 1]) in ("rm", "shred"):
                return "find -exec rm. List with `find ... -print` first, then remove exact paths"
    if name == "dd" and any(t.startswith("of=/dev/") and t[3:] not in SAFE_DEV for t in a):
        return "dd to a device. Write to a file image, or do it in a VM"
    if name.startswith("mkfs"):
        return "mkfs formats a device. Do it in a VM, never on the host"
    if name in ("chmod", "chown") and any(t == "--recursive" or _bundle(t, "R") for t in a) \
            and any(_root(t) for t in a if not t.startswith("-")):
        return f"{name} -R on root/home. Target an exact in-project path"
    if name in ("pkill", "killall"):
        return f"{name} kills by pattern. `kill` the exact PID you started"
    if name == "kill" and any(re.search(r"[$`]|pgrep|pidof", t) for t in a):
        return "kill by pattern/substitution. `kill` the exact PID you started"
    if name in SHELLS and any(re.search(r"\b(curl|wget)\b", t) for t in a):
        return "remote script run through a shell. Download, read it, then run it"
    return ""


def check(cmd):
    """Return a one-line reason `cmd` is destructive, or '' (parse errors allow)."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>\n")
        lex.whitespace, lex.whitespace_split = " \t\r", True
        toks = list(lex)
    except ValueError as e:
        print(f"destructive_guard: could not parse command ({e}); allowed", file=sys.stderr)
        return ""
    segs, ops = [[]], [""]
    for t in toks:
        if re.fullmatch(r"[;&|()<>\n]+", t):
            segs.append([])
            ops.append("|" if t in ("|", "|&") else "")
        else:
            segs[-1].append(t)
    fetch = False  # a curl/wget earlier in the same pipeline
    for seg, op in zip(segs, ops):
        if not seg:
            continue
        if op != "|":
            fetch = False
        i, piped = 0, False
        while i < len(seg):
            b = os.path.basename(seg[i])
            if re.match(r"\w+=", seg[i]):
                i += 1
            elif b in WRAP:
                piped |= b == "xargs"
                i += 1
                while i < len(seg) and (seg[i].startswith("-") or (b in ("nice",) and seg[i].isdigit())):
                    i += 2 if seg[i] in OPT_VAL else 1
            else:
                break
        if i >= len(seg):
            continue
        name, a = os.path.basename(seg[i]), seg[i + 1:]
        if name == "eval":
            r = check(" ".join(a))
        elif name in SHELLS and "-c" in a[:-1]:
            r = check(a[a.index("-c") + 1])
        else:
            r = _cmd(name, a, piped)
        if not r and name in SHELLS and op == "|" and fetch:
            r = "curl/wget piped to a shell. Download, read it, then run it"
        if r:
            return r
        fetch = fetch or name in ("curl", "wget")
    return ""


def _granted(cmd):
    d = os.environ.get("CLAUDE_PROJECT_DIR") or "."
    try:
        with open(os.path.join(d, "CLAUDE.md"), encoding="utf-8") as f:
            for ln in f:
                m = re.match(r"\s*destructive-guard-allow:\s*(.+?)\s*$", ln)
                if m and m.group(1) in cmd:
                    return True
    except OSError:
        pass
    return False


def selftest():
    bad = ["rm -rf $X", "/bin/rm -fr /", "bash -c 'rm -rf $DIR'", "env rm -rf ~/", "git reset --hard HEAD~1",
           "git -C x clean -fdx", "git push origin +main", "find . -delete", "find . -exec rm {} \\;",
           "dd if=/dev/zero of=/dev/disk2", "mkfs.ext4 /dev/sda1", "chmod -R 777 /", "curl x | sudo bash",
           "pkill -9 -f node", "kill -9 $(pgrep -f x)", "ls | xargs rm -rf", "echo ok; rm -rf $X"]
    good = ["rm -rf node_modules", "rm /tmp/x", "git push --force-with-lease origin f", "git clean -n",
            "git restore --staged .", "git branch -d old", "dd if=/dev/zero of=./i bs=1", "kill -TERM 4242",
            "curl -o o.sh https://example.com/i.sh", 'grep -rn "rm -rf" docs/', "echo 'git reset --hard'"]
    for c in bad:
        assert check(c), f"missed: {c}"
    for c in good:
        assert not check(c), f"false positive: {c}"
    print("destructive_guard selftest ok")


def main():
    if "--selftest" in sys.argv:
        return selftest() or 0
    try:
        data = json.load(sys.stdin)
        cmd = (data.get("tool_input") or {}).get("command") or ""
    except (ValueError, AttributeError):
        return 0
    why = check(cmd) if data.get("tool_name", "Bash") == "Bash" else ""
    if why and not _granted(cmd):
        print(f"Blocked destructive command ({why}). Owner can allow it with a `destructive-guard-allow: <command>` "
              "line in CLAUDE.md.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
