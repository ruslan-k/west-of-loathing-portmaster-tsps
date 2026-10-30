// Two managed fixes for the IL2CPP build:
//  * Steam DLC: the Steamworks wrapper reports the DLC as owned, so Gun Manor opens without Steam.
//  * Rewired's Linux-only ExternalTools.LinuxInput_* bodies: IL2CPP 2019.4 fails on them
//    (NullReferenceException in GetMethodCallExpression); the Android input path never calls them.
using Mono.Cecil;
using Mono.Cecil.Cil;

if (args.Length < 2)
{
    Console.Error.WriteLine("usage: dlcpatch <game Managed dir> <out dir>");
    return 2;
}

var managed = args[0];
var outDir = Directory.CreateDirectory(args[1]).FullName;
var changed = new List<string>();

// Cecil resolves the assembly's references while writing: point it at the game's own Managed folder.
var resolver = new DefaultAssemblyResolver();
resolver.AddSearchDirectory(managed);
var read = new ReaderParameters { AssemblyResolver = resolver };

void Save(AssemblyDefinition asm, string file)
{
    asm.Write(Path.Combine(outDir, file));
    changed.Add(file);
}

var swPath = Path.Combine(managed, "com.rlabrecque.steamworks.net.dll");
if (File.Exists(swPath))
{
    var sw = AssemblyDefinition.ReadAssembly(swPath, read);
    var hit = 0;
    foreach (var t in sw.MainModule.Types.Where(t => t.Name == "SteamApps"))
        foreach (var m in t.Methods)
        {
            if (m.Name == "GetDLCCount" && m.ReturnType.MetadataType == MetadataType.Int32 ||
                m.Name == "BIsDlcInstalled" && m.ReturnType.MetadataType == MetadataType.Boolean)
            {
                Stub(m, 1);
                hit++;
            }
        }
    if (hit > 0) Save(sw, "com.rlabrecque.steamworks.net.dll");
    else Console.Error.WriteLine("steamworks: no DLC methods found");
}

var csPath = Path.Combine(managed, "Assembly-CSharp.dll");
if (File.Exists(csPath))
{
    var cs = AssemblyDefinition.ReadAssembly(csPath, read);
    var hit = 0;
    foreach (var t in cs.MainModule.Types.Where(t => t.Name == "ExternalTools"))
        foreach (var m in t.Methods)
        {
            if (!m.Name.StartsWith("LinuxInput_") || m.Body == null) continue;
            Stub(m, 0);
            hit++;
        }
    Console.WriteLine($"rewired LinuxInput_* stubbed: {hit}");
    if (hit > 0) Save(cs, "Assembly-CSharp.dll");
}

Console.WriteLine("wrote: " + (changed.Count == 0 ? "(nothing)" : string.Join(", ", changed)));
return changed.Count == 0 ? 1 : 0;

static void Stub(MethodDefinition m, int intValue)
{
    m.Body = new MethodBody(m);
    var il = m.Body.GetILProcessor();
    if (m.ReturnType.MetadataType == MetadataType.Void) { il.Emit(OpCodes.Ret); return; }
    switch (m.ReturnType.MetadataType)
    {
        case MetadataType.Boolean:
        case MetadataType.Char:
        case MetadataType.SByte:
        case MetadataType.Byte:
        case MetadataType.Int16:
        case MetadataType.UInt16:
        case MetadataType.Int32:
        case MetadataType.UInt32:
            il.Emit(intValue == 0 ? OpCodes.Ldc_I4_0 : OpCodes.Ldc_I4_1);
            break;
        case MetadataType.Int64:
        case MetadataType.UInt64:
            il.Emit(OpCodes.Ldc_I4_0);
            il.Emit(OpCodes.Conv_I8);
            break;
        case MetadataType.Single:
            il.Emit(OpCodes.Ldc_R4, 0f);
            break;
        case MetadataType.Double:
            il.Emit(OpCodes.Ldc_R8, 0d);
            break;
        default:
            il.Emit(OpCodes.Ldnull);
            break;
    }
    il.Emit(OpCodes.Ret);
}
