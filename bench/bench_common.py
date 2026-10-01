"""Shared helpers for the pipen / snakemake benchmark drivers."""
import threading
import time


class TreeRSSSampler(threading.Thread):
    """Sample the summed RSS of a process tree from /proc."""

    def __init__(self, pid, interval=0.05):
        super().__init__(daemon=True)
        self.root = pid
        self.interval = interval
        self.peak_kb = 0
        self.n_samples = 0
        self._halt = threading.Event()

    @staticmethod
    def _snapshot():
        import os
        ppid, rss = {}, {}
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/stat", "rb") as fh:
                    data = fh.read()
                rp = data.rfind(b")")
                fields = data[rp + 2:].split()
                ppid[int(entry)] = int(fields[1])
                rss[int(entry)] = int(fields[21]) * 4096 // 1024
            except Exception:
                continue
        return ppid, rss

    def run(self):
        while not self._halt.is_set():
            try:
                ppid, rss = self._snapshot()
                children = {}
                for p, pp in ppid.items():
                    children.setdefault(pp, []).append(p)
                stack, seen, total = [self.root], set(), 0
                while stack:
                    p = stack.pop()
                    if p in seen:
                        continue
                    seen.add(p)
                    total += rss.get(p, 0)
                    stack.extend(children.get(p, ()))
                self.peak_kb = max(self.peak_kb, total)
                self.n_samples += 1
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self):
        self._halt.set()
        self.join(timeout=5)


def loadavg():
    return open("/proc/loadavg").read().split()[:3]
