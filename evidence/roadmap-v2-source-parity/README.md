# Roadmap v2 §9.1: dtime8 source/overlay parity

The previously uncommitted sampler-zone diff is now included in `runtime/wol-adapter.patch`.
`source-parity.json` records the exact ELF SHA-256, overlay SHA-256 and all **199 native files**
(including subdirectories) compared against the frozen `wol-horizon-build-dtime8/source/native`.
No source mismatches or extra files. This does not claim a byte-reproducible ELF across compiler
paths/dates: it proves the overlay reconstructs the exact source used by the measured ELF.

Owner-local verification (no game data is read):

```
python3 tools/wol_overlay_verify.py \
  --base /mnt/external/Hermes/spikes/wol-switch/terminator-source \
  --reference /mnt/external/Hermes/spikes/wol-switch/wol-horizon-build-dtime8/source \
  --out /path/to/new-source-receipt.json
```

The source manifest is validated by `build_horizon.sh` before its overlay apply/build. Its existing
three positional arguments are restored GPL source, owner-generated image contracts, NEW output.
The public tree deliberately does not include the owner image or extracted executable segments.

New `wol_memory_ledger.py` records same-window PSS/SwapPSS/VmSwap/majflt, global VM/swap/CMA,
Mali contexts belonging to the exact PID, CPU/GPU clocks and periodic guest pool pagemap counts.
Each record has monotonic begin/end timestamps and PID reuse checks. These are sequential reads,
not atomic snapshots; duration is explicit. Driver commit, PSS, borrowed pool residency and CMA
are **not summed**. Missing GPU counters are unavailable, never zero.

Parser tests at the roadmap-defined acceptance seams use synthetic data only. They verify hex
commit-column decoding, exact PID context selection, missing counters, PID reuse, strict full
frame interval distributions (including P95), and overlay mismatch rejection. The existing CI
memory-test discovery includes these tests automatically. The runtime timer definitions are
unchanged from dtime8 (including the historical pp2 counter's two closes); timing zones overlap
by design: sm1 includes pp1..pp5 and must never be added to them.
