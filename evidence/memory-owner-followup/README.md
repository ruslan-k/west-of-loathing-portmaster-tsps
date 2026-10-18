# M5 SDK owner and compatible-host-view follow-up

Memory-only owned route `memoryowners2`, ELF `87948d2c38efe0471049bb278705d9d3cd2f0904415a29fdf9c6dc28a58f4537`, corrected map section unchanged. Four exact-ELF descriptor/smaps snapshots, no pagemap scans or memory changes. Snapshot costs **380–774 ms**: these are **not clean FPS measurements**.

The 144,392,040-byte corrected core read starts **32 bytes inside** SDK allocation `0x1047752000`, requested extent `0x8a34000`. It is observed reused as the output of an additional 11,633,735-byte read. No matched SDK free and no overlapping NVN pool is recorded in this cycle. This is allocation ownership evidence, NOT proof of inactive/free Unity subobjects.

At game-idle 116 live texture descriptors have 153.94 MiB calculated host-image extents; map has 214 descriptors/187.34 MiB. **No exact compatible layout/backing tuple with different host names** is found in the game snapshot; no new storage-sharing optimization is justified by that narrow census. Row-pitch/format/generation/write hazards still prohibit merging arbitrary overlapping views.

The allocator trace is complete for its bounded large-SDK scope (93 allocation/free events), not a full native heap/free-list model. Source/destination page offsets differ, so direct source-file mmap is not a valid alternative read. A separate shifted-backing COW experiment is documented in `../romfs-cow/`; never infer permission to free or MADV_DONTNEED this retained arena.

Original save hashes restored and physical Spruce KMS cleanup captured. Owner save/content bytes are not published.
