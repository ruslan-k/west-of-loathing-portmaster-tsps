# Source-parity reconstruction (§18.2 step 1-2) — 2026-10-19

Roadmap §18.1 listed a **P0 source parity** concern: `runtime/source-manifest.sha256` pins
`native/memory.h` at `3db35657…`, while the sparse fixture/test referenced a frozen
**post-change** `68974762…`, and `runtime/wol-adapter.patch` appeared to contain no
`T2_TRANSFER_SPARSE_COPY` implementation. The audit therefore could not decide whether the
published baseline + public overlay can reproduce the measured sparse-enabled ELF.

## Method (isolated, no device, no writes outside scratch)

1. Copied the manifest-pinned baseline tree `native/` (the `upstream-source` tree whose
   `memory.h` hashes to the pinned `3db35657d69248a2f5885996391dd8534d577cc22ee4365ca96c25ae629f0923`)
   into a fresh scratch tree with its own `git init`.
2. `git apply --check runtime/wol-adapter.patch` then `git apply` — both succeeded cleanly.
3. Byte-compared the patched tree against the tree that actually produced the measured
   acceptance ELF (`wol-horizon-build-allocfix16/source/native`, ELF
   `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`).

## Result

- `git apply --check` and `git apply`: **OK** (no fuzz, no rejects).
- `diff -rq` patched-baseline vs measured-build source tree: **0 differences** (42 files
  changed/added by the overlay, all matching; `framework/` also 0).
- The patched `memory.h` hashes to **`68974762e5551fbc57f6753e1c9c311488bcf2283642806e35051778be96ed8b`**,
  i.e. exactly the frozen post-change header the fixture test refers to.
- The sparse implementation is present in the **pinned baseline** itself
  (`upstream-source/native/memory.h` contains `T2_TRANSFER_SPARSE_COPY`, 2 occurrences), so
  the overlay not mentioning the flag is expected: the overlay does not add it, it preserves it.

## Conclusion

The §18.1 **P0 source-parity gap is closed**: manifest-pinned baseline + published overlay
reproduces the measured sparse-enabled native source tree **exactly** (tree-level byte parity,
0 unexplained differences). No isolated sparse diff needs to be reconstructed; nothing must be
added to the GPL overlay for parity.

Remaining from §18.2 (not covered here, needs the owner-local cross toolchain and a device
rollout): a **fresh full rebuild** from that tree with `build_horizon.sh`, then source-parity
report of the *rebuilt* ELF vs the pinned device ELF, and the launcher-default synchronisation
commit with default/override tests.
