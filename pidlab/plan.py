"""python3 -m pidlab.plan <mean_L_seconds> [budget_hours]   (default budget 30 h of unattended compute)"""
import sys
L = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
H = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
per = L + 2.0                                   # + spawn/cleanup overhead per trial
cap = int(H * 3600 / per)
print(f"L={L:.1f}s -> ~{per:.0f}s/trial -> {cap} real inferences fit in {H:.0f} h\n")
tiers = [("A minimal (main model only)", 4 * 2 * 40 * 1, "classes C0,I-N,I-C,N-I x S0,S1 x n=40, temp 0"),
         ("B standard", 6 * 2 * 60, "6 classes x S0,S1 x n=60, temp 0   (add S2 / temp 0.7 only if time remains)"),
         ("C full", 6 * 3 * 2 * 100, "6 classes x S0,S1,S2 x temp 0,0.7 x n=100")]
for name, n, d in tiers:
    print(f"{name:30s} {n:5d} inferences = {n*per/3600:6.1f} h   [{d}] {'<-- fits' if n <= cap else '(too long)'}")
print("\nPID-reuse: use latency REPLAY (no LLM cost; only sleeps). With --time-scale 0.25:",
      f"{6*2*100} trials x ~{(L*0.25+2):.0f}s = {6*2*100*(L*0.25+2)/3600:.1f} h.  Add ~20 real-inference trials to validate.")
