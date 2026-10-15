#!/usr/bin/env python3
"""PreToolUse(Bash) hook: deny a destructive host command before it runs. Never executes the command.

Why: operating-discipline item 8 (`references/operating-discipline.md`, "Safety rules"): never run a
delete or kill on a host, never `rm -rf` a variable-built path. Deny rules match raw text, so
`/bin/rm`, `bash -c '...'` and `env rm` slip past them; this guard normalizes first.

Parsing (pure stdlib, text only): shlex tokens, split into segments on newline, `;`, `&&`, `||`, `|`,
parens, braces and redirects. Per segment: leading VAR=val, shell keywords (`{ } if then else elif fi while
until do done !`) and wrappers (`env sudo doas command nohup time nice timeout setsid stdbuf ionice chronic
exec builtin xargs`, with their options and the `timeout` duration) are skipped, argv0 becomes its basename
(`/bin/rm` -> `rm`), `eval STR` and `bash|sh|zsh|dash|ksh` with any flag bundle containing `c` (`-c`, `-lc`,
`-ec`) recurse into STR. Every `$(...)` and backtick body in the raw text is scanned recursively too.
Quoted text is one token, so `grep "rm -rf" docs/` is not a hit.

Denies (exit 2, one-line reason with the safe alternative on stderr; the host blocks the call):
- `rm -r` on a `$VAR`/backtick path, any glob, `.`, `..`, `../..`, `/`, `//`, `~`, `$HOME`, an absolute path
  within 2 components of `/` (`/usr`, `/Users/x`, `/home/x`), or with targets fed by `xargs`;
- `git reset --hard`, `git clean -f*` (not with -n), `git push --force|-f|--delete|-d|--mirror|+ref|:ref`
  (not `--force-with-lease`), `git checkout -f|.`, `git restore .` (not `--staged` only), `git branch -D`
  (or `-d` with `-f`), `git stash clear|drop`: judged by command text only, so denied even on a clean
  tree; git global options with values (`-c -C --git-dir --work-tree --namespace`) are skipped first;
- `find ... -delete` or `-exec|-execdir|-ok rm|shred`;
- `dd of=/dev/*` (not null|zero|stdout|stderr), `mkfs*`, `chmod|chown -R` on root/home/near-root paths;
- `curl|wget ... | sh|bash|zsh|dash|python|perl|ruby|node|php|...`, `sh|bash|source|. <(curl ...)`, `eval`
  or a shell fed by curl/wget;
- `pkill`, `killall`, `kill` with a substituted/pattern argument;
- `python -c`, `perl -e`, `node -e` ... bodies that delete (`rmtree`, `os.remove`, `unlink`, `rm_rf`, ...)
  anything but a literal relative path, or contain `rm -r` on a variable/root.
Everything else is allowed.

Escape hatch (explicit owner grant, no prompt): a line `destructive-guard-allow: <full command>` in the
committed `CLAUDE.md` (HEAD of the project repo, `$CLAUDE_PROJECT_DIR`). It counts only when `git blame`
shows that line was committed by an owner email with no Co-authored-by trailer (focus_gate.py's
`resolve_owners` + `_owner_problem`; owner set from DCR_OWNER_EMAIL or `git config dcr.owner`, which any
local process can edit, so set the env from protected configuration). An uncommitted line, a missing owner
set or any git error means no grant. The command must equal the line after whitespace normalization, EXACTLY,
not as a substring. The agent never authors a grant (`SKILL.md` Human gates, **Standing grant**).

Never crashes. Unparseable stdin, a non-string command, a shlex failure or any internal error falls back to
a regex scan of the raw text for the same destructive classes: block on a hit, otherwise allow (a guard that
errors closed would wedge every session; one that errors open on a hit would be trivial to evade).
# ponytail: text-only, so `g=git; $g reset --hard`, aliases, scripts and variables holding a command are not
# seen; the OS sandbox is the real boundary. Upgrade: resolve through the shell (never worth running it).
Side effects: none beyond read-only `git show|blame|config` for the grant. `--selftest` runs assertions.
"""
import importlib.util
import json
import os
import posixpath
import re
import shlex
import sys

KW = ("{", "}", "if", "then", "else", "elif", "fi", "while", "until", "do", "done", "!", "coproc")
WRAP = ("env", "command", "exec", "nohup", "sudo", "doas", "time", "builtin", "nice", "xargs", "timeout",
        "setsid", "stdbuf", "ionice", "chronic")
