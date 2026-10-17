#!/usr/bin/env python3
"""mutation_changed.equivalent(): each known equivalent-mutant shape is recognised, and near-misses are not."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/agentic-delivery/scripts"))
from mutation_changed import equivalent as eq  # noqa: E402

# codec alias
assert eq("open(p, encoding='utf-8')\n", 1, "open(p, encoding='utf-8')", "open(p, encoding='UTF-8')")
assert not eq("open(p, encoding='utf-8')\n", 1, "open(p, encoding='utf-8')", "open(p, encoding='latin-1')")
assert not eq("x = 'a'\n", 1, "x = 'a'", "x = 'A'")  # a case change outside encoding= is a real change

# falsy flag kwarg
assert eq("d.popitem(last=False)\n", 1, "d.popitem(last=False)", "d.popitem(last=None)")
assert not eq("d.popitem(last=False)\n", 1, "d.popitem(last=False)", "d.popitem(last=True)")
assert not eq("f(strict=False)\n", 1, "f(strict=False)", "f(strict=None)")  # unknown kwarg: could test `is False`

# tail break -> return
TAIL = "async def run(q):\n    while True:\n        item = await q.get()\n        if item is None:\n            break\n        use(item)\n"
assert eq(TAIL, 5, "break", "return")
assert not eq(TAIL + "    done()\n", 5, "break", "return")  # code runs after the loop
NESTED = "def f(xs):\n    for x in xs:\n        for y in x:\n            if y:\n                break\n"
assert not eq(NESTED, 5, "break", "return")  # inner break lets the outer loop go on
assert not eq("def f(xs):\n    for x in xs:\n        break\n    else:\n        g()\n", 3, "break", "return")  # loop else
assert not eq("def f(xs):\n    try:\n        for x in xs:\n            break\n    finally:\n        g()\n", 4, "break", "return")
assert not eq("for x in xs:\n    break\n", 2, "break", "return")  # module level: return is a SyntaxError

# constant only ever raised
RAISE = "def f(g):\n    last = None\n    for _ in range(3):\n        try:\n            return g()\n        except OSError as e:\n            last = e\n    raise last\n"
assert eq(RAISE, 2, "last = None", 'last = ""')
assert not eq(RAISE.replace("raise last", "return last"), 2, "last = None", 'last = ""')  # value is returned: visible
assert not eq(RAISE, 2, "last = None", "last = Exception()")  # not a literal constant

# strip set gains only X on lowercased data
SLUG = "def s(t):\n    slug = t.lower().strip('-')\n    return slug.rstrip('-')\n"
assert eq(SLUG, 2, "slug = t.lower().strip('-')", "slug = t.lower().strip('XX-XX')")
assert not eq(SLUG.replace(".lower()", ""), 2, "slug = t.strip('-')", "slug = t.strip('XX-XX')")  # data may hold X
assert not eq(SLUG.replace("rstrip('-')", "rstrip('-') + 'X'"), 2, "slug = t.lower().strip('-')", "slug = t.lower().strip('XX-XX')")
assert not eq(SLUG, 2, "slug = t.lower().strip('-')", "slug = t.lower().strip('-', 1)")
assert not eq(SLUG, 2, "slug = t.lower().strip('-')", "slug = t.lower().strip('XXYY-XX')")  # other chars added

# anchoring: the codec rule only fires on the encoding= literal, the flag rule only on its stdlib call
assert not eq("open('A.txt', encoding='utf-8')\n", 1, "open('A.txt', encoding='utf-8')", "open('a.txt', encoding='utf-8')")  # path changed
assert not eq("x = 'A'  # encoding='utf-8'\n", 1, "x = 'A'  # encoding='utf-8'", "x = 'a'  # encoding='utf-8'")
assert not eq("open(p, encoding=ENC)\n", 1, "open(p, encoding=ENC)", "open(p, encoding=enc)")  # not a literal
assert not eq("foo(last=False)\n", 1, "foo(last=False)", "foo(last=None)")  # not a stdlib call
assert not eq("d.popitem(flast=False)\n", 1, "d.popitem(flast=False)", "d.popitem(flast=None)")  # no word boundary
assert not eq("f(my_reverse=False)\n", 1, "sorted(xs, my_reverse=False)", "sorted(xs, my_reverse=None)")
assert not eq("f(x, last=False)\n", 1, "mylib.popitem2(x, last=False)", "mylib.popitem2(x, last=None)")
assert eq("sorted(xs, reverse=False)\n", 1, "sorted(xs, reverse=False)", "sorted(xs, reverse=None)")
assert eq("print(x, flush=False)\n", 1, "print(x, flush=False)", "print(x, flush=None)")

print("test_mutation_equivalent: ok")
