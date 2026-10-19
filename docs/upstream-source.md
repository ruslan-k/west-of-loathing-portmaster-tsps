# Upstream source reference

The owner supplied a separately supplied GPL-3.0 source archive. Its release source documentation identifies version 1.0.16 and runtime source commit `803b22b445c247c53849cef064f2b814d4ba3c24`; framework commit `7c0c07d795e1a7ede88b6a57c98756a8d01dddec`.

The archive contains `sources/runtime-source.patch`, `sources/nxgl-source.patch`, `sources/SOURCE-MANIFEST.json`, build recipes, component sources and a GPL-3.0 license. It is not necessary to recover those sources from decompiled pseudocode.

Reconstruction was performed in an empty local directory using `git apply` for both patches. Every one of the 435 manifest entries was checked against the reconstructed file's SHA-256: zero mismatches. Whitespace warnings from upstream patch application were retained without modifying the pinned source.

Runtime ELF observations: AArch64, 2,764 symbol-table entries, DWARF sections `.debug_info`, `.debug_line`, `.debug_loc`, `.debug_ranges` and other debug metadata. Linked host dependencies include system SDL2, EGL/GLESv2, libm, zlib, libdl, libpthread and libc.

Relevant native source boundaries:

- `loader.c`: guest mapping, system-call dispatch, memory budget, separate virtual TLS registers, startup.
- `threading.h`: host pthread backing, per-thread guest state and alternate signal stacks.
- `ipc.h`: bounded named-port access, handles, CMIF/TIPC parsing, service manager admission and response layout.
- `filesystem.h`, `save.h`, logging/audio/HID/service helpers.
- NVN replay/texture/shader/queue headers and host NXGL integration.

Our minimal CMIF SM Initialize implementation was checked against the wire layout and validation rules in `native/ipc.h` (GPL-3.0). It is deliberately narrower: unsupported services stop explicitly. None of the upstream game's NVN optimizations, shader catalogue or fixed game addresses has been adopted as a validated WoL implementation.

The source includes a 1536 MiB game memory budget and large address-space conventions. These are not suitable defaults to copy blindly to a 963 MiB handheld. Host/system state and guest ABI declarations must be distinguished from measured resident memory.

The reference source/package and game-derived files remain outside this repository. Do not commit owner images or original runtime binaries. Further extracted source reuse must preserve the upstream license and provenance.
