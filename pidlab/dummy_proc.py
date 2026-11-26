#!/usr/bin/env python3
"""Idle stand-in process. Does nothing harmful: it only RECORDS signals it receives
(never exits on them) so the harness can see exactly who was hit by which executor."""
import os, signal, time, ctypes
role, comm, sigdir = os.environ["ROLE"], os.environ["COMM"], os.environ["SIGDIR"]
ctypes.CDLL(None).prctl(15, comm.encode()[:15], 0, 0, 0)      # PR_SET_NAME -> /proc/<pid>/comm
def _h(signum, frame):
    fd = os.open(os.path.join(sigdir, role + ".log"), os.O_WRONLY | os.O_APPEND | os.O_CREAT)
    os.write(fd, f"{signum}\n".encode()); os.close(fd)
for s in (signal.SIGTERM, signal.SIGUSR1, signal.SIGUSR2):
    signal.signal(s, _h)
open(os.path.join(sigdir, role + ".ready"), "w").close()
while True:
    time.sleep(0.2)
