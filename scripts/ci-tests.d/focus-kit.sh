# Registers the focus-kit checks with CI (see the "Per-PR tests" step in ci.yml).
# docs/INDEX.md is the project docs map; docs/bench is data and is left out. --check proves the committed
# map is what `docs-index` would write today (an unlanded tree is rebuilt by regen-unlanded.sh first).
python3 .claude/skills/agentic-delivery/scripts/focus_kit.py docs-index --exclude bench --check
python3 scripts/test_focus_kit.py
