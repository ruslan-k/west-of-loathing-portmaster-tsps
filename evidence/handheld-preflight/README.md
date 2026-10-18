# Handheld-only preflight — actual existing AM contract

Baseline source eafd2e7; build `mode1`, ELF `c8de9ffc0333507e8ff69a8fd92674696b98d68c3a0e8ece57fad05df4cfd05b`.

The inherited AM dispatcher already returns operation mode **0 in one byte** and performance mode **0 in four bytes**. Extracting those existing replies into a constant-only helper does not add a TV mode or change rendering policy. A compiled regression exercises both ABI widths, unsupported commands, immutable policy and default-off/bounded tracing. No selector is read.

Read-only `WOL_MODE_TRACE=1` captured real domain AM requests 0, 1, 9 and 6. Two performance replies were Normal/0, 4 bytes. **No command 5, command 60 or VI ListDisplays call was observed in this window.** The absence of a call is not a fabricated 720p AM reply: command 60 remains unsupported, not speculatively implemented. Actual texture allocations still include **1920×1080**; output captures are 1280×720. Existing handheld policy is not the missing resolution switch demonstrated here. Inspect guest Unity RT/quality configuration next, not a docked toggle.

The controlled route reached the same gulch save, map and pause. `mode1/receipt.json` verifies restored save hashes and exact owned-process cleanup. `restored-menu.png` shows Spruce. No FPS/memory win claimed. Owner payloads and saves are not published.
