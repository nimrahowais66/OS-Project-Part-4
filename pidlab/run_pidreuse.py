"""RQ2 / PID-reuse experiment. MUST run inside a private PID namespace (see sandbox_run.sh).

Timeline per trial: t=0 request -> t=t_exit flagged process exits (reaped) -> t=t_exit+delta the SAME PID is
re-issued to an innocent process; the action fires when inference returns (latency L).

  Real inference:    python3 -m pidlab.run_pidreuse --model llama3.2:3b --n 20 --L 80 --out results/reuse_real.jsonl
  Latency replay:    python3 -m pidlab.run_pidreuse --replay results/inj_3b.jsonl --n 100 --L 80 --time-scale 0.25 \\
                         --out results/reuse_replay.jsonl
Replay = no LLM call; the 'inference' is a sleep drawn from the EMPIRICAL latency distribution measured in earlier
real runs. Valid because the race only depends on timing (t_recycle vs L), not on model output. --time-scale <1 shrinks
all times by the same factor (race outcome depends on ratios). Validate once with scale 1 against the real-inference run.
Deltas: with --L they are multiples of L (rel: 0, 0.25, 0.5, 1, 2, none); otherwise absolute seconds."""
import argparse, json, os, random, sys
from . import runner
ap = argparse.ArgumentParser()
ap.add_argument("--model", default="llama3.2:3b"); ap.add_argument("--n", type=int, default=50)
ap.add_argument("--deltas", nargs="+", default=["0", "0.25", "0.5", "1", "2", "none"])
ap.add_argument("--L", type=float, default=None, help="mean latency (s); if given, deltas are multiples of L")
ap.add_argument("--san", nargs="+", default=["S0", "S1"]); ap.add_argument("--t_exit", type=float, default=0.5)
ap.add_argument("--temp", type=float, default=0.0)
ap.add_argument("--replay", default=None, help="jsonl with measured latency_s to sample from (no LLM calls)")
ap.add_argument("--time-scale", type=float, default=1.0)
ap.add_argument("--out", default="results/reuse.jsonl"); ap.add_argument("--mock", action="store_true")
a = ap.parse_args()
if os.environ.get("IN_SANDBOX") != "1":
    sys.exit("Run via ./sandbox_run.sh (private PID namespace) so PID forcing cannot touch real processes.")
lat = {}
if a.replay:
    for l in open(a.replay):
        r = json.loads(l); lat.setdefault(r["san"], []).append(r["latency_s"])
sc = a.time_scale
items = []
for i in range(a.n):
    for s in a.san:
        for d in a.deltas:
            absd = None if d == "none" else float(d) * (a.L if a.L else 1.0)
            it = dict(cls="C0", inst=i, san=s, temp=a.temp, seed=i, difficulty="obvious",
                      reuse=dict(t_exit=a.t_exit * sc, delta=None if absd is None else absd * sc,
                                 label=("x" + d + "L") if a.L else d + "s"))
            if a.replay:
                pool = lat.get(s) or sum(lat.values(), [])
                it["replay_L"] = round(random.Random(f"{i}{s}").choice(pool) * sc, 3); it["time_scale"] = sc
            items.append(it)
runner.run_experiment(a.out, items, a.model, a.mock)
