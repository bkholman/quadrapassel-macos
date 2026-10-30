#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise bundle resources from a relocated path with no Homebrew runtime environment."""

import argparse
import importlib.util
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("build_app", HERE / "build-app.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)
run = bundle.run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, nargs="?", default=ROOT / "dist/Quadrapassel.app")
    args = parser.parse_args()
    app = args.app.resolve()
    run("codesign", "--verify", "--deep", "--strict", app)
    with tempfile.TemporaryDirectory(prefix="quadrapassel-test-") as temporary:
        work = Path(temporary).resolve()
        moved = work / "A folder with spaces" / "Renamed Quadrapassel.app"
        shutil.copytree(app, moved)
        contents = moved / "Contents"
        probe = contents / "MacOS/bundle-smoke-test"
        frameworks = contents / "Frameworks"
        env = os.environ.copy()
        openal = run("brew", "--prefix", "openal-soft", capture=True)
        env["PKG_CONFIG_PATH"] = f"{openal}/lib/pkgconfig" + (
            os.pathsep + env["PKG_CONFIG_PATH"] if env.get("PKG_CONFIG_PATH") else "")
        flags = shlex.split(run("pkg-config", "--cflags", "--libs", "gio-2.0", "gdk-pixbuf-2.0",
                                "sndfile", "openal", capture=True, env=env))
        run("cc", HERE / "smoke-test.c", ROOT / "src/macos-support.c", "-I", ROOT / "src",
            '-DAPP_ID="org.gnome.Quadrapassel"', "-Wl,-headerpad_max_install_names",
            *flags, "-o", probe, env=env)
        deps, rpaths, _ = bundle.macho_info(probe)
        changes = []
        for dep in deps:
            if dep.startswith(bundle.SYSTEM_PREFIXES):
                continue
            name = Path(dep).resolve().name
            if not (frameworks / name).is_file():
                raise RuntimeError(f"The probe needs a library missing from the bundle: {dep}")
            changes += ["-change", dep, f"@executable_path/../Frameworks/{name}"]
        for rpath in rpaths:
            changes += ["-delete_rpath", rpath]
        run("install_name_tool", *changes, probe)
        run("codesign", "--force", "--sign", "-", probe)
        run("codesign", "--force", "--sign", "-", moved)

        # Keep the real user identity for CoreAudio, but isolate all application data.
        clean = {key: os.environ[key] for key in ("HOME", "USER", "LOGNAME", "TMPDIR") if key in os.environ}
        clean.update(PATH="/usr/bin:/bin", LANG="en_US.UTF-8",
                     XDG_DATA_HOME=str(work / "data"), XDG_CACHE_HOME=str(work / "cache"),
                     XDG_CONFIG_HOME=str(work / "config"))
        for phase in ("write", "read"):
            run(probe, phase, env=clean, cwd=work)
        run("codesign", "--verify", "--deep", "--strict", moved)
        with (contents / "Info.plist").open("rb") as handle:
            info = plistlib.load(handle)
        print(f"PASS: app signature remains valid after relocation; minimum macOS {info['LSMinimumSystemVersion']}")


if __name__ == "__main__":
    main()
