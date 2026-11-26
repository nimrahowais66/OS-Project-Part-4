"""Run inside ./sandbox_run.sh before any experiment."""
import os, sys, tempfile, requests
from . import sandbox as sb, config
ok = lambda b: "OK " if b else "FAIL"
print(ok(hasattr(os, "pidfd_open")), "pidfd_open available (Python>=3.9, kernel>=5.3)")
print(ok(os.environ.get("IN_SANDBOX") == "1"), "running inside private PID namespace (IN_SANDBOX=1)")
sd = tempfile.mkdtemp()
a = sb.spawn("a", "probe", "/usr/bin/probe", ["--x"], sd); print(ok(sb.read_comm(a.pid) == "probe"), "dummy spawn + comm", sb.read_cmdline(a.pid))
pid = a.pid; a.kill(); a.close()
b = sb.spawn_with_pid(pid, "b", "probe2", "probe2", [], sd)
print(ok(b is not None), "forced PID reuse via ns_last_pid (needs --cap-add SYS_ADMIN)")
if b: b.kill(); b.close()
for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
    if os.path.exists(p): print("INFO memory limit:", open(p).read().strip(), "(expect 8589934592)")
try: print(ok(requests.get(config.OLLAMA_URL, timeout=3).ok), "Ollama reachable")
except Exception as e: print("FAIL Ollama:", e)
print("INFO nproc:", os.cpu_count(), "NUM_THREAD:", config.NUM_THREAD)
