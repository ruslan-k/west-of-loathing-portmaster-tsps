# Roadmap v2: semantic copy preflight and actual BC write census

## Decision: GPU sample redirection rejected

`WOL_COPY_AUDIT` is default-off and read-only apart from bounded diagnostic FBO/readback work. Its runs are deliberately **not FPS controls**. The CPU row copy and ordinary host upload remain unchanged.

- `v2-audit-gulch` and `v2-audit-saloon` used ELF `7788cf5ba009e6c292dbd3545de9cdd39f984684e9a103bf7caf3124310bb508` and owner section `a25600cebbd47376d9520d2c4d648463a78911224e8bc82e645dcab6223deb36`.
- Each captured 15 source audits. The initial unrendered source matched; all 14 later producer samples disagreed with the retained CPU copy. All sampled CPU copies were zero.
- The later `v2-postcopy-sand` run (ELF `2093c1a9018195ede915f0756229b8a5102997a8a77a73c481ec738e27e002d2`) also audited the destination: 15 producer samples and 15 destination samples. Every destination GPU image matched the zero CPU image. Thus this is **not merely stale CPU diagnostic data while the destination already contains the producer image**.
- The rotating GPU producer contains rendered art. Redirecting its sampler into the zero-image destination would change the current rendering contract. Sample-before-overwrite ordering cannot make unequal images equivalent. No GPU sample-redirection fast path is enabled or claimed.

This counterexample is sufficient to reject the proposed generic shortcut; it is not complete battle/late-game coverage. Raw owner pixels/cache payloads are not published; hashes, mismatch counts and actual KMS captures are.

## Corrected BC census

The old first-eight `WOL_BC_COPY` diagnostics were not a total census. The new bounded per-write trace observed **117 full-image level writes** in the gulch session and **106** in the saloon session. These include menu/startup and mip levels; they are **not** 117/106 unique scene-local textures. Texture 65 alone receives 11 mip-level writes. See `reconciled-summary.json` for texture IDs and totals, and each original `audit-summary.json` for exact dimensions/levels/content hashes.

No partial writes were observed in these two windows. This does not certify future immutability, render-target use or later scenes. The post-copy path therefore stays opt-in, single-level and complete-image only, with complete RGBA restoration on later unsupported writes.

## Screen coverage and limits

- Saloon `world.png` is a real basement interior, not a battle. Its requested `map.png` is a guide over that basement.
- The single post-copy `world.png` shows the gulch, the player and a snake. Its `map.png` shows the Boring Springs guide and one visible gulch marker.
- Action names are requests, not scene classifications. Movement, map and pause receipts are not physical-button or audio verification.
- Earlier `restored-menu.png` captures in the ledger/single test were actually black transient frames despite a live MainUI and successful kmsgrab exit. Do **not** use those as visible-menu proof. The probe now waits and rejects all-black RGB8 PNGs; final scene review remains separate.
- Owner-save hashes were restored, but battle, complete scene travel, late-game, physical audio/buttons and independent map-marker/reference parity remain open.

## Reproduce the report

```
python3 tools/wol_roadmap_analyze.py \
  evidence/roadmap-v2-copy-audit/gulch \
  evidence/roadmap-v2-copy-audit/saloon \
  evidence/roadmap-v2-postcopy-single \
  --out evidence/roadmap-v2-copy-audit/reconciled-summary.json
```

No speculative freeing, GPU alias substitution, global VM changes or production defaults were introduced.
