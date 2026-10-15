# pl:u shared-font service notes (native runtime)

West of Loathing's SDK initializes `nn::pl::detail::ISharedFontManager` (`pl:u`) on
the battle-scene autosave path: right after a 1920x1080 capture-sized texture the
game polls the font manager and maps a 16.25 MiB read-only shared region
(0x1100000 = the firmware's shared-font region size).

Wire facts measured on the device (do not re-derive):

* Command 1 is a load-state poll; the client retries forever on an empty reply.
  Answer it with `u32 1` as reply **data** (`GetLoadState`-style out).
* Command 4 (`GetSharedMemoryNativeHandle`-style) must answer with a **copy
  descriptor** carrying a handle that `svcMapSharedMemory` (0x13) can resolve: the
  runtime turns it into an `EP_SHARED` session whose `initialized` field indexes
  `shared_regions`. Move descriptors (the sm GetService shape) and raw data replies
  both made the client keep using handle 0.
* After the map the game iterates commands 3/2/1 with the font-type index as the
  first payload word and tolerates zeroed outputs.
* `shared_map` requires an exact size and permission match, so the region must be
  created as 0x1100000 / PROT_READ. `shared_create`'s bound is 32 MiB for it.
* svc 0x13 with handle 0 answers 0xE01 (no stop): keeps the failure observable and
  survivable while the reply shape is being tuned.

A/B knobs (env, single variable per run):

| env | default | purpose |
| --- | --- | --- |
| `WOL_PL_CMD1_REPLY` | `(unset)` = u32:1 | `u32:0`, `raw12`, `empty` |
| `WOL_PL_CMD4_REPLY` | `(unset)` = handle-copy | `handle-move`, `data`, `data8`, `handle-move+data`, `handle-copy+data`, `cycle` |

Tests: `tools/test_wol_pl_service.py <native overlay dir>` pins the source contract.
Evidence: `evidence/pl-service/`.
