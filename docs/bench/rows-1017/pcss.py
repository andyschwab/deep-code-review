"""Minimal PCSS (OpenAI-compatible) chat client.

Key: PCSS_KEY env var, else the first existing .env among ./.env and the repo-root .env
of the main checkout (a worktree has no .env of its own).
"""
import http.client, json, os, re, time, urllib.request, urllib.error

BASE = "https://llm.hpc.psnc.pl/v1"
ENVS = [".env", "../../../.env", os.path.expanduser("~/Desktop/deep-code-review/.env")]


def _key():
    if os.environ.get("PCSS_KEY"):
        return os.environ["PCSS_KEY"]
    for p in ENVS:
        if os.path.exists(p):
            return open(p).read().split("=", 1)[1].strip()
    raise RuntimeError("no PCSS_KEY and no .env found")


def chat(model, system, user, max_tokens=3000, temperature=0.7, tries=4):
    """One chat completion; returns text with <think> blocks stripped. Raises after `tries` failures."""
    body = {"model": model, "temperature": temperature, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False, "thinking": False},
            "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]}
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + "/chat/completions", json.dumps(body).encode(),
                                         {"Authorization": "Bearer " + _key(), "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=600))
            t = r["choices"][0]["message"]["content"] or ""
            t = re.sub(r"<think>.*?</think>", "", t, flags=re.S).strip()
            if t:
                return t
            err = "empty content (finish_reason %s)" % r["choices"][0].get("finish_reason")
        except (urllib.error.URLError, TimeoutError, KeyError, http.client.HTTPException) as e:
            err = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"pcss failed: {err}")


if __name__ == "__main__":
    req = urllib.request.Request(BASE + "/models", headers={"Authorization": "Bearer " + _key()})
    print([m["id"] for m in json.load(urllib.request.urlopen(req, timeout=30))["data"]])
