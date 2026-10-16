# Ordinary launch: diagnostic input socket off by default

## Before / after, isolated launcher change

The earlier `roadmap-v2-ordinary-title` run passed runtime/save/menu cleanup but exposed `COTM_INPUT_DIAGNOSTIC=1` from the launcher itself. An empty harness override map did not establish a diagnostic-free launch.

The only launcher behaviour changed is the default for this input-injection flag: `1` → `0`. Explicit `COTM_INPUT_DIAGNOSTIC=1` still works for the controlled harness; physical-controller mapping, shader/UV/stencil defaults, readback cadence, runtime, scene section and VM configuration are unchanged. The default/off/explicit-on shell cases have a data-free regression test.

- Previous launcher SHA-256: `d24ebc83879eb1b64d7f9131c7967561ba2a97482b27c29e46df32f6e0e16cf3`.
- New launcher SHA-256: `fa30af838b22e01b7a5eeeb7c4f34c4b5eaf3f67c7a984eee0ba87ba90581f3a`.
- Device backup: `wol-switch/backups/launcher.d24ebc83879eb1b6.sh`; verified before activation. Installed bytes were independently re-read over fresh non-multiplexed SSH.
- Runtime remains `0cca40eca762c984acb53ecd7af1f56caba8b9756041406f154a07daad74b8fc`.
- Owner section remains `a25600cebbd47376d9520d2c4d648463a78911224e8bc82e645dcab6223deb36`.

## Actual ordinary-title run

The published helper launched the ordinary Spruce principal/standard-launch path without diagnostic environment overrides and without injected input. The effective runtime environment records `COTM_INPUT_DIAGNOSTIC=0`; ASTC/PBO/upload/copy/allocation diagnostic options are not enabled. The new runtime log contains no `HID_DIAGNOSTIC_SOCKET path=` receipt.

Independent KMS review shows the West of Loathing title, readable Continue/New Game/Options signs, Wynona Carson WANTED portrait, control box and scene art. The final screenshot shows the real Spruce Recents list, not a black transition. Exact owned-PID/start-time cleanup, owner-save hash restoration and the menu signal check pass with no cleanup warnings.

This title-only check does **not** prove Continue input, combat, physical buttons/audio, save/load, scene travel, all-body graphics parity, 30 FPS or a no-swap boot. No diagnostic-off FPS improvement is claimed. The process was not left running.
