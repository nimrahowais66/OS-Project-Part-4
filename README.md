# Wrong-target actions in a local LLM defender — experiment kit

Defender = LLM + JSON action `{"action":"kill|none","pid":N}`. The harness never touches real processes:
all targets are idle dummy processes inside a private PID namespace inside an 8 GB / 4-core Docker container.

## 0. Hardware: one machine or two?
**Use ONE 16 GB machine for every measurement.** Latency is the independent variable of RQ2, so all runs must come
from the same CPU, thermal state and container config. Two machines would add a between-machine confound.
A second machine is only worth using for (a) a small validation subset (~10 % of trials) to show the Docker emulation
is not machine-specific, or (b) running the *analysis*/writing while the first one computes.
Never run two experiments concurrently on the same machine (they steal CPU and corrupt latency).
Needs native Linux or WSL2 (kernel >= 5.3 for pidfd, Python >= 3.9). Docker Desktop on macOS/Windows hides
the real kernel behaviour, so avoid it. Plug in power, set CPU governor to `performance`, close the browser/IDE.

## 1. Setup (once)
```
./run_container.sh                       # builds image, starts capped container with ollama serve
# inside the container:
ollama pull tinyllama; ollama pull llama3.2:3b; ollama pull llama3.1:8b
./sandbox_run.sh python3 -m pidlab.selfcheck     # every line must say OK
```
Edit `config.py` only to change `NUM_CTX` / `NUM_THREAD`; report them in the paper.

## 2. Experiments, cycles and conditions
Randomisation unit = scenario *instance* (random decoy/background/PIDs/payload), NOT repeated identical prompts:
at temperature 0 repeats are identical, so extra "cycles" of the same prompt add no information.
The same instance is replayed under every mitigation (paired design -> McNemar test).
Trial order is shuffled (fixed seed) so thermal drift is not tied to a condition. Runs resume if interrupted.

| Exp | Purpose | Factors | n | Inferences (3B model) |
|---|---|---|---|---|
| E0 latency | RQ2 input L | model x {8,16,32,64 procs} | 20 reps each | ~240 |
| E1 injection | RQ1, RQ3 | 6 classes x {S0,S1,S2} x temp {0,0.7} | 100 instances / cell | 3,600 |
| E2 PID reuse | RQ2, RQ3 | recycle delay {0,2,5,10,30,none}s x {S0,S1} | 50 / cell | 600 |
| E3 other models | RQ2 (L varies) + RQ1 robustness | tinyllama and llama3.1:8b, injection n=50 (temp 0 only), reuse n=40 | | ~1,500 |
| E4 hard mode (optional) | reuse of Part 3 "camouflage" | `--difficulty camouflage` | n=50 | |

Classes: C0 threat/no injection (control), I-N name, I-C cmdline, I-B both, N0 benign/no injection (control),
N-I benign process carrying a kill payload (acting when nothing needed). S0 raw, S1 strip+limit+quote,
S2 = S1 + "untrusted data" system-prompt warning. Identity verification (V) is evaluated *inside every trial*:
`naive` (os.kill), `starttime` (/proc/pid/stat field 22), `pidfd` (opened at detection) all act on the same decision
-> the 2x2 (S x V) costs no extra inference.

Wall-clock: `python3 -m pidlab.plan <mean_L_seconds>` after E0. Rough guide: 3B ~ 8-15 s/call -> E1 ~ 10-15 h,
E2 ~ 2 h; so do a pilot first (`--n 10`), then run the full set overnight in chunks.
Precision: n=100 gives Wilson half-width ~ +/-6 pp near 10 % and ~ +/-10 pp near 50 %. Report the CIs.

## 3. Commands
```
./sandbox_run.sh python3 -m pidlab.run_latency --models tinyllama llama3.2:3b llama3.1:8b
python3 -m pidlab.plan 10
./sandbox_run.sh python3 -m pidlab.run_injection --model llama3.2:3b --n 10 --out results/pilot.jsonl      # pilot
./sandbox_run.sh python3 -m pidlab.run_injection --model llama3.2:3b --n 100 --out results/inj_3b.jsonl
./sandbox_run.sh python3 -m pidlab.run_pidreuse  --model llama3.2:3b --n 50  --out results/reuse_3b.jsonl
./sandbox_run.sh python3 -m pidlab.run_injection --model tinyllama --n 50 --temps 0 --out results/inj_tiny.jsonl
./sandbox_run.sh python3 -m pidlab.run_pidreuse  --model llama3.1:8b --n 40 --out results/reuse_8b.jsonl
python3 -m pidlab.analyze results/inj_*.jsonl results/reuse_*.jsonl     # CSV tables + PNG figures
```
`--mock` runs the whole pipeline without Ollama (smoke test only).

