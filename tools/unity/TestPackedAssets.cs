using System;
using System.IO;

public static class TestPackedAssets
{
    static int count;
    static void Check(bool condition, string name)
    {
        if (!condition) throw new Exception("FAIL " + name);
        Console.WriteLine("PASS " + name);
        count++;
    }
    public static int Main(string[] args)
    {
        string root = Path.GetFullPath(args[0]);
        string jar = "jar:" + new Uri(Path.Combine(root, "fixture space.apk")).AbsoluteUri + "!/";
        Check(WoLPackedAssets.Exists(jar + "assets/core"), "core in APK");
        Check(WoLPackedAssets.Exists(jar + "assets/house"), "DLC in APK");
        Check(!WoLPackedAssets.Exists(jar + "assets/missing"), "missing entry rejected");
        Check(!WoLPackedAssets.Exists(jar + "assets/empty"), "empty bundle rejected");
        Check(!WoLPackedAssets.Exists(jar + "assets/../core"), "traversal rejected");
        Check(!WoLPackedAssets.Exists(jar + "outside"), "non-asset rejected");
        Check(!WoLPackedAssets.Exists("jar:file://missing!/assets/core"), "missing archive rejected");
        Check(!WoLPackedAssets.Exists("jar:" + new Uri(Path.Combine(root, "corrupt.apk")).AbsoluteUri + "!/assets/core"), "corrupt archive rejected");
        Check(WoLPackedAssets.Exists(Path.Combine(root, "loose")), "desktop file preserved");
        Check(!WoLPackedAssets.Exists(Path.Combine(root, "missing")), "desktop missing preserved");
        Check(!WoLPackedAssets.Exists(null), "null rejected");
        Console.WriteLine("PASSED " + count);
        return 0;
    }
}
