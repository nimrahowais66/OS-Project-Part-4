import json, re, time, requests
from . import config

SCHEMA = {"type": "object",
          "properties": {"action": {"type": "string", "enum": ["kill", "none"]}, "pid": {"type": "integer"},
                         **({"reason": {"type": "string"}} if config.REASON else {})},
          "required": ["action", "pid"]}

def _parse(raw):
    try:
        d = json.loads(raw)
        a, p = d["action"], int(d.get("pid", 0))
        if a not in ("kill", "none"): raise ValueError
        return {"action": a, "pid": p if a == "kill" else 0}, True
    except Exception:
        return {"action": "none", "pid": 0}, False

def query(model, system, user, temperature=0.0, seed=0, mock_answer=None, mock_latency=None):
    if mock_answer is not None:                           # smoke-test path, no Ollama needed
        lat = config.MOCK_LATENCY if mock_latency is None else mock_latency
        time.sleep(lat)
        raw = json.dumps(mock_answer); dec, ok = _parse(raw)
        return dict(decision=dec, parse_ok=ok, raw=raw, latency_s=lat,
                    prompt_tokens=0, eval_tokens=0, load_s=0.0)
    body = {"model": model, "stream": False, "format": SCHEMA, "keep_alive": config.KEEP_ALIVE,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": temperature, "seed": seed, "num_ctx": config.NUM_CTX,
                        "num_thread": config.NUM_THREAD, "num_predict": config.NUM_PREDICT}}
    t = time.perf_counter()
    r = requests.post(config.OLLAMA_URL + "/api/chat", json=body, timeout=900)
    lat = time.perf_counter() - t
    r.raise_for_status(); j = r.json(); raw = j["message"]["content"]
    dec, ok = _parse(raw)
    return dict(decision=dec, parse_ok=ok, raw=raw[:300], latency_s=lat,
                prompt_tokens=j.get("prompt_eval_count", 0), eval_tokens=j.get("eval_count", 0),
                load_s=j.get("load_duration", 0) / 1e9,
                prompt_eval_s=j.get("prompt_eval_duration", 0) / 1e9,
                eval_s=j.get("eval_duration", 0) / 1e9)

def warmup(model, mock=False):
    if not mock:
        query(model, "Reply with JSON.", "Say none.", 0.0, 0)   # load weights; excluded from results
