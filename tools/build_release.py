"""Builds dist/WhatDropsHere-<version>.zip containing only the addon files.

Usage (from the addon folder):  python tools/build_release.py
"""
import os
import re
import zipfile

ADDON = "WhatDropsHere"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files and folders that belong into the download (everything else stays in the repo only)
INCLUDE = [
    f"{ADDON}.txt",
    f"{ADDON}.lua",
    "WDH_Categories.lua",
    "WDH_Hud.lua",
    "WDH_Menu.lua",
    "lang",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
]


def read_version():
    with open(os.path.join(ROOT, f"{ADDON}.txt"), encoding="utf-8") as f:
        match = re.search(r"^## Version:\s*(\S+)", f.read(), re.MULTILINE)
    if not match:
        raise SystemExit("No '## Version:' found in the manifest")
    return match.group(1)


def collect_files():
    for entry in INCLUDE:
        path = os.path.join(ROOT, entry)
        if os.path.isdir(path):
            for folder, _, names in os.walk(path):
                for name in sorted(names):
                    yield os.path.join(folder, name)
        elif os.path.isfile(path):
            yield path
        else:
            raise SystemExit(f"Missing: {entry}")


def main():
    version = read_version()
    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    target = os.path.join(dist, f"{ADDON}-{version}.zip")

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in collect_files():
            # forward slashes and a top-level addon folder, as ESO and Minion expect
            name = ADDON + "/" + os.path.relpath(path, ROOT).replace(os.sep, "/")
            zf.write(path, name)
            print("  " + name)

    print(f"Created {target}")


if __name__ == "__main__":
    main()
