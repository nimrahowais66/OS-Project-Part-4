"""Central settings. Report every value here in the paper (RQ: reproducibility)."""
import os
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
NUM_CTX      = int(os.getenv("NUM_CTX", "4096"))
NUM_THREAD   = int(os.getenv("NUM_THREAD", "4"))      # keep == docker --cpuset-cpus size
NUM_PREDICT  = 80
KEEP_ALIVE   = "60m"
MOCK_LATENCY = float(os.getenv("MOCK_LATENCY", "0.3"))                                    # seconds, only for --mock smoke tests
# models: all Ollama default tags are Q4-class quantisations (Q4_K_M / Q4_0)
MODELS = ["tinyllama", "llama3.2:3b", "llama3.1:8b"]

REASON = os.getenv("REASON", "0") == "1"   # 0 = no free-text "reason" field -> fewer output tokens -> lower latency
