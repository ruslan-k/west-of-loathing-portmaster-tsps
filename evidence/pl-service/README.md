# pl:u shared-font service — battle-scene stop fix (2026-10-15)

## Symptom

Entering the goblin battle (which autosaves) ended the run twice with fail-closed
stops in the SDK's shared-font service path:

* First crash, unhandled service:
  ```
  GET_SERVICE name=pl:u
  STOP status=UNIMPLEMENTED_SERVICE pc=sdk.text.seg+0xa9d94 detail=0x1
  WOL_RUNTIME_EXIT status=20
  ```
  (`evidence/pl-service/original-stop.txt`)

* After mapping pl:u to a stub that answered commands but returned no handle, the
  run stopped a step later — the client mapped **handle 0**:
  ```
  PL_SERVICE command=0x4 data=0x8
  SVC id=0x13 arg0x0=0x0 arg0x1=0x2db7004000 arg0x2=0x1100000 arg0x3=0x1   <- MapSharedMemory(0, .., 0x1100000, R)
  STOP status=INVALID_SESSION_HANDLE
  WOL_RUNTIME_EXIT status=24
  ```
  (`evidence/pl-service/cmd4-move-fail.txt`)

## Measured sequence (what the game does)

1. `GET_SERVICE name=pl:u` -> command 1 polled. With an **empty** reply the client
   retried 1333 times (black screen, audio only); answering `u32 1` in the reply
   data ("loaded") lets it proceed.
2. Command 4 asks for a shared-memory handle; the client then calls
   `MapSharedMemory(handle, addr, 0x1100000, R--)` — a 16.25 MiB read-only region.
3. The client accepts the handle only as a **copy descriptor** in the reply
   (`handle-copy`): with move-descriptor (the sm GetService shape) or with the
   handle as reply data it kept using handle 0.

Winning sequence (run `pl-fix-g`):
```
PL_CMD4_REPLY mode=0x0 cycle=0x1 source=cycle
PL_SHARED_CREATE size=0x1100000 id=0x2
PL_SHARED_HANDLE handle=0x436 mode=0x2
SVC id=0x13 arg0x0=0x436 arg0x1=0x837c04000 arg0x2=0x1100000 arg0x3=0x1
```
After the mapping the game iterates font-type queries (commands 3/2/1 with `In` word
0,1,2), the autosave completes (save hash changed), the battle screen renders and is
playable — `evidence/pl-service/battle-screen.png`.

## Fix (all opt-in reversible; runtime defaults changed)

* `ipc.h`: `pl:u` -> `EP_PL_STUB`; command 1 answers `u32 1` (env `WOL_PL_CMD1_REPLY`:
  default / `u32:0` / `raw12` / `empty`); command 4 creates one 0x1100000 R region
  (`shared_create`) and answers with an EP_SHARED session handle, default = copy
  descriptor (env `WOL_PL_CMD4_REPLY`: `handle-copy` default, `handle-move`, `data`,
  `data8`, `handle-move+data`, `handle-copy+data`, `cycle` A/B sweep). Other commands
  succeed with zeroed caller buffers. Requests are logged sampled with the first 12
  payload bytes.
* `memory.h`: `shared_create` bound raised 16 -> 32 MiB (0x1100000 = 16.25 MiB).
* `loader.c` svc 0x13: handle 0 answers `0xE01` instead of stopping (mapping with an
  unanswered handle stays survivable; every other invalid handle keeps the stop).

## Limits

* The region contents are **zero**: there is no system shared font. Text drawn with
  the platform font would be blank; the title's own fonts and the battle UI rendered
  normally in `battle-screen.png`.
* Reply-shape envs are single-variable A/B knobs, not user-facing options.
