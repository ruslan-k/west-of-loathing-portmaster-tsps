"""Opt-in present-progress gate; neither PID liveness nor pixels imply progress."""
import math
import re
import subprocess


def phase_budget(settled, settled_s, transition_s):
    """Explicit opt-in policy; action names alone never establish settled gameplay."""
    if not isinstance(settled,bool) or not all(math.isfinite(v) for v in (settled_s,transition_s)):
        raise ValueError('finite budgets and an explicit settled boolean required')
    if settled_s==transition_s==0:return 0
    if not 5<=transition_s<=30 or not (settled_s==0 or 5<=settled_s<=transition_s):
        raise ValueError('settled budget must be 5..transition; transition must be 5..30s')
    return settled_s if settled and settled_s else transition_s


def run_monitored(command,check,*,popen=subprocess.Popen):
    """Check progress every second even while an input/capture helper waits.

    On error stop only the child spawned here. Runtime cleanup remains with its
    exact PID/start-time owner; this helper never signals the runtime or MainUI.
    """
    child=popen(command)
    try:
        while True:
            try:code=child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                check();continue
            check()
            if code:raise subprocess.CalledProcessError(code,command)
            return
    finally:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill();child.wait(timeout=3)

class PresentationStall(RuntimeError):
    def __init__(self, observation):
        self.observation=observation
        super().__init__('presentation progress missing/stale: '+str(observation))


def require_progress(text, now_ns, budget_s):
    if not math.isfinite(budget_s) or not 0<budget_s<=60:
        raise ValueError('bounded positive presentation budget required')
    matches=re.findall(r'MOMO_FRAME frame=(\d+) ns=(\d+)',text)
    if not matches:
        raise PresentationStall(dict(frame=None,ns=None,age_s=None,reason='no present marker in bounded log tail'))
    frame,ns=map(int,matches[-1]);age=(now_ns-ns)/1e9
    if age<0:
        raise ValueError('present timestamp is in a different/future clock domain')
    observation=dict(frame=frame,ns=ns,age_s=age)
    if age>=budget_s:
        raise PresentationStall(observation)
    return observation
