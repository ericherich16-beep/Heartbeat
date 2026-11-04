#!/usr/bin/env bash
# Sets up the Power Platform CLI (pac) on a Linux machine that has no .NET installed,
# such as a Claude Code cloud container. Everything is downloaded from nuget.org
# (official Microsoft packages) into a scratch folder. Nothing is installed system-wide.
#
# Usage:
#   tools/setup-pac-linux.sh [install-dir]      # default: $HOME/.pac-local
#   export PAC="python3 <install-dir>/bin/pac.py"
#   python3 solution/build.py
#
# On Windows or macOS, install pac normally instead (VS Code "Power Platform Tools"
# extension, the MSI, or `dotnet tool install --global Microsoft.PowerApps.CLI.Tool`).
set -euo pipefail

DIR="${1:-$HOME/.pac-local}"
PAC_VERSION="${PAC_VERSION:-2.14.1}"   # Microsoft.PowerApps.CLI.Core.linux-x64
mkdir -p "$DIR" && cd "$DIR"

nuget() { curl -sSL -o "$2" "https://api.nuget.org/v3-flatcontainer/$1/$3/$1.$3.nupkg"; }

echo "Downloading pac $PAC_VERSION"
nuget microsoft.powerapps.cli.core.linux-x64 pac.nupkg "$PAC_VERSION"
rm -rf pac && mkdir -p pac && unzip -q -o pac.nupkg -d pac/pkg

# pac targets .NET 10 and needs both the base runtime and the ASP.NET Core runtime.
RV=$(curl -sS https://api.nuget.org/v3-flatcontainer/microsoft.netcore.app.runtime.linux-x64/index.json \
  | python3 -c "import json,sys;v=[x for x in json.load(sys.stdin)['versions'] if x.startswith('10.0.') and '-' not in x];print(v[-1])")
echo "Downloading .NET runtime $RV"
for p in microsoft.netcore.app.runtime.linux-x64 microsoft.aspnetcore.app.runtime.linux-x64; do
  nuget "$p" "$p.nupkg" "$RV"; rm -rf "x/$p"; mkdir -p "x/$p"; unzip -q -o "$p.nupkg" -d "x/$p"
done
R="$DIR/dotnet"
mkdir -p "$R/shared/Microsoft.NETCore.App/$RV" "$R/shared/Microsoft.AspNetCore.App/$RV" "$R/host/fxr/$RV"
cp x/microsoft.netcore.app.runtime.linux-x64/runtimes/linux-x64/lib/net10.0/* \
   x/microsoft.netcore.app.runtime.linux-x64/runtimes/linux-x64/native/* "$R/shared/Microsoft.NETCore.App/$RV/"
cp x/microsoft.aspnetcore.app.runtime.linux-x64/runtimes/linux-x64/lib/net10.0/* "$R/shared/Microsoft.AspNetCore.App/$RV/"
cp "$R/shared/Microsoft.NETCore.App/$RV/libhostfxr.so" "$R/host/fxr/$RV/"

# The runtime packs have no `dotnet` launcher, so start pac through hostfxr from Python.
mkdir -p bin
cat > bin/pac.py <<EOF
import ctypes, sys, os
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root = os.path.join(S, "dotnet"); V = "$RV"
fxr = ctypes.CDLL(os.path.join(root, "host/fxr", V, "libhostfxr.so"))
app = os.path.join(S, "pac/pkg/tools/pac.dll")
args = [os.path.join(root, "dotnet")] + sys.argv[1:]
argv = (ctypes.c_char_p * len(args))(*[a.encode() for a in args])
fxr.hostfxr_main_startupinfo.restype = ctypes.c_int
sys.exit(fxr.hostfxr_main_startupinfo(len(args), argv, args[0].encode(), root.encode(), app.encode()))
EOF

PP_TOOLS_AUTOMATION_AGENT="claude-code/1.0" python3 bin/pac.py telemetry disable >/dev/null 2>&1 || true
python3 bin/pac.py help | head -2
echo
echo "Done. Use:  export PAC=\"python3 $DIR/bin/pac.py\""
