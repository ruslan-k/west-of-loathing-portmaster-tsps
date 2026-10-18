# Real GPU elapsed-query pass classifier — default-off

`WOL_GPU_TIMELINE=1` uses the device's **EXT_disjoint_timer_query**, one query pending at most, one pass every 120 frames, at most 64 shots. Results are retrieved only after availability, with GPU-disjoint rejection. No added finish/wait, no async renderer, no changed resource/sync semantics. Query identity is scoped to the existing producer context. Fake-driver regression exercises default-off, active/pending refusal, nonblocking availability and disjoint discard. Exact overlay build parity: **205 native files**.

Measured build `gputime1`, ELF `cfc3709f2addc357358af4fc5549097355f19c60e9c005219958e6122a942d12`. `WOL_ROMFS_COW=0`, upload skip/uniform cache OFF; periodic video checks unchanged. Same gulch save/corrected map section.

Findings:
- First six RT-switch ordinals often contain **zero draws and zero elapsed-query time**. This does NOT mean the frame has no GPU work.
- Sampled 1080p target pass ordinal 7: menu frame 840 **5.429 ms / 45 draws**; game frame 1800 **10.576 ms / 42 draws**.
- Adjacent ordinal 6: frame 1680 **10.296 ms / 0 draws**; map frame 2640 **6.583 ms / 1 draw**.
- Map ordinal 7, 960x540 target: frame 2760 **0.703 ms / 1 draw**.

These sparse tiler pass intervals include clear/resolve/scheduling effects and are **not additive isolated shader costs**; the zero-draw expensive pass requires attachment/clear audit, not deletion. Initial classifier rotates only ordinals 0..7 while the runtime has ~24 target switches/frame, so it is incomplete for total GPU attribution.

Existing telemetry additionally shows one real final wait per frame and three already-elided completion waits. Command submit has one list, not many independently finished lists. Therefore do not claim a simple per-list finish coalescing opportunity or enable MOMO_SUBMIT_FINISH=0 (that legacy switch publishes synchronous-list completion after only a flush).

Owned route, restored save hashes, zero analyzer GL errors and real Spruce recovery pass. This is instrumentation, not an FPS optimization. Full-frame performance overhead-on/off control and battle coverage are still open.
