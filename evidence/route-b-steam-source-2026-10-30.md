# Route B source check — Steam PC build vs the installed port (2026-10-30)

Owner states the Steam copy on this host is the current install. Inspected read-only.

## Steam build

```
~/.local/share/Steam/steamapps/common/West of Loathing
UnityPlayer.so → 2019.4.41f2_6b23d448b533
314 MB total
West of Loathing_Data/StreamingAssets/
  core            187,391,253   sha 95ca1f5e4a8ca45e…
  core.manifest       293,404
  house            57,615,719   sha 53f6efa6848ab73c…
  house.manifest       78,561
  main_scene       12,245,045
  StreamingAssets       1,661
```

`core` and `house` both contain the Gun Manor / Reckoning strings; `house` is the DLC bundle.

## Installed port (APK built 2018-08-02)

```
assets/core   221,420,352
assets/house   64,595,359      (same manifest size 78,561, different bundle)
assets/bin/Data     288,000
```

## Why this matters

| | Steam (host) | installed port |
|---|---|---|
| Unity | **2019.4.41f2** | 2017.4.19f1 (measured earlier) |
| DLC bundle | `house` 57.6 MB | `house` 64.6 MB (older packaging) |
| Extra asset | `main_scene` 12.2 MB | absent |

The Steam build is the **updated engine generation** — the same 2019.4 line as the Switch v327680
update — and it carries the DLC. That makes route B (§28.4) concrete: repack this data for the ARM64
native Unity host instead of chasing the Switch runtime.

## Next concrete question (not yet answered)

Does the port's `ua_host` load 2019.4 assets, or does it need a host built for that engine line?
`ua_host` carries no version string, and the repository docs mention no engine version for it. The
Cuphead PortMaster port (`wild1walker/portmaster-cuphead`) runs a 2019 PC build through the same
`portmaster-unity` family, so a 2019-capable host exists in that ecosystem and can be used as the
reference for a WoL build.

No files were modified; the Steam install was only read.
