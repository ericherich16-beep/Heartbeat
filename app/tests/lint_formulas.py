"""Syntax-check every formula in the generated app with `pac power-fx run` (offline).

The Power Fx runner doesn't know canvas-only functions (Navigate, Patch, Notify ...) or the
app's controls and data sources, so those "name isn't valid" / "not supported" messages are
ignored. What this catches is real syntax errors: unbalanced brackets, missing operators,
bad string quoting, misplaced separators. Each formula is checked on its own.

Usage
  PAC="python3 /path/to/pac.py" python3 app/tests/lint_formulas.py
Exit code 0 = no syntax errors.
"""
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SYNTAX = re.compile(r"Expected |Unexpected characters|contains 'Eof'|Missing |Invalid token|Unexpected token|"
                    r"Unterminated|is not closed|Unknown character")


def load_app():
    spec = importlib.util.spec_from_file_location("build_app", os.path.join(REPO, "app", "build_app.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.path.insert(0, os.path.join(REPO, "app"))
    import screens
    return mod, screens.build(mod)


def collect(ctrl, out, path=""):
    here = (path + "/" if path else "") + ctrl.name
    for k, v in ctrl.props.items():
        v = str(v)
        if re.fullmatch(r"-?\d+(\.\d+)?|true|false", v):
            continue
        out.append((here + "." + k, v))
    for ch in ctrl.children:
        collect(ch, out, here)


def main():
    app, screens = load_app()
    formulas = []
    for s in screens:
        collect(s, formulas)
    onstart = [("App.OnStart", app.APP_ONSTART)]
    lines, index = [], []
    for name, f in onstart + formulas:
        one = re.sub(r"//[^\n]*", "", f)               # comments
        one = re.sub(r"\s*\n\s*", " ", one).strip()     # the runner reads one statement per line
        if not one:
            continue
        lines.append(one)
        index.append(name)
    with tempfile.NamedTemporaryFile("w", suffix=".fx", delete=False, encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
        path = fh.name
    pac = shlex.split(os.environ.get("PAC", "pac"))
    res = subprocess.run(pac + ["power-fx", "run", "--file", path], capture_output=True)
    os.unlink(path)
    out = (res.stdout + res.stderr).replace(b"\x00", b"").decode("utf-8", "replace")
    bad = {}
    for l in out.splitlines():
        m = re.match(r"\s*Line (\d+): Error [\d-]+: (.*)", l)
        if m and SYNTAX.search(m.group(2)):
            n = int(m.group(1)) - 1
            bad.setdefault(index[n] if n < len(index) else f"line {n + 1}", []).append(m.group(2))
    print(f"Checked {len(lines)} formulas on {len(screens)} screens")
    for name, errs in bad.items():
        print("SYNTAX", name)
        for e in errs[:3]:
            print("     ", e)
    print("NO SYNTAX ERRORS" if not bad else f"{len(bad)} FORMULA(S) WITH SYNTAX ERRORS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
