// Creates an empty assembly of a given name: some Unity builds list a store plugin in MonoManager
// (globalgamemanagers) whose Assembly-*.dll folder never had that file, e.g. Kartridge, and
// pmunity android-data refuses to pack until the name resolves.
using Mono.Cecil;

if (args.Length < 2)
{
    Console.Error.WriteLine("usage: stubasm <AssemblyName> <out dir>");
    return 2;
}

var name = args[0];
var outDir = Directory.CreateDirectory(args[1]).FullName;
var asm = AssemblyDefinition.CreateAssembly(
    new AssemblyNameDefinition(name, new Version(0, 0, 0, 0)), name, ModuleKind.Dll);
asm.Write(Path.Combine(outDir, name + ".dll"));
Console.WriteLine($"wrote {name}.dll");
return 0;