OPT_VAL = ("-u", "-n", "-I", "-P", "-L", "-d", "-E", "-s", "-a", "-C", "-S", "-k", "-c", "-o", "-i", "-e", "-g")
SHELLS = ("bash", "sh", "zsh", "dash", "ksh")
INTERP = re.compile(r"^(python[\d.]*|perl|ruby|node|nodejs|bun|deno|php|lua)$")
SAFE_DEV = ("/dev/null", "/dev/zero", "/dev/stdout", "/dev/stderr")
GIT_OPT_VAL = ("-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env")
LIT = r"""['"][^'"/$@][^'"$@]*['"]"""  # a literal relative path
DELAPI = re.compile(r"(rmtree|os\.(?:remove|unlink|rmdir|removedirs)|rmSync|rmdirSync|unlinkSync|\bfs\.rm|rm_rf"
                    r"|File\.delete|\bunlink|\brmdir)(?:\(|\s)(?!\s*" + LIT + r"\s*(?:[,);]|$))")
BODYRM = re.compile(r"\brm\s+-\w*[rR]\w*\s+\S*[$/~*]")
MAXDEPTH = 6
FALLBACK = [re.compile(p) for p in (
    r"\brm\s+(?:-\S+\s+)*-\w*[rR]\w*\s+(?:\S*[$`*~]|/|\.\.?(?:\s|$))",
    r"\bgit\b.*\b(?:reset\s+--hard|clean\s+-\w*f|checkout\s+(?:-f|--\s+\.|\.)|restore\s+\.|branch\s+-D|stash\s+(?:clear|drop))",
    r"\bgit\b.*\bpush\b.*(?:--force\b|\s-\w*f\w*\b|--delete|--mirror|\s[+:]\S)",
    r"\bfind\b.*(?:-delete|-exec\s+rm)", r"\bdd\b.*\bof=/dev/(?!null|zero|std)", r"\bmkfs",
    r"\b(?:chmod|chown)\s+(?:-\S+\s+)*-\w*R\w*\s+(?:\S+\s+)?[/~]", r"\b(?:pkill|killall)\b",
    r"\bkill\s+.*[$`]", r"\b(?:curl|wget)\b.*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b",
)]


def _bundle(t, ch):
    return bool(re.fullmatch(r"-[A-Za-z]+", t)) and ch in t


def _far(t):
    """Root, home, `..` escapes or an absolute path within 2 components of `/`."""
    if t.startswith(("~", "$HOME", "${HOME")):
        return True
    if "$" in t or "`" in t:
        return False
    p = posixpath.normpath(re.sub("/+", "/", t)) if t else ""
    return p in ("/", "..") or p.startswith("../..") or (p.startswith("/") and p.count("/") <= 2)


def _rm(args, piped):
    rec, tg = False, []
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
        if re.search(r"[$`*?\[]", t) or posixpath.normpath(re.sub("/+", "/", t) or ".") == "." or _far(t):
            return f"rm -r on `{t}` (variable, glob, `.`, root, home or near-root). Delete an exact, quoted in-project path, or use a container/VM"
    return ""


def _git(a):
    i = 0
    while i < len(a) and a[i].startswith("-"):
        i += 2 if a[i] in GIT_OPT_VAL else 1
    if i >= len(a):
        return ""
    sub, r = a[i], a[i + 1:]
    flags = [t for t in r if re.fullmatch(r"-[A-Za-z]+", t)]
    force = "--force" in r or any("f" in t for t in flags)
    if sub == "reset" and "--hard" in r:
        return "git reset --hard discards work. Use `git stash` or `git reset --soft`/`--mixed`"
    if sub == "clean" and force and not ("--dry-run" in r or any("n" in t for t in flags)):
        return "git clean -f deletes untracked files. Preview with `git clean -n`, delete exact paths"
    if sub == "push" and (force or "--delete" in r or "--mirror" in r or any("d" in t for t in flags)
                          or any(len(t) > 1 and t[0] in "+:" for t in r)):
        return "force/delete/mirror push rewrites shared history. Use `--force-with-lease` after the owner approves"
    if sub == "checkout" and (force or ("." in r and not any(t in r for t in ("-b", "-B")))):
        return "git checkout -f/. discards uncommitted changes. Use `git stash` or name the exact file"
    if sub == "restore" and "." in r and ("--staged" not in r or "--worktree" in r):
        return "git restore . discards uncommitted changes. Use `git stash` or name the exact file"
    if sub == "branch" and (any(_bundle(t, "D") for t in r) or (force and ("--delete" in r or any("d" in t for t in flags)))):
        return "git branch -D deletes an unmerged branch. Use `git branch -d` (refuses if unmerged)"
    if sub == "stash" and r[:1] in (["clear"], ["drop"]):
        return "git stash clear/drop loses stashed work. Use `git stash list`/`apply` and keep it"
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
            and any(_far(t) for t in a if not t.startswith("-")):
        return f"{name} -R on root/home. Target an exact in-project path"
    if name in ("pkill", "killall"):
        return f"{name} kills by pattern. `kill` the exact PID you started"
    if name == "kill" and any(re.search(r"[$`]|pgrep|pidof", t) for t in a):
        return "kill by pattern/substitution. `kill` the exact PID you started"
    if name in SHELLS + ("eval",) and any(re.search(r"\b(curl|wget)\b", t) for t in a):
        return "remote script run through a shell. Download, read it, then run it"
    if INTERP.match(name) and any(DELAPI.search(t) or BODYRM.search(t) for t in a):
        return "interpreter one-liner deleting a variable/root path. Delete an exact literal in-project path"
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
    return "destructive pattern in unparseable command (regex fallback)" if any(p.search(cmd) for p in FALLBACK) else ""


