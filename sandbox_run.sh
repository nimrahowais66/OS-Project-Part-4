#!/usr/bin/env bash
# Runs a command inside a private PID namespace (harness becomes PID 1 there). Ollama stays outside,
# reached over localhost. Usage: ./sandbox_run.sh python3 -m pidlab.run_pidreuse ...
exec unshare --pid --fork --mount-proc env IN_SANDBOX=1 "$@"
