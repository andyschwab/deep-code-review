#!/usr/bin/env python3
"""PreToolUse(Bash) hook: deny a destructive host command before it runs. Never executes the command.

BEST-EFFORT defense in depth, not a boundary. The OS sandbox (`sandbox.enabled`, set by
`install.sh --apply-operating-layer`) is the boundary: operating-discipline item 8
(`references/operating-discipline.md`, "Safety rules": never run a delete or kill on a host, never `rm -rf`
a variable-built path). Text matching cannot see variables holding a command, aliases, scripts, `g=git; $g ...`
or interpreter code built at run time; this guard catches the honest and the common-wrapper mistakes only.

Parsing (pure stdlib, text only): backslash-newline joined, heredoc bodies and here-strings set aside, shlex
tokens, split into segments on newline, `;`, `&&`, `||`, `|`, parens. Redirections (`>f`, `2>/dev/null`, `<x`)
do not split a command and are skipped when finding argv0. Per segment: leading VAR=val, shell keywords
(`{ } if then else elif fi while until do done !`) and wrappers (`env sudo doas command nohup time nice timeout
setsid stdbuf ionice chronic caffeinate flock exec builtin busybox xargs`) are skipped, consuming option values
only for the flags that really take one (`sudo -u/-g/-C/-D/-h/-p/-r/-t/-U`, `env -u/-C/-S`, ...); `env -S STR`,
`flock -c STR`, `eval STR`, `su -c STR` and `bash|sh|zsh|dash|ash|ksh|fish` with a flag bundle containing `c`
(`-c`, `-lc`) recurse into STR. argv0 becomes its basename (`/bin/rm` -> `rm`). Every `$(...)` and backtick
body is scanned recursively. Quoted text is one token, so `grep "rm -rf" docs/` is not a hit. Text fed to a
shell or interpreter (`echo|printf ... | sh`, `<<<`, heredoc) is scanned as a command or interpreter body.

Denies (exit 2, one-line reason with the safe alternative on stderr; the host blocks the call):
- `rm -r` (also `--rec*`) on a `$VAR`/backtick path, any glob or brace list/range, `.`, `..`, `/`, `//`, `~`,
  `$HOME`, an absolute path within 2 components of `/` after normalizing `..`, or (under `xargs`) a `{}`/`%`
  placeholder or no explicit target;
- `git reset --hard`, `git clean -f*` (not with -n), `git push` force/delete/mirror/`+ref`/`:ref`/glob refspec
  (not `--force-with-lease`), `git checkout|switch -f|--discard-changes`, `git checkout|restore` of the whole
  tree (`.`, `./`, `*`, `:/`, `:(top)`; not `restore --staged` only), `git branch -D`, `git stash clear|drop`:
  judged by command text only, so denied even on a clean tree; global options with values and unique-prefix
  long options (`--ha`, `--mir`, `--forc`) are normalized first;
- `find ... -delete`, `-exec|-execdir|-ok rm|shred`, or an exec'd command (`sh -c ...`) that is itself denied;
- `dd of=/dev/*` (not null|zero|stdout|stderr), `mkfs*`, `chmod|chown -R` on root/home/near-root paths;
- `curl|wget ... | sh|bash|...|python|perl|ruby|node|php`, `sh|bash|source|. <(curl ...)`, `eval` or a shell
  fed by curl/wget;
- `pkill`, `killall`, `kill` with a substituted/pattern argument;
- `python -c`, `perl -e`, `node -e`, `awk` bodies that delete (`rmtree`, `os.remove`, `unlink`, `rm_rf`, ...)
  anything but a literal relative path, contain `rm -r` on a variable/root, or call `system()` on a
  non-literal command.
Everything else is allowed.

Escape hatch (explicit owner grant, no prompt): a line `destructive-guard-allow: <full command>` in the
committed `CLAUDE.md` (HEAD of the project repo, `$CLAUDE_PROJECT_DIR`). It counts only when the commit that
introduced that line (`git blame`) is authored by an email in DCR_OWNER_EMAIL, has no Co-authored-by trailer
and carries a GOOD signature (`%G?` == G; `git commit -S`). `git config dcr.owner` is NOT an owner source here
(any local process can edit it). No signature, no owner env, an uncommitted line or any git error means no
grant. The command must equal the line after whitespace normalization, EXACTLY, not as a substring. The agent
never authors a grant (`SKILL.md` Human gates, **Standing grant**).

Never crashes. Unparseable stdin, a non-string command, a shlex failure or any internal error falls back to
a regex scan of the raw text for the same destructive classes: block on a hit, otherwise allow (a guard that
errors closed would wedge every session; one that errors open on a hit would be trivial to evade).
Side effects: none beyond read-only `git show|blame` for the grant. `--selftest` runs assertions.
"""
import importlib.util
import json
import os
import posixpath
import re
import shlex
import sys

