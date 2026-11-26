# pidlab: LLM defender, prompt injection and PID reuse

Measures how often a **local LLM defender** (Llama-3.1 8B via Ollama, CPU-only, 8 GB, 4 cores) takes a **wrong-target kill** because of

* **(a)** attacker-controlled strings in process telemetry (prompt injection through process name / command line), and
* **(b)** **PID reuse** during the seconds of inference between detection and response,

and how much **input sanitization** (S1, S2) and **identity-verified actions** (start-time check, `pidfd`) reduce these errors.

All processes in the experiments are **harmless idle dummies** that only record the signals they receive. Nothing real is ever killed, and PID forcing happens only inside a private PID namespace.

## Headline results (Llama-3.1 8B, temperature 0)

| Class | S0 raw | S1 sanitized | S2 S1+warning |
|---|---|---|---|
| C0 / N0 (controls) | 0/60 | 0/60 | 0/60 |
| I-N (attack in name) | 1/60 | 0/60 | 0/60 |
| I-C (attack in cmdline) | 8/60 | 0/60 | 0/60 |
| I-B (both) | 35/60 | 0/60 | 0/60 |
| N-I (no threat, benign process carries kill order) | 43/60 | 32/60 | 20/60 |

* Mean inference latency: S0 19.1 s, S1 26.8 s, S2 27.0 s (overall L = 24.3 s).
* PID reuse: whenever the PID was recycled before the action, the naive `kill` hit the innocent process every time. `starttime` and `pidfd` produced no misfires (replay n=100 per cell; real run n=10, S0).

See `report/main.tex` for the full write-up and limitations.

## Repository layout

```
pidlab_project/
├── Dockerfile               # image: Python + Ollama client deps
├── run_container.sh         # builds the image and starts the container (name: pidlab)
├── sandbox_run.sh           # runs a command inside a private PID namespace (sets IN_SANDBOX=1)
├── pidlab/
│   ├── config.py            # all settings (model list, ctx, threads, tokens, keep-alive)
│   ├── prompt.py            # system prompt (v5, frozen) + S0/S1/S2 prompt builders
│   ├── sanitize.py          # control/zero-width stripping, whitespace collapse, length limits
│   ├── scenarios.py         # six classes, decoys/miners/background, 14 injection payloads
│   ├── sandbox.py           # spawn dummies, read /proc identity, force PID reuse, pidfds
│   ├── dummy_proc.py        # idle stand-in process that records signals
│   ├── telemetry.py         # builds the process snapshot from /proc
│   ├── llm.py               # Ollama call (JSON-schema output), latency + token logging
│   ├── executors.py         # naive / starttime / pidfd executors, hit reader
│   ├── runner.py            # one trial + resumable experiment loop
│   ├── run_injection.py     # E1: prompt-injection experiment
│   ├── run_pidreuse.py      # E2: PID-reuse experiment (real or latency replay)
│   ├── run_latency.py       # latency benchmark vs. snapshot size
│   ├── gate.py              # go/no-go check on a pilot run
│   ├── plan.py              # run-time planner
│   ├── selfcheck.py         # environment check (run before any experiment)
│   └── analyze.py           # tables (CSV) + figures (PNG) from result files
├── results/                 # *.jsonl raw trials, *.csv tables, fig_*.png
└── report/                  # IEEE-format LaTeX report (main.tex, figs/)
```

## Requirements

* Linux host with Docker (kernel >= 5.3 for `pidfd_open`; Python >= 3.9 in the container).
* Ollama running inside the container, with the model pulled once: `ollama pull llama3.1:8b` (models are kept in the `pidlab_models` Docker volume).
* On the host, for analysis only: Python 3 with `pandas`, `matplotlib`, `requests` (a venv is fine).
* The container is started with an **8 GB memory cap**, 4 pinned cores, and `CAP_SYS_ADMIN` (needed to write `ns_last_pid` inside the private PID namespace). **Do not raise the 8 GB cap**: it is the experiment's "defender box".
* Internet is needed only to build the image and pull models. The runs themselves are offline.

## How to run

All commands marked *container* run inside the container (`./run_container.sh`, or `docker exec -it pidlab bash`), from `/work`. For long runs use `tmux` (detach with `Ctrl+b`, then `d`).

### 0. Start and check the environment (container)

```bash
./run_container.sh
python3 -m pidlab.selfcheck          # every line should say OK
python3 -c "from pidlab import prompt; print(prompt.SYSTEM)"   # must be the frozen v5 prompt
```

### 1. Pilot and gate (container, ~10 min)

```bash
./sandbox_run.sh python3 -m pidlab.run_injection --model llama3.1:8b --n 10 \
    --classes C0 N0 --san S0 --temps 0 --out results/pilot.jsonl
python3 -m pidlab.gate results/pilot.jsonl      # expect GO
```

