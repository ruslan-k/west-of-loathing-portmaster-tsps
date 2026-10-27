using System;
using System.IO;
using System.IO.Compression;

public static class WoLPackedAssets
{
    public static bool Exists(string path)
    {
        if (path == null || !path.StartsWith("jar:file://", StringComparison.Ordinal))
            return File.Exists(path);
        int separator = path.IndexOf("!/", StringComparison.Ordinal);
        if (separator < 0) return false;
        try
        {
            Uri archive = new Uri(path.Substring(4, separator - 4));
            string entry = path.Substring(separator + 2);
            if (!archive.IsFile || !entry.StartsWith("assets/", StringComparison.Ordinal) ||
                entry.Contains("/../") || entry.Contains("\\")) return false;
            using (FileStream file = File.OpenRead(archive.LocalPath))
            using (ZipArchive zip = new ZipArchive(file, ZipArchiveMode.Read))
            {
                ZipArchiveEntry found = zip.GetEntry(entry);
                return found != null && found.Length > 0;
            }
        }
        catch (InvalidDataException) { return false; }
        catch (IOException) { return false; }
        catch (UnauthorizedAccessException) { return false; }
        catch (ArgumentException) { return false; }
        catch (NotSupportedException) { return false; }
    }
}
