"""Copies the addon files into the game's AddOns folder for testing in game.

Usage (from the repository folder):  python tools/deploy.py [AddOns folder]

The repository lives outside the AddOns folder, because Minion replaces the whole
addon folder on every update (including .git, docs and tools). The copy in AddOns
is only a deployment target: it is deleted and rebuilt from the files listed in
build_release.INCLUDE, i.e. exactly what the release ZIP contains.
Default AddOns folder: %ESO_ADDONS% or D:/Dokumente/Elder Scrolls Online/live/AddOns
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_release  # noqa: E402  (same folder)

DEFAULT_ADDONS = os.environ.get("ESO_ADDONS", r"D:\Dokumente\Elder Scrolls Online\live\AddOns")


def main():
    addons = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDONS
    if not os.path.isdir(addons):
        raise SystemExit(f"AddOns folder not found: {addons}")
    target = os.path.join(addons, build_release.ADDON)
    root = os.path.abspath(build_release.ROOT)

    if os.path.abspath(target) == root:
        raise SystemExit("The repository is the AddOns folder itself - nothing to deploy")
    if os.path.exists(os.path.join(target, ".git")):
        raise SystemExit(f"{target} contains a git repository - not deleting it")

    # Empty the folder but keep it (it may be open in Explorer or a terminal, then it cannot be removed)
    os.makedirs(target, exist_ok=True)
    for name in os.listdir(target):
        path = os.path.join(target, name)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    count = 0
    for path in build_release.collect_files():
        dest = os.path.join(target, os.path.relpath(path, root))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(path, dest)
        count += 1
    print(f"Deployed {build_release.ADDON} {build_release.read_version()} ({count} files) to {target}")


if __name__ == "__main__":
    main()
