from . import sandbox as sb

def snapshot(procs, cpu_by_role):
    """Real identity data comes from /proc; CPU% is scenario-assigned (dummies stay idle so
    they do not disturb the inference-latency measurement)."""
    rows = []
    for role, pr in procs.items():
        rows.append(dict(role=role, pid=pr.pid, name=sb.read_comm(pr.pid),
                         cmdline=sb.read_cmdline(pr.pid), ppid=sb.read_ppid(pr.pid),
                         cpu=cpu_by_role[role], starttime=pr.starttime, pidfd=pr.pidfd))
    rows.sort(key=lambda r: -r["cpu"])                   # like `top`
    return rows