## 4. Design notes you must state in the report
* Process *name* (`comm`) is truncated by the kernel to 15 bytes; only short payloads fit the name. cmdline is
  effectively unlimited. This is itself a finding (name vs cmdline injection capacity).
* Wrong-target is measured at two levels: **intent** (what the model chose) and **effect** (which dummy actually
  received the signal, per executor). PID-reuse "misfire" = effect hit the recycled victim *given* a correct intent.
* In the harness, signal numbers (SIGUSR1/USR2/SIGTERM) are only tags identifying which executor delivered; dummies
  record and survive. The naive executor can only signal PIDs owned by that trial's dummies (safety guard).
* PID recycling is *forced* with `/proc/sys/kernel/ns_last_pid`; `delta` is the controlled recycle delay.
  Natural reuse probability is rare on Linux (sequential allocation); `analyze.py` prints the analytic estimate
  ~ lambda*L/pid_max for fork rates lambda. Report both: conditional misfire rate and realistic exposure.
* starttime check has 10 ms (clock-tick) resolution and a check-then-kill TOCTOU window; pidfd has neither.
* CPU% is scenario-assigned (dummies idle) so they do not perturb inference latency.
* Memory cap does not slow the CPU; latencies are specific to this host + `--cpuset-cpus` + thread count.
* Ollama may reuse the KV cache for the constant system-prompt prefix; this is realistic for a daemon, but say so.

## 5. Update after reading your Part 3 report and Part 2 repo
Part 3 numbers (your hardware): llama3.2:3b needed a 150 s limit (45 s gave all timeouts) and averaged ~81 s to detect;
llama3.1:8b detected 0/27 even at 150 s; TinyLlama 0/27; no model ever killed a virus. Consequences for this project:

1. **Latency will be tens of seconds, not ~10 s.** Run E0 first and plan from the measured L: `python3 -m pidlab.plan <L> <hours>`.
   The full design (Tier C, 3,600 inferences) is ~80 h at L=80 s, so it is not feasible. Tiers A/B in `plan.py` are.
2. **PID reuse uses latency REPLAY** (`run_pidreuse --replay ... --time-scale 0.25`): the race depends only on timing, so
   the "inference" is a sleep drawn from the measured latency distribution (no LLM cost). Validate with ~20 real-inference
   trials at scale 1 and show the misfire rates agree. Deltas are multiples of L (`--L`).
3. **Capability gate before anything else:** pilot with `run_injection --classes C0 N0 --san S0 --temps 0 --n 10`, then
   `python3 -m pidlab.gate results/pilot.jsonl`. If the model cannot pick the right process with NO injection, injection
   results are unreadable (floor/ceiling). Part 3's 0/27 may have come from the tool-calling/agent loop and timeouts,
   not raw ability; this harness uses one constrained-JSON call, so it may do better. The pilot tells you.
4. **Speed levers** (all in `config.py`/env): free-text `reason` is off by default (`REASON=1` to enable; fewer output tokens),
   `NUM_CTX` 4096 (Part 2 exported 16384: do NOT export OLLAMA_CONTEXT_LENGTH here), 6-8 processes per snapshot, one model loaded.
5. **Check your environment (hypothesis, I cannot see your machine):** if you used WSL2, its default memory cap is 50 % of
   host RAM (8 GB on a 16 GB laptop), so an 8 GB container inside it, plus Ollama, likely swaps/thrashes. Set `memory=12GB`
   and `swap=0` in `%UserProfile%\.wslconfig`, `wsl --shutdown`, and confirm `ollama ps` shows 100% CPU, model loaded once.
   `run_latency.py` prints tokens and prompt/eval seconds so you can see whether prompt processing or generation dominates.
6. **Use the same timeout for every model** (this harness has none beyond 900 s), unlike Part 3 where TinyLlama differed.
7. **Reuse from the Part 2 repo:** `report_generator.py` (python-docx) for the final write-up tables; the whitelist idea of
   `ALLOWED_INSTALL` is mirrored by the executors' "only PIDs owned by this trial" guard; Part 2 used TEMPERATURE=0.1 while
   the manual says 0 — here temperature is explicit (0 and 0.7 with seeds). The Part 2 debate supervisor (4 debaters + judge +
   summariser, several LLM calls) would multiply L and widen the reuse window; a good optional extension (E5), not built.
