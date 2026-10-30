// Makes the Steamworks wrapper report the DLC as owned, so the game's own DLC path opens on a
// handheld where SteamAPI_Init fails. Rewrites the three SteamApps methods the game calls to
// return "installed" instead of asking Steam (the Cuphead codepatch's dlc-from-steam-install idea).
using Mono.Cecil;
using Mono.Cecil.Cil;

if (args.Length < 2)
{
    Console.Error.WriteLine("usage: dlcpatch <steamworks.dll> <out.dll>");
    return 2;
}

var asm = AssemblyDefinition.ReadAssembly(args[0]);
var patched = new List<string>();

foreach (var type in asm.MainModule.Types)
{
    if (type.Name != "SteamApps") continue;

    foreach (var m in type.Methods)
    {
        bool ownsOne =
            (m.Name == "GetDLCCount" && m.ReturnType.MetadataType == MetadataType.Int32) ||
            (m.Name == "BIsDlcInstalled" && m.ReturnType.MetadataType == MetadataType.Boolean);
        if (!ownsOne) continue;

        m.Body = new MethodBody(m);
        var il = m.Body.GetILProcessor();
        il.Emit(OpCodes.Ldc_I4_1);
        il.Emit(OpCodes.Ret);
        m.Body.InitLocals = false;
        patched.Add(m.Name);
    }
}

if (patched.Count == 0)
{
    Console.Error.WriteLine("no SteamApps DLC methods found");
    return 1;
}

asm.Write(args[1]);
Console.WriteLine("patched: " + string.Join(", ", patched));
return 0;
