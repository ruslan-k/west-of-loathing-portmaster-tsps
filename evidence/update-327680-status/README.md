# Where the optimisation stands

Baseline (release, scripted entry into gameplay, ELF `332b741a`):

```
frame 42.1-43.1 ms   replay 25.9-26.9   present 1.7   draws-mean 71-73
DrawArrays 6.84 (3 calls, 7 vertices each: 1280x720 x2, 1920x1080 x1)
ReportCounter 6.79 (2 calls)   DrawElementsBaseVertex 6.21 (72.8 calls)
```

Gap to 30 f/s: **9.8 ms**.

## Closed, with evidence

- uniform cache: wash (7.92-8.51 vs 7.78-8.47 on the same band);
- flush instead of finish (`MOMO_SUBMIT_FINISH=0`): replay unchanged;
- asynchronous frame (`COTM_ASYNC_FRAME=1`): fails closed, programs unqualified;
- storage-scale / UpRender: black screen or non-engaging;
- probe-path input: was missing `SDL_GAMECONTROLLERCONFIG`; fixed, scripted entry works.

## What is left

The two remaining candidates are the 1920x1080 seven-vertex pass and the counter pair. The counter's
cost is charged as "time since the previous op", and dropping the per-list finish did not move it, so
it behaves like a real GPU wait rather than work inside the call. If so, the only lever left is GPU
work - the 1080p intermediate - and that is a renderer change with a black-screen history.

Decision needed before any further runs: attempt the 1080p pass, or accept ~24 f/s in the heavy
scene as this build's level.
