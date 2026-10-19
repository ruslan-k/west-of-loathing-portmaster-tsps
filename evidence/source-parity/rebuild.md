
## Full rebuild verification (roadmap §18.2 step 1)

- Baseline: `upstream-source` — `sha256sum -c runtime/source-manifest.sha256` → **435/435 OK,
  0 failures** (nothing added, nothing customized in place).
- Recipe: the documented container `pmjs-arm64-spruce-local:20261002-gcc10` with the baseline
  mounted read-only at `/reference` and the owner image read-only at `/image`;
  `bash build_horizon.sh /reference /image /spike/wol-horizon-build-parity0` into a previously
  absent output directory.
- Patch application: `git apply --check` **OK**, `git apply` OK; the nxaudio providers compiled;
  the native AArch64 compile and link succeeded with the full object/link log retained.
- New ELF `484275f7d011079b9f090332df609f3bc0fade0a57a9c73a5c39cd52e43751bb`, 1,974,840 bytes.
  Deployment receipt for comparison:
  `b60057eaeafa738e9b48cf2b68b356545ee5ffde2c57bb84a5da5722e5935158`, 1,974,880 bytes. The 40-byte
  difference is exactly the documented caveat that exact bytes depend on compiler/source paths;
  a byte-identical reissue is **not** promised by the recipe.
- Feature presence matrix — marker strings present in **both** the fresh rebuild and the deployed
  receipt: `WOL_UPRENDER_720`, `WOL_UPRENDER_CONFIG`, `WOL_UP_CODE_IDENTITY`,
  `WOL_UP_COMPONENT_SETTINGS`, `T2_TRANSFER_SPARSE_COPY`, `NVN_COMMAND_RECORD_SIZE`,
  `WOL_ALLOC_TRACE`, `T2_MEMORY_FLOOR_MIB`, `COTM_INPUT_DIAGNOSTIC`, `WOL_ROMFS_COW`,
  `T2_GUEST_ZRAM`, `NVN_COMMAND_ARENA_OVERLAP`. (`WOL_RT720_MAIN_SHA256` is a compile-time macro
  and is absent as a string in both, by design.)

**Consequence:** the published baseline plus the published overlay now build a feature-equivalent
adapter with the documented recipe. Any ELF produced this way is a *new* artifact: per §18.2 step 6
it must re-run the acceptance basis instead of borrowing the deployed hash's results.
