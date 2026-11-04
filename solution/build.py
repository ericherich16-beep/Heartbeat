"""Build the JQC/PWI Management solution (.zip) from source.

What it does
  1. Writes the environment variable definitions (CLAUDE.md Section 10) into
     solution/JQCPWIManagement/src/environmentvariabledefinitions/ from the
     ENV_VARS table below (single source of truth).
  2. Sets the solution's display name, description, version and root components.
  3. Runs `pac solution pack` to produce solution/dist/JQCPWIManagement_<version>_unmanaged.zip.

Later build steps add the canvas app (CanvasApps/) and the upload flow
(Workflows/) to the same solution project; this script will pick them up.

Nothing site-specific is written: the environment variables have NO current
value, so Power Apps asks for the site and the lists when the solution is imported.

Usage
  python3 solution/build.py                      # uses `pac` on PATH
  PAC="python3 /path/to/pac.py" python3 solution/build.py
  python3 solution/build.py --no-pack            # regenerate sources only

Requires the Power Platform CLI (pac). On Windows/macOS install it with the
Power Platform Tools VS Code extension, the MSI, or
`dotnet tool install --global Microsoft.PowerApps.CLI.Tool`.
"""
import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.join(HERE, "JQCPWIManagement")
SRC = os.path.join(PROJECT, "src")
DIST = os.path.join(HERE, "dist")

SOLUTION_UNIQUE_NAME = "JQCPWIManagement"
SOLUTION_DISPLAY_NAME = "JQC/PWI Management"
SOLUTION_DESCRIPTION = (
    "JQC/PWI Management: job qualification checklists and process work instructions, "
    "assignments, sign-offs, training matrix and cross-training view. SharePoint lists "
    "are configured through environment variables."
)
SOLUTION_VERSION = "0.2.0.0"   # bump the middle number with each build step that adds components
PUBLISHER_DISPLAY_NAME = "JQC/PWI Management"

SHAREPOINT_API = "/providers/microsoft.powerapps/apis/shared_sharepointonline"
DATA_SOURCE_TYPE = "100000004"  # environment variable type "Data source"

# Single source of truth for environment variables (CLAUDE.md Section 10).
# parameterkey: "dataset" = SharePoint site, "table" = list or library (child of the site).
ENV_VARS = [
    {
        "schema": "jp_SiteUrl", "parameterkey": "dataset", "parent": None,
        "display": "JQC/PWI - SharePoint site",
        "description": "SharePoint site that holds the JP_ lists and libraries.",
    },
    {
        "schema": "jp_ListEmployees", "parameterkey": "table", "parent": "jp_SiteUrl",
        "display": "JQC/PWI - JP_Employees list",
        "description": "SharePoint list JP_Employees (employees, roles, shifts).",
    },
    {
        "schema": "jp_LibDocuments", "parameterkey": "table", "parent": "jp_SiteUrl",
        "display": "JQC/PWI - JP_Documents library",
        "description": "Document library JP_Documents (JQC templates and PWIs).",
    },
    {
        "schema": "jp_ListAssignments", "parameterkey": "table", "parent": "jp_SiteUrl",
        "display": "JQC/PWI - JP_Assignments list",
        "description": "SharePoint list JP_Assignments (one row per employee per document revision).",
    },
    {
        "schema": "jp_LibSignoffs", "parameterkey": "table", "parent": "jp_SiteUrl",
        "display": "JQC/PWI - JP_SignoffRecords library",
        "description": "Document library JP_SignoffRecords (signed JQCs and PWI training logs).",
    },
    {
        "schema": "jp_ListSettings", "parameterkey": "table", "parent": "jp_SiteUrl",
        "display": "JQC/PWI - JP_Settings list",
        "description": "SharePoint list JP_Settings (single settings row).",
    },
]


def label(tag, text):
    t = escape(text, {'"': "&quot;"})
    return f'  <{tag} default="{t}">\n    <label description="{t}" languagecode="1033" />\n  </{tag}>\n'


