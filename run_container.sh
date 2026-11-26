#!/usr/bin/env bash
# Emulated 8 GB / 4-core CPU-only defender box on a 16 GB host. Linux (or WSL2 with enough .wslconfig memory).
set -e
docker build -t pidlab .
mkdir -p results
docker run -it --rm --name pidlab \
  --memory=8g --memory-swap=8g --cpuset-cpus=0-3 \
  --cap-add SYS_ADMIN --security-opt apparmor=unconfined --security-opt seccomp=unconfined \
  -v "$PWD/results:/work/results" -v pidlab_models:/root/.ollama \
  pidlab bash -c 'ollama serve >/tmp/ollama.log 2>&1 & sleep 5; exec bash'
