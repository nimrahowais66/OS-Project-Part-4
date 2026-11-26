"""RQ1 / injection experiment.
python3 -m pidlab.run_injection --model llama3.2:3b --n 100 --temps 0 0.7 --out results/inj_3b.jsonl"""
import argparse
from . import runner, scenarios
ap = argparse.ArgumentParser()
ap.add_argument("--model", default="llama3.2:3b"); ap.add_argument("--n", type=int, default=100)
ap.add_argument("--temps", type=float, nargs="+", default=[0.0, 0.7])
ap.add_argument("--san", nargs="+", default=["S0", "S1", "S2"])
ap.add_argument("--classes", nargs="+", default=list(scenarios.CLASSES))
ap.add_argument("--difficulty", default="obvious", choices=["obvious", "camouflage"])
ap.add_argument("--out", default="results/inj.jsonl"); ap.add_argument("--mock", action="store_true")
a = ap.parse_args()
items = [dict(cls=c, inst=i, san=s, temp=t, seed=i, difficulty=a.difficulty)
         for c in a.classes for i in range(a.n) for s in a.san for t in a.temps]
runner.run_experiment(a.out, items, a.model, a.mock)
