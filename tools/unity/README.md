# Owner-local Unity data preparation

These tools contain no game/Unity binaries. Use your lawfully owned **Linux** West of Loathing build with `core`, `main_scene` and `house`, Unity **2017.4.19f1**. Preserve the source; work on a copy. The recipe is for the verified TSPS build, not an automatic converter for arbitrary releases.

## Workspace prerequisites

```text
WORK/
  portmaster-unity/              pinned recursive upstream checkout
  venv/                         Python with upstream convert/requirements.txt
  player/                       exact Android ARM64 IL2CPP player + managed modules
  data/                         converted copy of West of Loathing_Data
  guided/                       upstream native ASTC encoder for the conversion Python
  asmpatch/                     upstream .NET 8 asmpatch build
  cuphead-runtime/cuphead/setup64/mono64/
    classlibs/                  generic 4.x BCL from pinned Cuphead release
    etc/                        matching Mono configuration
  classlibs-extra/
    System.Runtime.Serialization.dll
    System.ServiceModel.Internals.dll
    System.IO.Compression.dll
```

Pin upstream and runtime sources as documented in [`../../runtime/unity/README.md`](../../runtime/unity/README.md). Generic Mono components come from Cuphead release `2026.10.26.10`, ZIP SHA256 `1c05883bdcdeb7e31e558245ecdc9ca8d6cbf591972f3be138ff654fc252f7f3`. Copy only its generic `setup64/mono64/` and licenses, not Cuphead-specific code/data.

Create the venv, install `portmaster-unity/convert/requirements.txt`, then use that Python below. With `PYTHONPATH="$WORK/portmaster-unity/convert"`:

```sh
python -m pmunity player fetch 2017.4.19f1 "$WORK/player" --backend il2cpp --abi arm64-v8a --managed
dotnet build "$WORK/portmaster-unity/tools/asmpatch/asmpatch.csproj" -c Release -o "$WORK/asmpatch"
```

The three extra implementation assemblies must come from the exact Unity editor's `MonoBleedingEdge/lib/mono/unityjit/` profile, not `*-api` reference assemblies. Upstream `pmunity.nsis.Nsis` and `pmunity.winbcl.facades` retrieve only needed files from:
`https://download.unity3d.com/download_unity/47cd37c28be8/Windows64EditorInstaller/UnitySetup64-2017.4.19f1.exe`.
Use `facades(['System.Runtime.Serialization', 'System.ServiceModel.Internals', 'System.IO.Compression'], 'MonoBleedingEdge/lib/mono/unityjit/', installer, output_directory)` and assert no missing results. Keep these owner-local Unity files out of git.

## Convert a fresh copy

Run from this repository root, with WORK set to an owner-local directory and the venv active:

```sh
cp -a '/path/to/West of Loathing_Data' "$WORK/data"
python "$WORK/portmaster-unity/convert/native/guided_astc/build.py" "$WORK/guided"
export PYTHONPATH="$WORK/portmaster-unity/convert:$WORK/guided"
python -m pmunity convert "$WORK/data" --config tools/unity/convert.json
python tools/unity/convert_scene.py "$WORK"
```

The narrow scene wrapper exists because this `main_scene` has two serialized nodes. It refuses streamed textures/other shapes, preserves node names and untouched object bytes, and verifies GLES3 shader coverage and texture dimensions. Run it only once on the fresh source scene; it creates `WORK/scene-data` and fails if that workspace already exists. The main converter's 'left as it is' notice for this scene is not complete conversion by itself.

## Pack without consuming source

```sh
# DOTNET may be an absolute path if dotnet is not on PATH.
DOTNET=dotnet python tools/unity/prepare_packed.py "$WORK" "$WORK/packed-output"
```

`packed-output` must not exist. The tool compiles the small archive-existence helper against the matching BCL, builds the guarded Mono.Cecil patcher, applies upstream Rewired adaptation, then changes exactly one proven `File.Exists` call. It packs all data into an aligned STORE APK and verifies all bundles with pmunity. It does not modify DLC entitlement, texture quality, audio codecs, source files or installed progress. Only a proven unused missing `Kartridge.dll` MonoManager entry is dropped.

The helper tests in `TestPackedAssets.cs` cover actual/missing/corrupt/empty archive entries, URI spaces, path rejection and desktop file checks; the accepted build passed all eleven under target Mono. See [`../../docs/native-unity-port.md`](../../docs/native-unity-port.md). Final assembly reference closure must include all 67 dependencies; a successful first load does not prove save serialization.

Assemble the resulting owner-only `packed-output/android/zip/` plus exact player libraries using [`../../port/README.md`](../../port/README.md). Never copy game/Unity data back into a git staging area. The repository's `.gitignore` is a safeguard, not a license check.