### 2. E1: prompt injection (container, ~6 h, 1,080 trials)

```bash
./sandbox_run.sh python3 -m pidlab.run_injection --model llama3.1:8b --n 60 \
    --san S0 S1 S2 --temps 0 --out results/inj_8b.jsonl
```

The run is **resumable**: if it stops, run the identical command again and only missing trials are executed. Failed trials (for example Ollama killed at the memory limit) are logged to `results/inj_8b.jsonl.errors` and are retried by re-running. Check progress with `wc -l results/inj_8b.jsonl` (goal: 1080).

### 3. E2: PID reuse, latency replay (container, ~2.5 h, 1,200 trials)

Uses the real latencies from E1; no model is called. `--L` is the mean latency measured in E1 (24 s here); delays are multiples of `L`.

```bash
./sandbox_run.sh python3 -m pidlab.run_pidreuse --replay results/inj_8b.jsonl \
    --model llama3.1:8b --n 100 --L 24 --time-scale 0.25 --out results/reuse_replay.jsonl
```

### 4. E2 validation with real inference (container, ~30 min, 60 trials)

Run only after step 3 has finished (the two would compete for CPU).

```bash
./sandbox_run.sh python3 -m pidlab.run_pidreuse --model llama3.1:8b --n 10 \
    --san S0 --L 24 --out results/reuse_real.jsonl
```

Optional: `--deltas 0.5 0.7 0.85 1 1.15 1.3 --san S0 S1` for a finer delay grid, and `--n 20 --san S1 --deltas 1` for a real S1 check.

### 5. Analysis (host, in the venv)

Analyse each file separately (real and replay latencies must not be mixed). Each PID-reuse run overwrites `pidreuse_rates.csv` and `fig_pidreuse.png`, so copy them after each run.

```bash
python3 -W ignore -m pidlab.analyze results/inj_8b.jsonl

python3 -W ignore -m pidlab.analyze results/reuse_replay.jsonl
cp results/pidreuse_rates.csv results/pidreuse_replay_rates.csv
cp results/fig_pidreuse.png   results/fig_pidreuse_replay.png

python3 -W ignore -m pidlab.analyze results/reuse_real.jsonl
cp results/pidreuse_rates.csv results/pidreuse_real_rates.csv
cp results/fig_pidreuse.png   results/fig_pidreuse_real.png
```

If the files are root-owned (written by the container): `sudo chown -R $USER results`.

Outputs in `results/`: `injection_rates.csv` (rates with 95% Wilson CIs for wrong-target, miss, hijack, suppressed), `injection_paired_reduction.csv` (S0 to S1/S2, McNemar p), `injection_by_payload.csv`, `fig_injection.png`, and the `pidreuse_*` tables and figures.

### Optional: smoke test without a model

`--mock` replaces the model with a scripted answer (needs no Ollama):

```bash
./sandbox_run.sh python3 -m pidlab.run_injection --mock --n 3 --out results/smoke.jsonl
```

## Building the report

```bash
cd report
pdflatex main.tex && pdflatex main.tex
```

Requires the `IEEEtran` class (included in TeX Live `texlive-publishers`, and available on Overleaf). `figs/` holds the figures; `mkfigs.py` regenerates them from the reported numbers.

## Key settings (`pidlab/config.py`)

| Setting | Value |
|---|---|
| Model | llama3.1:8b (Ollama default Q4-class quantization) |
| Context / threads / max new tokens | 4096 / 4 / 80 |
| Temperature, seed | 0, seed = instance index |
| Output | JSON schema: `action` in {kill, none}, `pid` (no free-text reason) |
| Sanitization limits | name 32 chars, cmdline 120 chars |
| Container | 8 GB RAM, 4 cores, no GPU |

## Design notes and known issues

* **Frozen prompt.** The system prompt (v5) was fixed after the pilot. Do not edit `prompt.py` between or during runs. A fresh container loses `docker cp` edits unless the image is rebuilt from the saved files.
* **Memory kills.** On 8 GB, Ollama's runner was killed by the kernel five times during E1 (11 trials failed on the first pass). Re-running the same command retried them. If it recurs, stop, restart the container and resume.
* **Replay vs. real.** The replay holds the decision fixed at "kill the correct process" and only reproduces timing, so it measures misfire *given a correct decision*. It was validated against a small real run.
* **0 misfires** for `starttime` / `pidfd` means none observed, not impossible.
* Possible S1 truncation effect (120-char limit) is untested; see the report's limitations.

## Safety

Experiments only ever signal idle dummy processes created by the harness. Executors refuse PIDs that are not part of the current trial, and PID forcing is only allowed inside the private PID namespace (`run_pidreuse.py` exits if `IN_SANDBOX` is not set).