KW = ("{", "}", "if", "then", "else", "elif", "fi", "while", "until", "do", "done", "!", "coproc")
# wrapper -> short flags that take a value (only these consume the next token)
VAL = {"env": "uCS", "sudo": "ugCDhprtU", "doas": "uC", "nice": "n", "timeout": "sk", "xargs": "adEILnPsI",
       "stdbuf": "ioe", "ionice": "cnpPu", "time": "fo", "exec": "a", "caffeinate": "tw", "flock": "wEc",
       "command": "", "builtin": "", "nohup": "", "setsid": "", "chronic": "", "busybox": ""}
LONGVAL = ("--user", "--group", "--chdir", "--host", "--prompt", "--role", "--type", "--other-user", "--unset",
           "--split-string", "--signal", "--kill-after", "--arg-file", "--delimiter", "--max-args",
           "--max-procs", "--max-lines", "--max-chars")
SHELLS = ("bash", "sh", "zsh", "dash", "ash", "ksh", "fish")
AWK = ("awk", "gawk", "mawk", "nawk")
INTERP = re.compile(r"^(python[\d.]*|perl|ruby|node|nodejs|bun|deno|php|lua)$")
EVALFLAG = re.compile(r"-[A-Za-z]*[ceErp][A-Za-z]*")
SAFE_DEV = ("/dev/null", "/dev/zero", "/dev/stdout", "/dev/stderr")
GIT_OPT_VAL = ("-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env")
LIT = r"""['"][^'"/$@][^'"$@]*['"]"""  # a literal relative path
DELAPI = re.compile(r"(rmtree|os\.(?:remove|unlink|rmdir|removedirs)|rmSync|rmdirSync|unlinkSync|\bfs\.rm|rm_rf"
                    r"|File\.delete|\bunlink|\brmdir)(?:\(|\s)(?!\s*" + LIT + r"\s*(?:[,);]|$))")
BODYRM = re.compile(r"\brm\s+-\w*[rR]\w*\s+\S*[$/~*]")
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_]\w*)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
MAXDEPTH = 6
FALLBACK = [re.compile(p) for p in (
    r"\brm\s+(?:-\S+\s+)*-\w*[rR]\w*\s+(?:\S*[$`*~{]|/|\.\.?(?:\s|$))",
    r"\bgit\b.*\b(?:reset\s+--ha|clean\s+-\w*f|checkout\s+(?:-f|--\s+\.|\.)|switch\s+-f|restore\s+\.|branch\s+-D|stash\s+(?:clear|drop))",
    r"\bgit\b.*\bpush\b.*(?:--for|\s-\w*f\w*\b|--del|--mir|\s[+:]\S)",
    r"\bfind\b.*(?:-delete|-exec\s+rm)", r"\bdd\b.*\bof=/dev/(?!null|zero|std)", r"\bmkfs",
    r"\b(?:chmod|chown)\s+(?:-\S+\s+)*-\w*R\w*\s+(?:\S+\s+)?[/~]", r"\b(?:pkill|killall)\b",
    r"\bkill\s+.*[$`]", r"\b(?:curl|wget)\b.*\|\s*(?:sudo\s+)?(?:ba|z|da|k|fi)?sh\b",
)]


def _bundle(t, ch):
    return bool(re.fullmatch(r"-[A-Za-z]+", t)) and ch in t


