# TransferMemory backing copy: the cold 72 MiB owner, and the sparse-copy A/B

The per-VMA census left one fully-cold 72.0 MiB anonymous mapping unexplained
(0.1 MiB resident, 64.0 MiB swapped, zero-filled ends, present since startup in
every run). A bounded LD_PRELOAD logger (`tools/wol_hostmmap_shim.c`, default
OFF, logs host requests >=16 MiB with caller frames) named the owner in
`hmmap-b1`: the runtime services a guest TransferMemory request by mapping a
64 MiB anonymous backing and copying the whole region into it
(`memory.h transfer_create_locked`, call site `wol-horizon+0x53afc`, reached
from a signal-serviced guest call). The observed 72 MiB VMA is that 64 MiB copy
merged with an adjacent 8 MiB mapping. The copy is written once, then entirely
swapped out; the runtime already ships an opt-in gate for exactly this case.

## Pair

Same ELF `273b4638...`, UpRender 720 in both arms, only
`T2_TRANSFER_SPARSE_COPY` differs (0 vs 1); 87 present-progress checks per arm;
cleanup verified, no warnings. The candidate receipt prints:

```
T2_TRANSFER_SPARSE_COPY index=0 source=0x1078b00000 bytes=67108864 copied-bytes=0 skipped-bytes=67108864
```

The transferred region is entirely zero, so the sparse copy commits nothing.

## Measurements

- Cold 72.0 MiB VMA: control carries 64.1 MiB SwapPss in every phase (as in all
  five earlier runs); candidate has no >=64 MiB VMA with swap at all.
- SwapPss totals (MiB), control -> candidate:
  - startup 582.3 -> 557.5 (-24.8)
  - game-idle 526.4 -> 495.8 (-30.6)
  - precleanup 488.5 -> 454.8 (-33.7)
- Ledger accounting: the copy contribution is removed exactly, but other VMAs
  redistribute (guest arena +76.8, second arena -47.0 at precleanup), so the
  net deltas above are what this pair supports - not the 64 MiB sum.
- Presents over the identical route: 4882 vs 4877 (no regression signal).
- KMS frames: both arms bright, near-identical (world diff mean 0.1/255,
  <=0.1% pixels >16).

## Position

Nothing is promoted: the gate remains opt-in and default OFF; the device runs
ended clean and the save set stayed intact. This closes the "name the owner of
the cold 72 MiB" objective with a measured, reversible lever; zero-swap is
still not reached (454.8 MiB SwapPss remains, dominated by the guest arenas).
