"""Process helpers: spawn dummies, read /proc identity, force PID reuse, pidfds."""
import os, sys, time, subprocess, threading

DUMMY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dummy_proc.py")
_spawn_lock = threading.Lock()

def _stat_fields(pid):
    with open(f"/proc/{pid}/stat") as f:
        return f.read().rsplit(")", 1)[1].split()       # index 0 == field 3 (state)
def read_starttime(pid): return int(_stat_fields(pid)[19])   # field 22, clock ticks since boot
def read_ppid(pid):      return int(_stat_fields(pid)[1])
def read_comm(pid):
    with open(f"/proc/{pid}/comm", errors="replace") as f: return f.read().rstrip("\n")
def read_cmdline(pid):
    with open(f"/proc/{pid}/cmdline", "rb") as f: parts = f.read().split(b"\0")
    parts = [p.decode("utf-8", "replace") for p in parts if p != b""]
    return " ".join([parts[0]] + parts[2:])              # hide our own script path (index 1)

class Proc:
    def __init__(self, role, popen):
        self.role, self.popen, self.pid = role, popen, popen.pid
        self.starttime = read_starttime(self.pid)
        self.pidfd = os.pidfd_open(self.pid)             # opened at detection time
    def kill(self):
        try: self.popen.kill()
        except ProcessLookupError: pass
        self.popen.wait()                                # reap -> PID becomes reusable
    def close(self):
        try: os.close(self.pidfd)
        except OSError: pass

def spawn(role, comm, argv0, args, sigdir):
    env = {"ROLE": role, "COMM": comm[:15], "SIGDIR": sigdir, "PATH": os.environ.get("PATH", ""),
           "PYTHONHOME": sys.base_prefix}
    p = subprocess.Popen([argv0, DUMMY, *args], executable=os.path.realpath(sys.executable),
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ready, t0 = os.path.join(sigdir, role + ".ready"), time.time()
    while not os.path.exists(ready):
        if p.poll() is not None or time.time() - t0 > 10:
            raise RuntimeError(f"dummy {role} failed to start")
        time.sleep(0.005)
    return Proc(role, p)

def spawn_with_pid(target, role, comm, argv0, args, sigdir, tries=5):
    """Force the kernel to hand out `target` as the next PID (needs CAP_SYS_ADMIN in a
    private PID namespace; /proc/sys/kernel/ns_last_pid). Returns Proc or None."""
    for _ in range(tries):
        with _spawn_lock:
            try:
                with open("/proc/sys/kernel/ns_last_pid", "w") as f: f.write(str(target - 1))
            except OSError:
                return None
            pr = spawn(role, comm, argv0, args, sigdir)
        if pr.pid == target: return pr
        pr.kill(); pr.close()
    return None
