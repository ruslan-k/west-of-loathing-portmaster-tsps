# External references reviewed: nx2android, and consult round 5

## nx2android (github.com/shirai91/nx2android)

Same class of software as this port: the game's own arm64 code runs natively, the
Switch services are stubbed by a host, and NVN is replayed on the platform's
graphics API. Three things there are worth copying, one is not.

Worth copying:

1. **Game profile as data only.** Their rule is explicit: core holds no title
   IDs, no game names, no per-game branches; a game that needs different
   behaviour gets a key in `dm/games/<title id>/game.tsv` (plus per-build
   `patches.py` and a shader table). This port does the opposite - a dozen
   `WOL_*`/`ZERO_*` environment switches whose meaning lives in code. A profile
   file per build would make every "what is this title actually running with"
   question answerable in one look.
2. **Per-build patch sets keyed to the build.** Their rewriter cuts live in
   `patches.py` per game profile, so an update cannot silently inherit offsets
   from the previous one - the exact failure this port already hit when the
   v23 `+32/+36` pixel fields moved.
3. **Offline shader bundle.** They translate shaders ahead of time into a bundle
   for the backend. This runtime announces `shader-catalogue=absent` for this
   title, i.e. every program is translated at run time.

Not reusable: their texture path requires hardware BC decoding and states plainly
that Adreno and Xclipse work while **Mali and PowerVR do not**. This device is
Mali, which is why the BC textures here still have no cheap path (88 BC objects on
the title alone).

## Consult round 5 (chatgpt-use, --model current)

Verdict on the question "what dominates a ~217 ms frame":

1. diagnostic overhead plus CPU-side work or blocking - most plausible;
2. GPU synchronisation, memory traffic and GL driver work - credible;
3. the 1080p-to-720p present pass - weakest explanation for this frame time.

Its single reversible experiment: a **release-mode frame-phase ledger** (`WOL_PHASE64=1`)
that records wall-clock and CPU time at four boundaries per frame - guest submit
interval, replay/finish waits, present CPU work, swap/scanout - accumulating in
memory and emitting one summary per 64 presents, reusing the existing
`NVN_PROFILE*` counters instead of adding a second profiling subsystem.

## What this port already measured in the same direction

`WOL_PRESENT_TICK` now carries `cpu_ms` per present (thread CPU time inside the
present call). Over run `budget-ctl2`: **13.0-28.7 ms per present**, against a
frame of ~165-217 ms at 4.6 f/s. So present CPU is roughly 7% of the frame, which
matches the consult's ranking: the present blit is not where the time goes.

Also checked: only 45 shader-related lines in a 120 s run and no compile storm, so
runtime shader translation is not happening per frame (it happens once, which is
still a startup cost the absent catalogue could remove).
