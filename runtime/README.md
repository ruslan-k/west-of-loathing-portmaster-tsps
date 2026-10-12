# GPL runtime overlay

The owner-supplied Terminator runtime and nxgl source patches reconstruct the 435-file baseline pinned by `source-manifest.sha256`. Their source provenance is documented in `../docs/terminator-source.md`.

`wol-adapter.patch` is our GPL-3.0 modification overlay. The build applies it to a fresh verified baseline copy; no third-party ELF, owner NSO/RomFS or generated shader bytes are included. The overlay reaches shader capture only: it is not a playable port. See `../docs/tsps-horizon-adapter.md`.
