#!/usr/bin/env python3
"""Direct-child watchdog for isolated WoL Switch bring-up probes."""
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def emit(message):
    print(message, flush=True)
    try:
        os.fsync(sys.stdout.fileno())
    except OSError:
        pass


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def identity(pid, expected, parent_pid):
    proc = Path("/proc") / str(pid)
    try:
        stat_text = (proc / "stat").read_text()
        comm, rest = stat_text.rsplit(")", 1)
        fields = rest.split()  # begins with field 3 (state)
        state = fields[0]
        ppid = int(fields[1])
        starttime = int(fields[19])  # proc stat field 22
        actual_comm = (proc / "comm").read_text().strip()
        exe = proc / "exe"
        exe_link = os.readlink(exe)
        same_exe = os.path.samefile(expected, exe)
    except (OSError, ValueError, IndexError):
        return None
    return {
        "pid": pid,
        "ppid": ppid,
        "parent_expected": ppid == parent_pid,
        "starttime": starttime,
        "state": state,
        "comm": actual_comm,
        "exe": exe_link,
        "same_exe": same_exe,
    }


def main(argv):
    if len(argv) < 5:
        emit("WOL_WATCHDOG_REFUSED reason=usage")
        return 64
    expected = Path(argv[1]).resolve()
    expected_hash = argv[2].lower()
    try:
        budget = int(argv[3])
    except ValueError:
        emit("WOL_WATCHDOG_REFUSED reason=invalid-budget")
        return 64
    command = argv[4:]
    if len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash):
        emit("WOL_WATCHDOG_REFUSED reason=invalid-elf-hash")
        return 64
    if not 1 <= budget <= 600 or not expected.is_file() or not command:
        emit("WOL_WATCHDOG_REFUSED reason=invalid-input")
        return 64
    observed_hash = sha256(expected)
    if observed_hash != expected_hash:
        emit(f"WOL_WATCHDOG_REFUSED reason=elf-hash-mismatch expected={expected_hash} observed={observed_hash}")
        return 73

    start = time.monotonic()
    child = subprocess.Popen(command, cwd=str(expected.parent), close_fds=True)
    parent_pid = os.getpid()
    deadline = start + budget
    snap = None
    for _ in range(40):
        if child.poll() is not None:
            break
        snap = identity(child.pid, expected, parent_pid)
        if snap is not None:
            break
        time.sleep(0.025)
    if snap is None:
        emit(f"WOL_WATCHDOG_REFUSED reason=child-identity-unavailable pid={child.pid}")
        # Popen owns this direct child; do not signal if identity could not be established.
        return child.wait()
    if not (snap["parent_expected"] and snap["same_exe"] and snap["comm"] == expected.name and snap["state"] != "Z"):
        emit(f"WOL_WATCHDOG_REFUSED reason=child-identity-mismatch snapshot={snap}")
        return child.wait()
    initial_starttime = snap["starttime"]
    emit(f"WOL_WATCHDOG_START pid={child.pid} starttime={initial_starttime} ppid={parent_pid} exe={snap['exe']} sha256={observed_hash} budget_seconds={budget}")

    while child.poll() is None and time.monotonic() < deadline:
        time.sleep(min(0.25, max(0.01, deadline - time.monotonic())))
    if child.poll() is not None:
        rc = child.returncode
        emit(f"WOL_WATCHDOG_EXIT reason=runtime-exit rc={rc} elapsed={time.monotonic()-start:.3f}")
        return rc if rc >= 0 else min(255, 128 + (-rc))

    snap = identity(child.pid, expected, parent_pid)
    if not (snap and snap["parent_expected"] and snap["same_exe"] and snap["comm"] == expected.name and snap["starttime"] == initial_starttime and snap["state"] != "Z"):
        emit(f"WOL_WATCHDOG_REFUSED reason=deadline-identity-mismatch snapshot={snap}")
        return child.wait()
    emit(f"WOL_WATCHDOG_DEADLINE action=TERM pid={child.pid} starttime={initial_starttime}")
    child.terminate()  # direct unreaped child; no unrelated PID can be selected
    try:
        rc = child.wait(timeout=5)
        emit(f"WOL_WATCHDOG_EXIT reason=deadline-term rc={rc} elapsed={time.monotonic()-start:.3f}")
        return 124
    except subprocess.TimeoutExpired:
        snap = identity(child.pid, expected, parent_pid)
        if not (snap and snap["parent_expected"] and snap["same_exe"] and snap["comm"] == expected.name and snap["starttime"] == initial_starttime and snap["state"] != "Z"):
            emit(f"WOL_WATCHDOG_REFUSED reason=kill-identity-mismatch snapshot={snap}")
            return child.wait()
        emit(f"WOL_WATCHDOG_DEADLINE action=KILL pid={child.pid} starttime={initial_starttime}")
        child.kill()
        rc = child.wait(timeout=5)
        emit(f"WOL_WATCHDOG_EXIT reason=deadline-kill rc={rc} elapsed={time.monotonic()-start:.3f}")
        return 124


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