def _far(t):
    """Root, home, `..` escapes or an absolute path within 2 components of `/`, after normalizing."""
    if t.startswith(("~", "$HOME", "${HOME")):
        return True
    if "$" in t or "`" in t:
        return False
    p = posixpath.normpath(re.sub("/+", "/", t)) if t else ""
    return p in ("/", "..") or p.startswith("../..") or (p.startswith("/") and p.count("/") <= 2)


def _tree(t):
    """A git pathspec naming the whole work tree (or its parent)."""
    if t in ("*", ":/", ":(top)", ":(top)*"):
        return True
    return not t.startswith(":") and "$" not in t and bool(t) and posixpath.normpath(re.sub("/+", "/", t)) in (".", "..")


def _rm(args, ph):
    rec, tg = False, []
    for i, t in enumerate(args):
        if t == "--":
            tg += args[i + 1:]
            break
        if (t.startswith("--") and len(t) >= 5 and "--recursive".startswith(t.split("=")[0])) \
                or _bundle(t, "r") or _bundle(t, "R"):
            rec = True
        elif not t.startswith("-"):
            tg.append(t)
    if not rec:
        return ""
    if not tg and ph:
        return "rm -r with targets from xargs. List them first (`ls`), then `rm` the exact paths"
    for t in tg:
        n = posixpath.normpath(re.sub("/+", "/", t) or ".")
        if re.search(r"[$`*?\[]|\{[^}]*(?:,|\.\.)", t) or (ph and any(p in t for p in ph if p)) or n == "." or _far(t):
            return f"rm -r on `{t}` (variable, glob, placeholder, `.`, root, home or near-root). Delete an exact, quoted in-project path, or use a container/VM"
    return ""


def _git(a):
    i = 0
    while i < len(a) and a[i].startswith("-"):
        i += 2 if a[i] in GIT_OPT_VAL else 1
    if i >= len(a):
        return ""
    sub, r = a[i], a[i + 1:]
    longs = [t.split("=")[0] for t in r if t.startswith("--") and len(t) > 2]

    def has(full):  # unique-prefix long option (>= 4 chars, e.g. --ha, --mir, --forc)
        return any(len(x) >= 4 and full.startswith(x) for x in longs)
    flags = [t for t in r if re.fullmatch(r"-[A-Za-z]+", t)]
    force = has("--force") or any("f" in t for t in flags)
    dele = has("--delete") or any("d" in t for t in flags)
    if sub == "reset" and has("--hard"):
        return "git reset --hard discards work. Use `git stash` or `git reset --soft`/`--mixed`"
    if sub == "clean" and force and not (has("--dry-run") or any("n" in t for t in flags)):
        return "git clean -f deletes untracked files. Preview with `git clean -n`, delete exact paths"
    if sub == "push" and (force or dele or has("--mirror") or any(
            not t.startswith("-") and (t.startswith(("+", ":")) or ":+" in t or "*" in t) for t in r)):
        return "force/delete/mirror push rewrites shared history. Use `--force-with-lease` after the owner approves"
    if sub in ("checkout", "switch") and (force or has("--discard-changes")):
        return "git checkout/switch -f discards uncommitted changes. Use `git stash` or name the exact file"
    if sub in ("checkout", "restore") and any(_tree(t) for t in r if not t.startswith("-")) \
            and not (sub == "restore" and has("--staged") and not has("--worktree")):
        return "whole-tree git checkout/restore discards uncommitted changes. Use `git stash` or name the exact file"
    if sub == "branch" and (any(_bundle(t, "D") for t in r) or (force and dele)):
        return "git branch -D deletes an unmerged branch. Use `git branch -d` (refuses if unmerged)"
    if sub == "stash" and any(t in ("clear", "drop") for t in r):
        return "git stash clear/drop loses stashed work. Use `git stash list`/`apply` and keep it"
    return ""


