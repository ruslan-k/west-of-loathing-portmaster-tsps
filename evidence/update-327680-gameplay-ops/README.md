# Inside real gameplay: 43 ms frame, three call classes hold 20 of the 27 ms replay

Scripted entry (see `update-327680-scripted-input`), 240 s, `COTM_REPLAY_PHASES=1`, ELF `3d02292e`.
Frame 2041 is a normal gameplay frame, past loading:

```
NVN_PROFILE frame=2041 elapsed-ms=43.128 replay-ms=26.894 present-ms=1.719

NVN_REPLAY_OP DrawArrays              6.838 ms   3.0 calls   2279 us/call
NVN_REPLAY_OP ReportCounter           6.794       2.0         3397
NVN_REPLAY_OP DrawElementsBaseVertex  6.206      72.8           85
NVN_REPLAY_OP Downsample              2.562       4.0          640
NVN_REPLAY_OP CopyTextureToTexture    1.649       1.0         1649
NVN_REPLAY_OP SetRenderTargets        0.447      19.0           24
```

- **DrawArrays is 2.28 ms per call across only three calls.** That is not draw setup - 73 indexed
  draws cost 85 us each, and these three unindexed ones cost 27 times more. They are almost
  certainly the full-screen passes (or a large vertex buffer rebuilt per frame).
- `ReportCounter` is 3.4 ms per call now, half what it was on the lighter scene, which again fits
  "time charged to the op" rather than work inside it.
- Replay 26.9 of a 43.1 ms frame; present 1.7.

## Gap to 30 fps

43.1 -> 33.3 needs **9.8 ms**. Two independent candidates are each about that size: the three
DrawArrays calls (6.8 ms) and the counter pair (6.8 ms). Neither has been attacked yet on this
baseline; the previous attempts were made on scenes that were not gameplay.
