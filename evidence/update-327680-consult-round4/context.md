# WOL v327680 on TSPS — where we are, what to do next

Repo: https://github.com/ruslan-k/west-of-loathing-portmaster-tsps (branch main, HEAD 9350973a)
Historical context to read there: `evidence/uprender-owner/README.md`,
`docs/optimization-roadmap.md` §15, `evidence/guest-rt720/README.md`,
`evidence/update-327680-rt-origin-title/`, `evidence/update-327680-gameplay-entry/`.

## Hardware / platform
Anbernic-class ARM64 handheld (TrimUI Smart Pro), 963 MB RAM + swap, Mali-G57,
1280x720 panel, SpruceOS. Game: West of Loathing, Switch build, update v327680,
IL2CPP metadata v24, native Horizon/NVN runtime built in this repo.

## Proven by measurement (this port, update build)
1. Guest presents a 1920x1080 source that the host crops to 0,0,1280,720.
2. `UnityEngine.Screen::get_width/height` return 1280x720 inside the guest at the
   UpRender call site (measured), so the 1080p is not derived from Screen there.
3. RT-origin census joined to host allocations by guest object pointer: on the
   title, 386-438 textures, exactly **four** 1920x1080 (three swapchain images +
   one depth). No dynamic 1080p camera render targets at the title.
4. The v23 profile of this same port got **24.0 -> 32.6-33.9 presents/s** by
   rewriting `UpRender.forceWidth/forceHeight` (+32/+36) before
   `RenderTexture::.ctor`; nine *dynamic* 1080p targets became 720p while the
   four initial swapchain textures stayed 1080p. In v24 those field offsets are
   different: at +0x20 the component holds {16,9} (aspect), not pixels.
5. Constant-based 720p (11 guest instructions in the dimension-query function,
   `WOL_GUEST_RT720`) gave **zero** FPS change in v23 and was rejected.
6. Baseline FPS on the title: 25.5 presents/s, 39.2 ms/frame; 30 FPS needs
   <=33.3 ms, i.e. ~5.9 ms less per frame.
7. Memory: unique physical ~582 MB peak; memcpy-style duplication 132-137 MB;
   CMA must stay >=65 536 kB (lowering it yields 0 presented frames).

## Blocker right now
The device is currently powered off / wedged and awaiting a physical power-cycle,
so nothing can be measured. Gameplay entry is unproven: the owner says it takes
**several A presses**, and single/double taps of BTN_SOUTH(304) and BTN_EAST(305)
left the title on screen. RT tracing needs `T2_MEMORY_FLOOR_MIB=16` or it stops
at 36 s; `probe 600 / watchdog 780` is refused as invalid input.

## What I need from you
One reversible experiment to reach >=30 presents/s in gameplay, not a list of
ideas. Specifically: how to locate `forceWidth/forceHeight` in metadata v24
without guessing offsets, and what to instrument so a single run proves both the
field identity and the target-size change. State what is proven vs hypothesis,
and name the three most likely misconceptions in the above.