def _body(t):
    """Interpreter/awk one-liner or fed text: deletes a non-literal path, or system() on a non-literal command."""
    if DELAPI.search(t) or BODYRM.search(t):
        return "interpreter one-liner deleting a variable/root path. Delete an exact literal in-project path"
    calls = re.findall(r"\bsystem\s*\(", t)
    lits = re.findall(r"""\bsystem\s*\(\s*(?:"([^"]*)"|'([^']*)')\s*\)""", t)
    if len(calls) > len(lits):
        return "system() on a non-literal command. Run an exact literal command"
    for d, s in lits:
        r = check(d or s, 1)
        if r:
            return r
    return ""


def _cmd(name, a, ph):
    if name == "rm":
        return _rm(a, ph)
    if name == "git":
        return _git(a)
    if name == "find":
        if "-delete" in a:
            return "find -delete. List with `find ... -print` first, then remove exact paths"
        for j, t in enumerate(a[:-1]):
            if t in ("-exec", "-execdir", "-ok"):
                k = next((m for m in range(j + 1, len(a)) if a[m] in (";", "+")), len(a))
                sub = a[j + 1:k]
                if sub and os.path.basename(sub[0]) in ("rm", "shred"):
                    return "find -exec rm. List with `find ... -print` first, then remove exact paths"
                r = check(" ".join(shlex.quote(x) for x in sub), 1)
                if r:
                    return r
    if name == "dd" and any(t.startswith("of=/dev/") and t[3:] not in SAFE_DEV for t in a):
        return "dd to a device. Write to a file image, or do it in a VM"
    if name.startswith("mkfs"):
        return "mkfs formats a device. Do it in a VM, never on the host"
    if name in ("chmod", "chown") and any(t == "--recursive" or _bundle(t, "R") for t in a) \
            and any(_far(t) for t in a if not t.startswith("-")):
        return f"{name} -R on root/home. Target an exact in-project path"
    if name in ("pkill", "killall"):
        return f"{name} kills by pattern. `kill` the exact PID you started"
    if name == "kill" and any(re.search(r"[$`]|pgrep|pidof", t) for t in a):
        return "kill by pattern/substitution. `kill` the exact PID you started"
    if name in SHELLS + ("eval",) and any(re.search(r"\b(curl|wget)\b", t) for t in a):
        return "remote script run through a shell. Download, read it, then run it"
    if INTERP.match(name):
        for j, t in enumerate(a[:-1]):
            if (EVALFLAG.fullmatch(t) or t in ("--eval", "--print")) and _body(a[j + 1]):
                return _body(a[j + 1])
    if name in AWK:
        for t in a:
            if _body(t):
                return _body(t)
    return ""


def _unwrap(seg):
    """(index of argv0, xargs placeholders or None, nested command string or None) for one segment."""
    i, ph, nested = 0, None, None
    while i < len(seg):
        b = os.path.basename(seg[i])
        if re.match(r"\w+=", seg[i]) or b in KW:
            i += 1
        elif b in VAL:
            vals = VAL[b]
            if b == "xargs":
                ph = ["{}", "%"]
            i += 1
            while i < len(seg) and seg[i].startswith("-"):
                t = seg[i]
                i += 1
                if t == "--":
                    break
                if t.startswith("--"):
                    if b == "env" and t.startswith("--split-string="):
                        nested = t.split("=", 1)[1]
                    elif "=" not in t and t in LONGVAL:
                        if b == "env" and t == "--split-string" and i < len(seg):
                            nested = seg[i]
                        i += 1
                    continue
                for k, ch in enumerate(t[1:], 1):
                    if ch in vals:
                        val = t[k + 1:] or (seg[i] if i < len(seg) else "")
                        i += 0 if t[k + 1:] else 1
                        if (b == "env" and ch == "S") or (b == "flock" and ch == "c"):
                            nested = val
                        if b == "xargs" and ch == "I":
                            ph.append(val)
                        break
            if b in ("timeout", "flock") and i < len(seg):
                i += 1  # the duration / lock file
                if b == "flock" and seg[i:i + 1] == ["-c"]:
                    nested, i = seg[i + 1] if i + 1 < len(seg) else "", i + 2
        else:
            break
    return i, ph, nested


