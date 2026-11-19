#!/usr/bin/env python3
"""Builds the two zips into dist/:
  hyperslice-<version>-extension.zip   for extensions.blender.org (blender_manifest.toml at the root of the zip)
  hyperslice-<version>.zip             classic add-on zip (folder sculpture_sg1/, no manifest), for Install from Disk
The version is read from hyperslice/blender_manifest.toml; keep __init__.py's bl_info in step with it."""
import os, re, sys, zipfile, tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "hyperslice")
DIST = os.path.join(ROOT, "dist")
with open(os.path.join(SRC, "blender_manifest.toml"), "rb") as f:
    version = tomllib.load(f)["version"]
init = open(os.path.join(SRC, "__init__.py"), encoding="utf-8").read()
m = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', init)
if not m or ".".join(m.groups()) != version:
    sys.exit("bl_info version in __init__.py does not match blender_manifest.toml (%s)" % version)
os.makedirs(DIST, exist_ok=True)

def files():
    for d, dirs, fs in os.walk(SRC):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for n in sorted(fs):
            if n.endswith(".pyc"):
                continue
            p = os.path.join(d, n)
            yield p, os.path.relpath(p, SRC).replace(os.sep, "/")

ext = os.path.join(DIST, "hyperslice-%s-extension.zip" % version)
with zipfile.ZipFile(ext, "w", zipfile.ZIP_DEFLATED) as z:
    for p, rel in files():
        z.write(p, rel)
classic = os.path.join(DIST, "hyperslice-%s.zip" % version)
with zipfile.ZipFile(classic, "w", zipfile.ZIP_DEFLATED) as z:
    for p, rel in files():
        if rel != "blender_manifest.toml":
            z.write(p, "sculpture_sg1/" + rel)
print(ext); print(classic)
