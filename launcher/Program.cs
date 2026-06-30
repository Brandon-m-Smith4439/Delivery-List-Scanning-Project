using System.Diagnostics;

static string? FindAppScript()
{
    var candidates = new[]
    {
        AppContext.BaseDirectory,
        Directory.GetCurrentDirectory(),
        Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..")),
        Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..")),
    };

    foreach (var directory in candidates.Distinct(StringComparer.OrdinalIgnoreCase))
    {
        var script = Path.Combine(directory, "Start-DeliveryScannerWebApp.ps1");
        if (File.Exists(script))
        {
            return script;
        }
    }

    return null;
}

var scriptPath = FindAppScript();
if (scriptPath is null)
{
    Console.Error.WriteLine("Could not find Start-DeliveryScannerWebApp.ps1. Keep this launcher in the delivery-list-web-app folder.");
    return 1;
}

var startInfo = new ProcessStartInfo
{
    FileName = "powershell.exe",
    Arguments = $"-NoProfile -ExecutionPolicy Bypass -File \"{scriptPath}\"",
    WorkingDirectory = Path.GetDirectoryName(scriptPath) ?? Directory.GetCurrentDirectory(),
    UseShellExecute = true,
    WindowStyle = ProcessWindowStyle.Normal,
};

Process.Start(startInfo);
return 0;
