"""Three response executors. Each delivers a DIFFERENT signal number purely as a tag, so one
trial can evaluate all three on the same decision (paired design) and the dummies' logs tell
us which executor hit which process.  naive=SIGUSR1, starttime=SIGUSR2, pidfd=SIGTERM."""
import os, signal
from .sandbox import read_starttime

SIG = {"naive": signal.SIGUSR1, "starttime": signal.SIGUSR2, "pidfd": signal.SIGTERM}
TAG = {int(v): k for k, v in SIG.items()}

def naive(pid, registry):
    # SAFETY: only PIDs that currently belong to a dummy of this trial can ever be signalled.
    if pid not in registry: return "blocked_unknown_or_gone"
    try: os.kill(pid, SIG["naive"]); return "sent"
    except ProcessLookupError: return "gone"

def starttime(pid, entry, registry):
    if entry is None: return "refused_unknown"
    try: cur = read_starttime(pid)
    except (FileNotFoundError, ProcessLookupError): return "refused_gone"
    if cur != entry["starttime"]: return "refused_mismatch"
    try: os.kill(pid, SIG["starttime"]); return "sent"
    except ProcessLookupError: return "gone"

def pidfd(entry):
    if entry is None: return "refused_unknown"
    try: signal.pidfd_send_signal(entry["pidfd"], SIG["pidfd"]); return "sent"
    except ProcessLookupError: return "refused_gone"

def read_hits(sigdir):
    hits = {k: [] for k in SIG}
    for fn in os.listdir(sigdir):
        if fn.endswith(".log"):
            for line in open(os.path.join(sigdir, fn)):
                tag = TAG.get(int(line))
                if tag: hits[tag].append(fn[:-4])
    return hits