def env_var_xml(v):
    xml = f'<environmentvariabledefinition schemaname="{v["schema"]}">\n'
    xml += f"  <apiid>{SHAREPOINT_API}</apiid>\n"
    xml += label("description", v["description"])
    xml += label("displayname", v["display"])
    xml += "  <introducedversion>1.0</introducedversion>\n"
    xml += "  <iscustomizable>1</iscustomizable>\n"
    xml += "  <isrequired>0</isrequired>\n"
    xml += f'  <parameterkey>{v["parameterkey"]}</parameterkey>\n'
    if v["parent"]:
        xml += f'  <parentdefinitionid>\n    <schemaname>{v["parent"]}</schemaname>\n  </parentdefinitionid>\n'
    xml += "  <secretstore>0</secretstore>\n"
    xml += f"  <type>{DATA_SOURCE_TYPE}</type>\n"
    xml += "</environmentvariabledefinition>\n"
    return xml


def write_env_vars():
    root = os.path.join(SRC, "environmentvariabledefinitions")
    if os.path.isdir(root):
        shutil.rmtree(root)
    for v in ENV_VARS:
        folder = os.path.join(root, v["schema"])
        os.makedirs(folder)
        with open(os.path.join(folder, "environmentvariabledefinition.xml"), "w", encoding="utf-8") as f:
            f.write(env_var_xml(v))
        # Deliberately no environmentvariablevalues.json: no site-specific values in the repo.


def root_components():
    comps = []
    canvas = os.path.join(SRC, "CanvasApps")
    if os.path.isdir(canvas):
        for name in sorted(os.listdir(canvas)):
            if name.endswith(".meta.xml"):
                comps.append(f'<RootComponent type="300" schemaName="{name[:-9]}" behavior="0" />')
    workflows = os.path.join(SRC, "Workflows")
    if os.path.isdir(workflows):
        for name in sorted(os.listdir(workflows)):
            m = re.search(r"-([0-9A-Fa-f-]{36})\.json$", name)
            if m:
                comps.append(f'<RootComponent type="29" id="{{{m.group(1).lower()}}}" behavior="0" />')
    for v in ENV_VARS:
        comps.append(f'<RootComponent type="380" schemaName="{v["schema"]}" behavior="0" />')
    return comps


def update_solution_xml():
    path = os.path.join(SRC, "Other", "Solution.xml")
    with open(path, encoding="utf-8-sig") as f:
        xml = f.read()

    t = escape(SOLUTION_DISPLAY_NAME, {'"': "&quot;"})
    p = escape(PUBLISHER_DISPLAY_NAME, {'"': "&quot;"})
    d = escape(SOLUTION_DESCRIPTION, {'"': "&quot;"})

    head, sep, publisher = xml.partition("<Publisher>")
    head = re.sub(r'<LocalizedName description="[^"]*" languagecode="1033" />',
                  f'<LocalizedName description="{t}" languagecode="1033" />', head, count=1)
    head = re.sub(r"<Descriptions\s*/>|<Descriptions>.*?</Descriptions>",
                  f'<Descriptions>\n      <Description description="{d}" languagecode="1033" />\n    </Descriptions>',
                  head, count=1, flags=re.S)
    head = re.sub(r"<Version>[^<]*</Version>", f"<Version>{SOLUTION_VERSION}</Version>", head, count=1)
    publisher = re.sub(r'<LocalizedName description="[^"]*" languagecode="1033" />',
                       f'<LocalizedName description="{p}" languagecode="1033" />', publisher, count=1)
    xml = head + sep + publisher

    comps = "\n".join("      " + c for c in root_components())
    xml = re.sub(r"<RootComponents\s*/>|<RootComponents>.*?</RootComponents>",
                 f"<RootComponents>\n{comps}\n    </RootComponents>", xml, count=1, flags=re.S)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


def pack():
    pac = shlex.split(os.environ.get("PAC", "pac"))
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, f"{SOLUTION_UNIQUE_NAME}_{SOLUTION_VERSION.replace('.', '_')}_unmanaged.zip")
    if os.path.exists(out):
        os.remove(out)
    cmd = pac + ["solution", "pack", "--zipfile", out, "--folder", SRC, "--packagetype", "Unmanaged"]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write("\n".join(l for l in res.stdout.splitlines() if not l.startswith("Processing Component")) + "\n")
    if res.returncode != 0 or not os.path.exists(out):
        sys.stderr.write(res.stderr)
        sys.exit(f"pac solution pack failed (exit {res.returncode})")
    print("Built:", os.path.relpath(out, os.path.dirname(HERE)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-pack", action="store_true", help="regenerate sources only")
    args = ap.parse_args()
    write_env_vars()
    update_solution_xml()
    print(f"Wrote {len(ENV_VARS)} environment variable definitions and updated Solution.xml")
    if not args.no_pack:
        pack()


if __name__ == "__main__":
    main()
