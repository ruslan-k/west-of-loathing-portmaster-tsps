using Mono.Cecil;
using Mono.Cecil.Cil;

if (args.Length != 4) throw new ArgumentException("managed-dir out-dir helper-dll reference-dir");
using var resolver = new DefaultAssemblyResolver();
resolver.AddSearchDirectory(args[0]);
resolver.AddSearchDirectory(args[3]);
using var game = AssemblyDefinition.ReadAssembly(Path.Combine(args[0], "Assembly-CSharp.dll"),
    new ReaderParameters { AssemblyResolver = resolver });
using var helper = AssemblyDefinition.ReadAssembly(args[2]);
var method = game.MainModule.Types.Single(t => t.Name == "AssetBundleManager").Methods
    .Single(m => m.Name == "FTryLoadAssetBundleInternal");
var calls = method.Body.Instructions.Where(i => i.OpCode == OpCodes.Call).ToArray();
if (!calls.Any(i => i.Operand is MethodReference m && m.DeclaringType.FullName == "UnityEngine.Application" && m.Name == "get_streamingAssetsPath") ||
    !calls.Any(i => i.Operand is MethodReference m && m.DeclaringType.FullName == "UnityEngine.AssetBundle" && m.Name == "LoadFromFileAsync") ||
    !calls.Any(i => i.Operand is MethodReference m && m.Name == "FHasDlc"))
    throw new InvalidDataException("Unexpected asset loader; refusing to patch");
var exists = calls.Single(i => i.Operand is MethodReference m && m.DeclaringType.FullName == "System.IO.File" && m.Name == "Exists");
var replacement = helper.MainModule.Types.Single(t => t.Name == "WoLPackedAssets").Methods.Single(m => m.Name == "Exists");
exists.Operand = game.MainModule.ImportReference(replacement);
Directory.CreateDirectory(args[1]);
string output = Path.Combine(args[1], "Assembly-CSharp.dll");
game.Write(output);
using var readback = AssemblyDefinition.ReadAssembly(output);
var checkedMethod = readback.MainModule.Types.Single(t => t.Name == "AssetBundleManager").Methods.Single(m => m.Name == method.Name);
if (checkedMethod.Body.Instructions.Count != method.Body.Instructions.Count ||
    checkedMethod.Body.Instructions.Count(i => i.Operand is MethodReference m && m.DeclaringType.FullName == "WoLPackedAssets" && m.Name == "Exists") != 1)
    throw new InvalidDataException("Patched call-site check failed");
Console.WriteLine("PACKED_ASSETS_PATCH_OK one File.Exists call replaced; DLC branch and engine load retained");
