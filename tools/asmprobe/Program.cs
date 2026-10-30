// Prints the signatures of a type's methods (and fields) from a managed assembly: what a patch must
// match exactly when it rewrites IL.
using Mono.Cecil;

if (args.Length < 2)
{
    Console.Error.WriteLine("usage: asmprobe <assembly> <type name>");
    return 2;
}

var asm = AssemblyDefinition.ReadAssembly(args[0], new ReaderParameters { AssemblyResolver = new DefaultAssemblyResolver() });
foreach (var t in asm.MainModule.Types)
{
    if (args[1].StartsWith("~")) {
        if (!t.FullName.ToLower().Contains(args[1].TrimStart('~').ToLower())) continue;
    } else if (t.Name != args[1]) continue;
    Console.WriteLine($"type {t.FullName}");
    foreach (var f in t.Fields) Console.WriteLine($"  field {f.FieldType.Name} {f.Name}");
    foreach (var m in t.Methods)
    {
        var ps = string.Join(", ", m.Parameters.Select(p => $"{p.ParameterType.Name} {p.Name}"));
        Console.WriteLine($"  {(m.IsStatic ? "static " : "")}{m.ReturnType.Name} {m.Name}({ps})");
    }
}
return 0;
