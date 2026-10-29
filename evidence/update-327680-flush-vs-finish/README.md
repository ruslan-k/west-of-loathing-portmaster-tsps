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

## Matched frame indices, finish vs flush

Six frame numbers appear in both logs; comparing the same frame index rather than the same wall
clock:

```
frame   control (finish)        flush
 61     432.6 ms / replay 35.0  460.4 / 60.8
121      36.9 / 28.3             58.4 / 40.1
181      49.8 / 36.8             36.0 / 25.9
241     109.5 / 24.6             84.9 / 24.0
301     190.6 / 102.4           119.3 / 60.7
361      33.2 / 23.3             30.9 / 23.4
```

At the only frame where both runs are past loading (361) the two are identical: 33.2/23.3 against
30.9/23.4. The other rows are dominated by load spikes that do not coincide.

**Verdict: flush and finish are a wash here.** Combined with the run-to-run spread (frame 361 is
33.2 ms in this control and 39.8 ms in the same run's later windows), the conclusion is that the
frame is scene-bound and the current measurement method cannot separate a 5 ms change from noise.

## Blocked on a deterministic scene

Every remaining question - is the wait a drain, does flushing help, would 720p work - needs the
same view twice. That means a save that always loads into the same room, plus scripted input to
reach it, checked by the frame's own draw count (`draws-mean`) rather than by wall time.
