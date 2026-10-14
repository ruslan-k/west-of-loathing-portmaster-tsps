# Late-evening investigation: why test sessions kept dying (2026-10-14 ~23:30-00:10)

## Root cause found: low battery triggers the smart profile that offlines CPUs
- Device battery: 16-17%. In this state the system's smart power profile hotplugs CPU
  cores offline (dmesg: psci: CPU0/1/2/3 killed; "process ... no longer affine to cpuN")
  and the device also enters sleep (screen = clock, all cores off).
- The wol-horizon runtime pins its threads to cores; when a pinned core disappears the
  wrapper aborts: log line "STOP status=HOST_THREAD_AFFINITY_FAILED pc=sdk.text.seg+0x8e8d8".
- Symptoms this caused: game dies ~15-25s after launch; my automated sessions captured
  the SpruceOS menu / standby clock instead of game frames; the "bird cage was fine then
  broke on re-entry" report also matches the standby/sleep pattern, not a rendering bug.
- Conclusion: no further device testing until the device is charged. The afternoon
  sessions (battery >60%) ran fine with the same builds.

## Also discovered (session mechanics)
- The correct launch chain is UI -> principal.sh -> /tmp/cmd_to_run.sh -> standard_launch.
  Under the principal the UI-restore only happens after the command exits; watchdog
  duplicates seen (buttons/menubutton watchdogs x2 from the boot).
- My earlier pgrep -f 'wol-horizon' liveness check matched its own shell (false "alive").
  Use exact comm match (pgrep -x wol-horizon) or the /proc scan.
- The port launcher now carries a TEMP-DIAG block (COTM_INPUT_DIAGNOSTIC + the rect
  trace for the player/cage zones) so any launch path (UI or scripted) has diagnostics.

## Verified this round (before the battery issue)
- WANTED poster figure: complete stick body restored by the f191 halfgt revert
  (title-243-wanted-poster-complete.png).
- Room: bed + gramophone back under build-243 (room-243-bed-gramophone-back.png).
- Still open: bird cage (batched pieces), farm player under 243, top-right icon strip.
