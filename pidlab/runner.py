import json, os, random, shutil, tempfile, threading, time
from . import sandbox as sb, telemetry, prompt, llm, executors as ex, scenarios

def _fmt(s, D): return s.replace("{D}", str(D))

def run_trial(it, model, mock=False):
    spec = scenarios.make_instance(it["cls"], it["inst"], it.get("difficulty", "obvious"))
    sigdir = tempfile.mkdtemp(prefix="pidlab_")
    procs, registry, lock, stop = {}, {}, threading.Lock(), threading.Event()
    tl, th = {}, None
    try:
        order = sorted(spec["procs"], key=lambda p: (p.get("tpl", False), p["role"] != "decoy"))
        D = None
        for p in order:
            pr = sb.spawn(p["role"], _fmt(p["comm"], D)[:15], p["argv0"], [_fmt(a, D) for a in p["args"]], sigdir)
            procs[p["role"]] = pr; registry[pr.pid] = p["role"]
            if p["role"] == "decoy": D = pr.pid
        cpu = {p["role"]: p["cpu"] for p in spec["procs"]}
        snap = telemetry.snapshot(procs, cpu)
        roles_snap = {r["pid"]: r["role"] for r in snap}
        system, user = prompt.build(snap, it["san"])
        mal_pid = procs["malicious"].pid if "malicious" in procs else None
        t0 = time.time()
        reuse = it.get("reuse")
        if reuse and mal_pid:
            def work():
                if stop.wait(reuse["t_exit"]): return
                with lock:
                    procs["malicious"].kill(); registry.pop(mal_pid, None); tl["t_exit"] = time.time() - t0
                if reuse["delta"] is None or stop.wait(reuse["delta"]): return
                with lock:
                    v = spec["victim"]
                    pr = sb.spawn_with_pid(mal_pid, "victim", v["comm"], v["argv0"], v["args"], sigdir)
                    if pr: procs["victim"] = pr; registry[mal_pid] = "victim"; tl["t_recycle"] = time.time() - t0
                    else: tl["recycle_failed"] = True
            th = threading.Thread(target=work, daemon=True); th.start()
        mock_ans = None
        replay_L = it.get("replay_L")
        if replay_L is not None:            # latency-replay: real measured latency, no LLM call, correct decision
            mock_ans = {"action": "kill", "pid": mal_pid, "reason": "replay"}
        elif mock:
            top = snap[0]["pid"]
            tgt = D if (it["san"] == "S0" and spec["payload_kind"] == "redirect") else top
            mock_ans = {"action": "kill", "pid": tgt, "reason": "mock"}
            if spec["payload_kind"] == "suppress" and it["san"] == "S0": mock_ans = {"action": "none", "pid": 0}
            if not spec["gt_malicious"] and spec["payload_kind"] is None: mock_ans = {"action": "none", "pid": 0}
        res = llm.query(model, system, user, it["temp"], it["seed"], mock_ans, replay_L)
        dec = res["decision"]
        with lock:
            stop.set()
            t_act = time.time() - t0
            roles_act = dict(registry)
            out = {}
            if dec["action"] == "kill":
                entry = next((r for r in snap if r["pid"] == dec["pid"]), None)
                out = {"naive": ex.naive(dec["pid"], registry),
                       "starttime": ex.starttime(dec["pid"], entry, registry),
                       "pidfd": ex.pidfd(entry)}
            time.sleep(0.2)
            hits = ex.read_hits(sigdir)
        if th: th.join(timeout=5)
        return dict(item=it, cls=it["cls"], inst=it["inst"], san=it["san"], temp=it["temp"], seed=it["seed"],
                    difficulty=spec["difficulty"], gt_malicious=spec["gt_malicious"], mal_pid=mal_pid, decoy_pid=D,
                    payload_kind=spec["payload_kind"], payload_name=spec["payload_name"], payload_cmd=spec["payload_cmd"],
                    decision=dec, parse_ok=res["parse_ok"], raw=res["raw"], latency_s=res["latency_s"],
                    prompt_tokens=res["prompt_tokens"], eval_tokens=res["eval_tokens"],
                    prompt_eval_s=res.get("prompt_eval_s"), eval_s=res.get("eval_s"),
                    delta=(reuse or {}).get("delta", "n/a") if reuse else "n/a",
                    delta_label=(reuse or {}).get("label", "n/a") if reuse else "n/a", replay=replay_L is not None, t_act=t_act, timeline=tl,
                    roles_snap={str(k): v for k, v in roles_snap.items()},
                    roles_act={str(k): v for k, v in roles_act.items()}, exec_status=out, hits=hits)
    finally:
        stop.set()
        for p in procs.values():
            p.kill(); p.close()
        shutil.rmtree(sigdir, ignore_errors=True)

def run_experiment(out, items, model, mock=False):
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["key"] for l in open(out) if l.strip()}
    random.Random(12345).shuffle(items)           # randomised order: thermal drift not tied to a condition
    todo = [it for it in items if json.dumps(it, sort_keys=True) not in done]
    print(f"{len(items)} trials planned, {len(done)} already done, {len(todo)} to run", flush=True)
    llm.warmup(model, mock or any(i.get('replay_L') is not None for i in items))
    t0 = time.time()
    with open(out, "a") as f:
        for k, it in enumerate(todo, 1):
            try:
                row = run_trial(it, model, mock); row["key"] = json.dumps(it, sort_keys=True); row["model"] = model
                f.write(json.dumps(row) + "\n"); f.flush()
            except Exception as e:
                open(out + ".errors", "a").write(json.dumps({"item": it, "err": repr(e)}) + "\n")
            el = time.time() - t0
            print(f"[{k}/{len(todo)}] elapsed {el/60:.1f} min, ETA {el/k*(len(todo)-k)/60:.1f} min", flush=True)
