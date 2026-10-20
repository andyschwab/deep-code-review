#!/usr/bin/env python3
"""Regenerate the synthetic transcript fixture next to this file (stdlib, deterministic, no real content).

Usage: python3 gen.py   (writes session.jsonl and session/subagents/*; rerun then update the pinned numbers in run.sh)
Every number below is invented arithmetic; message bodies are the literal word "synthetic".
"""
import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def line(i, t, model, ctx, new, rewrite, calls=0, side=False, last=False):
    """One assistant turn: `ctx` tokens of context, `new` of them written this turn; `rewrite` = cache expired, all of ctx re-written."""
    w = ctx if rewrite else new
    content = [{"type": "text", "text": "synthetic"}] + [
        {"type": "tool_use", "id": f"t{i}_{k}", "name": "Read", "input": {}} for k in range(calls)]
    return {"type": "assistant", "isSidechain": side, "requestId": f"r{i}", "timestamp": t.isoformat().replace("+00:00", "Z"),
            "message": {"model": model, "stop_reason": "end_turn" if last else "tool_use", "content": content,
                        "usage": {"input_tokens": 50, "output_tokens": 400, "cache_creation_input_tokens": w,
                                  "cache_creation": {"ephemeral_5m_input_tokens": w, "ephemeral_1h_input_tokens": 0},
                                  "cache_read_input_tokens": 0 if rewrite else ctx - new}}}


def write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)


def thread(model, n, start, step, every, gap, calls=0, side=False):
    """n turns, context +step each; every `every`th turn follows a `gap`-minute idle (cache expired), others follow 1 minute."""
    t, rows = T0, []
    for i in range(n):
        t += timedelta(minutes=gap if i and i % every == 0 else 1)
        rows.append(line(i, t, model, start + step * i, step if i else start, i == 0 or (i % every == 0), calls, side, i == n - 1))
    return rows


write(f"{HERE}/session.jsonl", thread("claude-opus-5-5", 60, 20_000, 4_000, 6, 12))
lanes = f"{HERE}/session/subagents"
for name, n, calls in (("agent-wide", 60, 10), ("agent-a", 10, 4), ("agent-b", 10, 4), ("agent-c", 10, 4)):
    write(f"{lanes}/{name}.jsonl", thread("claude-sonnet-5-5", n, 28_000, 2_500, 10**6, 1, calls, True))
    write(f"{lanes}/{name}.meta.json", [{"description": f"synthetic lane {name}", "agentType": "synthetic"}])
