"""Inference-latency benchmark on the capped container (feeds RQ2 and the run-time planner).
python3 -m pidlab.run_latency --models tinyllama llama3.2:3b llama3.1:8b --sizes 8 16 32 64 --reps 20"""
import argparse, csv, os, random, subprocess
from . import llm, prompt, config
def peak_mem():
    for p in ("/sys/fs/cgroup/memory.peak", "/sys/fs/cgroup/memory/memory.max_usage_in_bytes"):
        if os.path.exists(p): return int(open(p).read()) / 2**30
    return float("nan")
def fake_snap(n, rng):
    names = ["bash", "sshd", "python3", "nginx", "postgres", "cron", "vim", "java"]
    return [dict(pid=rng.randint(2, 30000), name=rng.choice(names), cmdline="/usr/bin/x --opt " + "a" * rng.randint(5, 60),
                 cpu=round(rng.uniform(0, 99), 1), ppid=1) for _ in range(n)]
ap = argparse.ArgumentParser()
ap.add_argument("--models", nargs="+", default=config.MODELS); ap.add_argument("--sizes", type=int, nargs="+", default=[8, 16, 32, 64])
ap.add_argument("--reps", type=int, default=20); ap.add_argument("--out", default="results/latency.csv")
a = ap.parse_args(); rng = random.Random(1)
cpu = subprocess.run("lscpu | grep 'Model name'", shell=True, capture_output=True, text=True).stdout.strip()
print(cpu, "| threads:", config.NUM_THREAD, "| ctx:", config.NUM_CTX)
with open(a.out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "n_proc", "rep", "latency_s", "prompt_tokens", "eval_tokens", "prompt_eval_s", "eval_s", "peak_mem_gib"])
    for m in a.models:
        llm.warmup(m)
        for n in a.sizes:
            for r in range(a.reps):
                sysm, usr = prompt.build(fake_snap(n, rng), "S1")
                x = llm.query(m, sysm, usr, 0.0, r)
                w.writerow([m, n, r, x["latency_s"], x["prompt_tokens"], x["eval_tokens"], x.get("prompt_eval_s"), x.get("eval_s"), peak_mem()])
                f.flush()
            print(m, n, "done", flush=True)
