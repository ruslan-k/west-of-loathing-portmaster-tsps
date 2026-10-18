# GPU frequency experiment — effective clocks, not requested policy

All arms use `uploadskip1` with upload skip and uniform cache OFF, same owner save and corrected map section. Temporary policy changes are restored and independently read back.

- `gpu600a`: setting governor before launch was overwritten by Spruce; game samples remained **150 MHz**. **Invalid as a 600 MHz performance arm**.
- `gpu600b`: applying performance governor after process appearance held **600 MHz only in 5 startup samples**, then **150 MHz** throughout menu/game. Again **invalid as a sustained 600 MHz arm**. Neither result establishes frequency neutrality.
- `gpumin600`: only the minimum frequency was raised to the existing **600 MHz maximum** after the runtime appeared. All recorded phases, including all 15 `game-idle` samples, actually observe **600 MHz**. The wrapper restores min=150 MHz, max=600 MHz, governor=simple_ondemand; both receipt and fresh sysfs read confirm restoration.

Valid `gpumin600` observations:
- title: **27.338 presents/s**, P50 **35.952 ms**, P95 **39.163 ms**;
- gulch idle: **26.540 presents/s**, P50 **37.151 ms**, P95 **40.259 ms**;
- map: **30.173 presents/s**, P50 **32.370 ms**, P95 **35.525 ms**;
- map return: **26.210 presents/s**, P50 **37.685 ms**, P95 **41.871 ms**.

This is one valid exploratory arm, not repeated all-scene acceptance or a production clock change. Ordinary 150 MHz controls were ~23.46–23.49 presents/s in the same gulch idle; warm VM/cache state is imperfectly controlled. The >30 FPS and P95 <=33.33 ms targets remain **unmet in gameplay**. Median game SwapPSS is **537.27 MiB**; zero-swap is not solved. No power/temperature/battery-life benefit is asserted.

The first two invalid arms and their receipts are deliberately retained. Real KMS captures, memory/clock series and cleanup/save receipts are included. Diagnostic wrapper source is `tools/wol_gpu_frequency_probe.py`.
