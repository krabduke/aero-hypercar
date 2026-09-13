"""Copy the RX-8V engine sources into powerunit/.

The car does not re-model its engine: it imports the generators from the
sibling project and positions the result. That only stays true if the copy in
powerunit/ is actually the engine, and it had silently fallen three modules
and 111 parts behind -- the car was carrying the old engine while the engine
project had moved on.

So the copy is scripted, and it records which commit it came from. `make
vendor` refreshes it; verify.py checks the manifest still matches what is on
disk, so a stale copy fails the build instead of quietly shipping.

    python3 tools/vendor_engine.py [path-to-car-engine-repo]
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(os.path.dirname(ROOT), "car-engine")

# What the car needs in order to build the engine. Anything the engine's own
# assemble.py pulls in has to be here, or the import fails at build time.
FILES = ["spec.py", "mesh.py", "shapes.py", "airfoil.py"]
PART_MODULES = ["__init__.py", "common.py", "block.py", "bottomend.py",
                "heads.py", "plumbing.py", "induction.py", "turbo.py",
                "hybrid.py", "drive.py", "detail.py"]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()[:12]


def vendor(src=DEFAULT_SRC):
    eng = os.path.join(src, "engine")
    if not os.path.isdir(eng):
        raise SystemExit(f"no engine sources at {eng}")
    dst = os.path.join(ROOT, "powerunit")
    os.makedirs(os.path.join(dst, "parts"), exist_ok=True)

    manifest = {"source": os.path.basename(src), "files": {}}
    try:
        manifest["commit"] = subprocess.check_output(
            ["git", "-C", src, "rev-parse", "--short", "HEAD"],
            text=True).strip()
    except Exception:
        manifest["commit"] = "unknown"

    for f in FILES:
        s = os.path.join(eng, f)
        if not os.path.exists(s):
            continue
        shutil.copy2(s, os.path.join(dst, f))
        manifest["files"][f] = digest(s)
    for f in PART_MODULES:
        s = os.path.join(eng, "parts", f)
        if not os.path.exists(s):
            continue
        shutil.copy2(s, os.path.join(dst, "parts", f))
        manifest["files"]["parts/" + f] = digest(s)

    # drop any stale __pycache__, which will happily shadow a changed module
    for d, _, _ in os.walk(dst):
        if d.endswith("__pycache__"):
            shutil.rmtree(d, ignore_errors=True)

    with open(os.path.join(dst, "VENDOR.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    return manifest


def check():
    """True if every vendored file still matches its recorded digest."""
    p = os.path.join(ROOT, "powerunit", "VENDOR.json")
    if not os.path.exists(p):
        return False, "powerunit/VENDOR.json missing -- run `make vendor`"
    man = json.load(open(p))
    bad = []
    for rel, want in man["files"].items():
        f = os.path.join(ROOT, "powerunit", rel)
        if not os.path.exists(f):
            bad.append(rel + " (missing)")
        elif digest(f) != want:
            bad.append(rel + " (changed)")
    if bad:
        return False, ", ".join(bad[:4])
    return True, f"{len(man['files'])} files from {man.get('commit', '?')}"


if __name__ == "__main__":
    m = vendor(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC)
    print(f"vendored {len(m['files'])} files from {m['source']} @ {m['commit']}")
