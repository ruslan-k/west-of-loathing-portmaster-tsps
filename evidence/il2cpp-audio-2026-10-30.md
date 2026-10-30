# Audio on the IL2CPP route: why 2019 games are silent and how WoL got sound (2026-10-30)

Symptom: Unity 2019.4 IL2CPP port ran at 60 fps with no sound, while the same `ua_host`
(the 2017-era builds) had sound.

## The two audio paths

- **2017 players** call OpenSL ES directly → `runtime/android/opensles.c` → SDL device or an
  `aplay`/`pw-cat`/`pacat` pipe. This path works on this hardware.
- **2019+ players** never touch OpenSL ES. Unity's `org.fmod.FMODAudioDevice` (Java) mixes in
  `runtime/jni/up_input.c:fmod_thread()` and hands the PCM to `UPC.on_audio`.
  **`ua_host` never assigned `cfg.on_audio`**, so every block was dropped after mixing:
  no error, no warning, silence. That is the whole bug.

## Fixes in `runtime/host/ua_host.c`

1. `cfg.on_audio = host_audio_out;` — a real sink. First attempt: SDL
   (`SDL_OpenAudioDevice`, s16 stereo at the rate FMOD reports).
2. On TSPS SDL fails even with `AUDIODEV=plughw:0,0`:
   `SDL_OpenAudioDevice(48000 Hz, dev plughw:0,0): No such device`, while `aplay -D plughw:0,0`
   and a standalone SDL test both work. Cause not pinned; the fallback is what ships.
3. Fallback sink: `popen("aplay -q -t raw -f S16_LE -r 48000 -c 2 -D plughw:0,0 -", "w")`,
   unbuffered `fwrite` of each block (`UA_AUDIO_PIPE_CMD` overrides the command).
4. **`UA_AUDIO_SINK=pipe`** selects the aplay path as the only sink. Without it both paths could
   open: SDL succeeded on a later attempt while aplay already held the card in `PREPARED`, so the
   PCM went to SDL and the device stayed blocked by an idle aplay — still silent, and the next
   `aplay` reported `Device or resource busy`.
5. Pacing bug found by the port's own jni tests: the original loop did `continue` after handing a
   block to the sink, skipping the AudioTrack-style sleep — a busy loop with an unbounded queue.
   The sink call no longer skips pacing (`PASSED: 0 failures in 8 Unity version shapes`).
6. The open failure is logged once (`g_audio_failed`), not once per block (5376 lines in 10 s).

## Launcher (port side)

```sh
export SDL_AUDIODRIVER=alsa
export AUDIODEV=plughw:0,0
export UA_AUDIO_SINK=pipe
```

## Measured after the fix

```
[audio] PCM pipe: aplay -q -t raw -f S16_LE -r 48000 -c 2 -D plughw:0,0 -
[fps] 60.1 fps, frame 16.6 avg / 20.4 p99 / 30.0 worst ms, hitch 0, rss 590 MB
MemAvailable 257 MB
```

Sound confirmed by ear on the device; the same run also confirms the shader/DLC fixes.