def check(cmd, _depth=0):
    """Return a one-line reason `cmd` is destructive, or '' (parse errors use the regex fallback)."""
    if _depth > MAXDEPTH:
        return _fallback(cmd)
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
    segs, ops = [[]], [""]
    for t in toks:
        if re.fullmatch(r"[;&|()<>\n]+", t):
            segs.append([])
            ops.append("|" if t in ("|", "|&") else "<(" if "<(" in t else "")
        else:
            segs[-1].append(t)
    fetch, prev = False, ""  # fetch: a curl/wget earlier in the same pipeline; prev: previous segment's command
    for seg, op in zip(segs, ops):
        if not seg:
            continue
        if op != "|":
            fetch = False
        i, piped = 0, False
        while i < len(seg):
            b = os.path.basename(seg[i])
            if re.match(r"\w+=", seg[i]) or b in KW:
                i += 1
            elif b in WRAP:
                piped |= b == "xargs"
                i += 1
                while i < len(seg) and seg[i].startswith("-"):
                    i += 2 if seg[i] in OPT_VAL else 1
                if b == "timeout" and i < len(seg):
                    i += 1  # the duration
            else:
                break
        if i >= len(seg):
            continue
        name, a = os.path.basename(seg[i]), seg[i + 1:]
        r = _cmd(name, a, piped)
        if not r and name == "eval":
            r = check(" ".join(a), _depth + 1)
        if not r and name in SHELLS:
            for j, t in enumerate(a[:-1]):
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", t):
                    r = check(a[j + 1], _depth + 1)
                    break
        if not r and op == "|" and fetch and (name in SHELLS or INTERP.match(name)):
            r = "curl/wget piped to a shell/interpreter. Download, read it, then run it"
        if not r and op == "<(" and name in ("curl", "wget") and prev in SHELLS + ("source", "."):
            r = "remote script sourced through process substitution. Download, read it, then run it"
        if r:
            return r
        fetch = fetch or name in ("curl", "wget")
        prev = name
    return ""


def _granted(cmd):
    """True when an owner-authored, committed `destructive-guard-allow:` line equals `cmd` (whitespace-normalized)."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location("focus_gate", os.path.join(here, "focus_gate.py"))
        fg = importlib.util.module_from_spec(spec)
        sys.modules["focus_gate"] = fg  # its dataclasses need the module registered
        spec.loader.exec_module(fg)
        git = fg.real_git(os.environ.get("CLAUDE_PROJECT_DIR") or ".")
        owners, _ = fg.resolve_owners(None, git)
        want = " ".join(cmd.split())
        if not owners:
            return False
        for n, ln in enumerate(git(["show", "HEAD:CLAUDE.md"]).splitlines(), 1):
            m = re.match(r"\s*destructive-guard-allow:\s*(.+?)\s*$", ln)
            if m and " ".join(m.group(1).split()) == want:
                sha = git(["blame", "--porcelain", "-L", f"{n},{n}", "HEAD", "--", "CLAUDE.md"]).split()[0]
                if fg._owner_problem(git, sha, owners, False) == "":
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
           "echo \"rm -rf $X"]
    good = ["rm -rf node_modules", "rm -rf ./build", "rm /tmp/x", "git push --force-with-lease origin f", "git clean -n",
            "git restore --staged .", "git branch -d old", "dd if=/dev/zero of=./i bs=1", "kill -TERM 4242",
            "curl -o o.sh https://example.com/i.sh", 'grep -rn "rm -rf" docs/', "echo 'git reset --hard'",
            "find . -name x"]
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
        print(f"Blocked destructive command ({why}). Owner can allow it with an owner-committed "
              "`destructive-guard-allow: <exact command>` line in CLAUDE.md.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