def _head(prefix):
    """argv0 of the last command in `prefix` (text before a heredoc marker)."""
    try:
        toks = shlex.split(re.split(r"[;&|\n(]", prefix)[-1])
    except ValueError:
        return ""
    i = _unwrap(toks)[0]
    return os.path.basename(toks[i]) if i < len(toks) else ""


def _feed(name, text):
    """Reason when `text` is fed to shell/interpreter `name` and is destructive."""
    if name in SHELLS:
        return check(text, 1)
    if INTERP.match(name) or name in AWK:
        return _body(text)
    return ""


def _bodies(cmd):
    """Backtick and `$(...)` bodies of the raw text (balanced parens), scanned recursively by the caller."""
    out = re.findall(r"`([^`]*)`", cmd)
    for m in re.finditer(r"\$\(", cmd):
        depth, j = 1, m.end()
        while j < len(cmd) and depth:
            depth += (cmd[j] == "(") - (cmd[j] == ")")
            j += 1
        out.append(cmd[m.end():j - 1 if depth == 0 else j])
    return out


def _fallback(cmd):
    """Regex scan of raw text for the destructive classes; used when parsing fails."""
    cmd = cmd.replace("\\\n", "")
    return "destructive pattern in unparseable command (regex fallback)" if any(p.search(cmd) for p in FALLBACK) else ""


def check(cmd, _depth=0):
    """Return a one-line reason `cmd` is destructive, or '' (parse errors use the regex fallback)."""
    cmd = cmd.replace("\\\n", "")
    if _depth > MAXDEPTH:
        return _fallback(cmd)
    for m in HEREDOC.finditer(cmd):  # a heredoc into a shell/interpreter is code; any other body is data
        r = _feed(_head(cmd[cmd.rfind("\n", 0, m.start()) + 1:m.start()]), m.group(3))
        if r:
            return r
    cmd = HEREDOC.sub(lambda m: m.group(0).split("\n", 1)[0], cmd)
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()<>\n")
        lex.whitespace, lex.whitespace_split = " \t\r", True
        toks = list(lex)
    except ValueError:
        return _fallback(cmd)
    for b in _bodies(cmd):
        r = check(b, _depth + 1)
        if r:
            return r
    segs, ops, hs, skip = [[]], [""], [None], None
    for t in toks:
        if re.fullmatch(r"[;&|()<>\n]+", t):
            if re.search(r"[;|()\n]", t) or not re.search(r"[<>]", t):
                segs.append([])
                hs.append(None)
                ops.append("|" if t in ("|", "|&") else "<(" if "<(" in t else "")
                skip = None
            else:  # redirection: the next token is its target; the command continues
                if segs[-1] and segs[-1][-1].isdigit():
                    segs[-1].pop()
                skip = "hs" if t.endswith("<<<") else "t"
        elif skip:
            if skip == "hs":
                hs[-1] = t
            skip = None
        else:
            segs[-1].append(t)
    fetch, prev, feed = False, "", None  # fetch: curl/wget earlier in the pipeline; feed: echo/printf text
    for seg, op, here in zip(segs, ops, hs):
        if not seg:
            continue
        if op != "|":
            fetch, feed = False, None
        i, ph, nested = _unwrap(seg)
        if nested:
            r = check(nested, _depth + 1)
            if r:
                return r
        if i >= len(seg):
            continue
        name, a = os.path.basename(seg[i]), seg[i + 1:]
        r = _cmd(name, a, ph)
        if not r and name == "eval":
            r = check(" ".join(a), _depth + 1)
        if not r and name in SHELLS + ("su",):
            for j, t in enumerate(a[:-1]):
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", t):
                    r = check(a[j + 1], _depth + 1)
                    break
        if not r and here is not None:
            r = _feed(name, here)
        if not r and op == "|" and feed:
            r = next((x for x in (_feed(name, f) for f in feed) if x), "")
        if not r and op == "|" and fetch and (name in SHELLS or INTERP.match(name)):
            r = "curl/wget piped to a shell/interpreter. Download, read it, then run it"
        if not r and op == "<(" and name in ("curl", "wget") and prev in SHELLS + ("source", "."):
            r = "remote script sourced through process substitution. Download, read it, then run it"
        if r:
            return r
        fetch = fetch or name in ("curl", "wget")
        feed = ([" ".join(a)] + a) if name in ("echo", "printf") else None  # joined, and each arg (printf FORMAT ARG)
        prev = name
    return ""


