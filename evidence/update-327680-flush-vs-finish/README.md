# `MOMO_SUBMIT_FINISH=0` (flush instead of finish): inconclusive

Existing switch, no build: end an executed list with `glFlush` instead of a full wait.

```
frame=121 elapsed 58.386  replay 40.071
frame=181 elapsed 35.974  replay 25.928
frame=241 elapsed 84.871  replay 23.972
frame=301 elapsed 119.271 replay 60.711
frame=361 elapsed 30.870  replay 23.398  present 1.742
```

Control on the same build with finish: 39.6-41.1 ms, replay 24.2-24.8 (run `stab-a1`).

- Replay did not move: 23.4-25.9 ms against 24.2-24.8. So the wait that the op ledger charges to
  the counter is **not** removed by dropping the finish, which weakens the "GPU drain" reading.
- Frame time is unusable as a comparison: 31, 36, 58, 85, 119 ms in one run. The scene changes
  underneath it (loads at 241/301), so this is not a matched pair and cannot show a win.

Verdict: no evidence either way. What it does rule out cheaply is the idea that the per-list
`glFinish` is the expensive wait - it is not, or removing it would have shown up in replay.

A real test needs a fixed scene (a save that always loads into the same room), then finish vs flush
on the identical view, three windows each.
