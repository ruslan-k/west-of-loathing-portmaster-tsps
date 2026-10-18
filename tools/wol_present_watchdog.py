"""Opt-in present-progress gate; neither PID liveness nor pixels imply progress."""
import math
import re

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