def _granted(cmd):
    """True when a signed, owner-authored, committed `destructive-guard-allow:` line equals `cmd` (whitespace-normalized)."""
    try:
        owners = [e.strip().strip("<>").casefold() for e in re.split(r"[,\s]+", os.environ.get("DCR_OWNER_EMAIL", "")) if e.strip()]
        if not owners:
            return False
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location("focus_gate", os.path.join(here, "focus_gate.py"))
        fg = importlib.util.module_from_spec(spec)
        sys.modules["focus_gate"] = fg  # its dataclasses need the module registered
        spec.loader.exec_module(fg)
        git = fg.real_git(os.environ.get("CLAUDE_PROJECT_DIR") or ".")
        want = " ".join(cmd.split())
        for n, ln in enumerate(git(["show", "HEAD:CLAUDE.md"]).splitlines(), 1):
            m = re.match(r"\s*destructive-guard-allow:\s*(.+?)\s*$", ln)
            if m and " ".join(m.group(1).split()) == want:
                sha = git(["blame", "--porcelain", "-L", f"{n},{n}", "HEAD", "--", "CLAUDE.md"]).split()[0]
                if fg._owner_problem(git, sha, owners, True) == "":  # owner email, no Co-authored-by, %G? == G
                    return True
    except Exception:
        pass
    return False


def selftest():
    bad = ["rm -rf $X", "/bin/rm -fr /", "bash -c 'rm -rf $DIR'", "env rm -rf ~/", "git reset --hard HEAD~1",
           "git -C x clean -fdx", "git push origin +main", "find . -delete", "find . -exec rm {} \\;",
           "dd if=/dev/zero of=/dev/disk2", "mkfs.ext4 /dev/sda1", "chmod -R 777 /", "curl x | sudo bash",
           "pkill -9 -f node", "kill -9 $(pgrep -f x)", "ls | xargs rm -rf", "echo ok; rm -rf $X",
           "{ rm -rf $X; }", "bash -lc 'rm -rf $X'", "timeout 5 rm -rf $X", "echo $(rm -rf $X)", "bash <(curl x)",
           "echo \"rm -rf $X", "sudo -n rm -rf $X", ">o rm -rf $X", "echo 'rm -rf $X' | sh", "git reset --ha"]
    good = ["rm -rf node_modules", "rm -rf ./build", "rm /tmp/x", "git push --force-with-lease origin f", "git clean -n",
            "git restore --staged .", "git branch -d old", "dd if=/dev/zero of=./i bs=1", "kill -TERM 4242",
            "curl -o o.sh https://example.com/i.sh", 'grep -rn "rm -rf" docs/', "echo 'git reset --hard'",
            "find . -name x", "sudo -n ls"]
    for c in bad:
        assert check(c), f"missed: {c}"
    for c in good:
        assert not check(c), f"false positive: {c}"
    print("destructive_guard selftest ok")


def main():
    if "--selftest" in sys.argv:
        return selftest() or 0
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        cmd = (data.get("tool_input") or {}).get("command")
        if data.get("tool_name", "Bash") != "Bash":
            return 0
        if not isinstance(cmd, str):
            cmd = " ".join(map(str, cmd)) if isinstance(cmd, (list, tuple)) else None if cmd is None else json.dumps(cmd)
    except Exception:
        cmd = raw  # not JSON / wrong shape: scan the raw text
    if not cmd:
        return 0
    try:
        why = check(cmd)
    except Exception:
        why = _fallback(cmd)
    if why and not _granted(cmd):
        print(f"Blocked destructive command ({why}). Best-effort guard; the OS sandbox is the boundary. To allow it, the "
              "owner commits a signed (`git commit -S`) `destructive-guard-allow: <exact command>` line to CLAUDE.md "
              "with an author email listed in DCR_OWNER_EMAIL.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
