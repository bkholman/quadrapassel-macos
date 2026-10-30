#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a relocatable, locally signed Quadrapassel.app from Homebrew libraries."""

import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PREFIXES = ("/System/Library/", "/usr/lib/")
LOAD_COMMANDS = {"LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LOAD_UPWARD_DYLIB"}


def run(*args, capture=False, **kwargs):
    result = subprocess.run([str(arg) for arg in args], check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, **kwargs)
    return result.stdout.strip() if capture else None


def macho_info(path):
    """Read actual load commands, not the install ID shown by otool -L."""
    commands = re.split(r"Load command \d+\n", run("otool", "-l", path, capture=True))
    deps, rpaths, minimums = [], [], []
    for block in commands:
        match = re.search(r"^\s*cmd (\S+)", block, re.M)
        if not match:
            continue
        command = match[1]
        if command in LOAD_COMMANDS:
            deps.append(re.search(r"^\s*name (.+) \(offset", block, re.M)[1])
        elif command == "LC_RPATH":
            rpaths.append(re.search(r"^\s*path (.+) \(offset", block, re.M)[1])
        elif command in {"LC_BUILD_VERSION", "LC_VERSION_MIN_MACOSX"}:
            minimums.append(re.search(r"^\s*(?:minos|version) ([\d.]+)", block, re.M)[1])
    return list(dict.fromkeys(deps)), list(dict.fromkeys(rpaths)), minimums


def version_key(version):
    return tuple(int(part) for part in version.split("."))


class Bundler:
    def __init__(self, app, executable):
        self.app = app
        self.executable = executable.resolve()
        self.frameworks = app / "Contents/Frameworks"
        self.resources = app / "Contents/Resources"
        self.frameworks.mkdir(parents=True)
        self.resources.mkdir(parents=True)
        self.copied = {}
        self.names = {}
        self.kegs = set()
        self.minimums = ["11.0"]
        self.architectures = set(run("lipo", "-archs", executable, capture=True).split())

    def record_keg(self, path):
        for parent in path.resolve().parents:
            if (parent / "INSTALL_RECEIPT.json").is_file():
                self.kegs.add(parent)
                return

    def resolve(self, dependency, source, rpaths):
        def expand(value):
            return value.replace("@loader_path", str(source.parent)).replace(
                "@executable_path", str(self.executable.parent))

        if dependency.startswith("@rpath/"):
            candidates = [Path(expand(path)) / dependency[len("@rpath/"):] for path in rpaths]
            candidates += [source.parent / Path(dependency).name]
        else:
            candidates = [Path(expand(dependency))]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        raise RuntimeError(f"Cannot resolve {dependency} needed by {source}")

    def copy_binary(self, source, destination=None):
        source = source.resolve()
        if source in self.copied:
            return self.copied[source]
        destination = destination or self.frameworks / source.name
        if destination.name in self.names and self.names[destination.name] != source:
            raise RuntimeError(f"Two different libraries have the name {destination.name}")
        self.names[destination.name] = source
        self.copied[source] = destination
        self.record_keg(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        destination.chmod(destination.stat().st_mode | 0o200)
        archs = set(run("lipo", "-archs", source, capture=True).split())
        if not self.architectures <= archs:
            raise RuntimeError(f"{source} lacks architectures {self.architectures - archs}")
        deps, rpaths, minimums = macho_info(source)
        self.minimums.extend(minimums)
        changes = []
        for dependency in deps:
            if dependency.startswith(SYSTEM_PREFIXES):
                continue
            copied_dep = self.copy_binary(self.resolve(dependency, source, rpaths))
            relative = os.path.relpath(copied_dep, destination.parent)
            changes.extend(["-change", dependency, f"@loader_path/{relative}"])
        if destination.parent == self.frameworks:
            changes.extend(["-id", f"@rpath/{destination.name}"])
        for rpath in rpaths:
            changes.extend(["-delete_rpath", rpath])
        if changes:
            run("install_name_tool", *changes, destination)
        return destination

    def copy_tree(self, source, relative):
        if source.is_dir():
            self.record_keg(source)
            shutil.copytree(source, self.resources / relative, dirs_exist_ok=True)

    def copy_licenses(self):
        target = self.resources / "licenses"
        target.mkdir()
        shutil.copy2(ROOT / "COPYING", target / "Quadrapassel-GPL-3.0.txt")
        support = ROOT / "subprojects/libgnome-games-support"
        for name in ("COPYING", "COPYING.LESSER"):
            shutil.copy2(support / name, target / f"libgnome-games-support-{name}")
        manifest = []
        for keg in sorted(self.kegs):
            dest = target / f"{keg.parent.name}-{keg.name}"
            dest.mkdir()
            for child in keg.iterdir():
                if child.is_file() and re.match(r"(?i)(copying|licen[cs]e|notice|authors|copyright)", child.name):
                    shutil.copy2(child, dest / child.name)
            for relative in ("share/licenses", ".brew"):
                if (keg / relative).is_dir():
                    shutil.copytree(keg / relative, dest / Path(relative).name)
            if (keg / "sbom.spdx.json").is_file():
                shutil.copy2(keg / "sbom.spdx.json", dest / "sbom.spdx.json")
            manifest.append({"name": keg.parent.name, "version": keg.name})
        (target / "dependencies.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (target / "README.txt").write_text(
            "Quadrapassel is GPL-3.0-or-later. libgnome-games-support is LGPL-3.0-or-later.\n"
            "Third-party notices, Homebrew formulae (including source URLs and build recipes),\n"
            "and available SPDX metadata are included in the component directories.\n"
            "See the source repository's MACOS.md before distributing a release.\n")

    def verify(self):
        for path in self.copied.values():
            deps, rpaths, _ = macho_info(path)
            if rpaths:
                raise RuntimeError(f"Unexpected runtime search paths in {path}: {rpaths}")
            for dep in deps:
                if dep.startswith(SYSTEM_PREFIXES):
                    continue
                if not dep.startswith("@loader_path/"):
                    raise RuntimeError(f"External dependency in {path}: {dep}")
                resolved = (path.parent / dep[len("@loader_path/"):]).resolve()
                if not resolved.is_relative_to(self.app.resolve()) or not resolved.is_file():
                    raise RuntimeError(f"Dependency escapes or is missing from the bundle: {dep}")
        for path in self.app.rglob("*"):
            if path.is_symlink() and not path.resolve().is_relative_to(self.app.resolve()):
                raise RuntimeError(f"External symlink: {path}")


def make_icon(resources, work):
    iconset = work / "Quadrapassel.iconset"
    iconset.mkdir()
    source = ROOT / "data/icons/hicolor/scalable/org.gnome.Quadrapassel.svg"
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            name = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
            run("rsvg-convert", "-w", size * scale, "-h", size * scale,
                "-o", iconset / name, source)
    run("iconutil", "-c", "icns", iconset, "-o", resources / "Quadrapassel.icns")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build-macos")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("Build the macOS bundle on macOS; Linux builds use Meson directly.")
    for tool in ("brew", "meson", "ninja", "valac", "pkg-config", "blueprint-compiler",
                 "glib-compile-schemas", "gdk-pixbuf-query-loaders", "rsvg-convert",
                 "otool", "install_name_tool", "lipo", "codesign", "iconutil"):
        if shutil.which(tool) is None:
            parser.error(f"Missing {tool}. Install the build dependencies listed in MACOS.md.")

    build = args.build_dir.resolve()
    output = args.output_dir.resolve()
    install = build / "install"
    env = os.environ.copy()
    openal = Path(run("brew", "--prefix", "openal-soft", capture=True))
    env["PKG_CONFIG_PATH"] = str(openal / "lib/pkgconfig") + (
        os.pathsep + env["PKG_CONFIG_PATH"] if env.get("PKG_CONFIG_PATH") else "")
    setup = ["meson", "setup", build, ROOT, f"--prefix={install}", "-Dgamepad=disabled", "-Dprofile=default"]
    if (build / "meson-private/coredata.dat").is_file():
        setup.append("--reconfigure")
    run(*setup, env=env)
    run("meson", "compile", "-C", build, env=env)
    run("meson", "install", "-C", build, "--no-rebuild", env=env)
    project = json.loads(run("meson", "introspect", "--projectinfo", build, capture=True))
    output.mkdir(parents=True, exist_ok=True)
    final_app = output / "Quadrapassel.app"
    marker = "Contents/Resources/quadrapassel-build.json"
    if final_app.exists() and not (final_app / marker).is_file():
        raise RuntimeError(f"Refusing to replace an app not produced by this script: {final_app}")

    with tempfile.TemporaryDirectory(prefix=".quadrapassel-", dir=output) as temporary:
        work = Path(temporary)
        app = work / "Quadrapassel.app"
        bundler = Bundler(app, install / "bin/quadrapassel")
        bundler.copy_binary(install / "bin/quadrapassel", app / "Contents/MacOS/quadrapassel")
        bundler.copy_tree(install / "share", "share")
        for formula, relative in (("adwaita-icon-theme", "share/icons"),
                                  ("hicolor-icon-theme", "share/icons"),
                                  ("gtk4", "share/glib-2.0/schemas"),
                                  ("gtk4", "share/locale"),
                                  ("libadwaita", "share/locale"),
                                  ("glib", "share/locale"),
                                  ("gdk-pixbuf", "share/locale")):
            prefix = Path(run("brew", "--prefix", formula, capture=True))
            bundler.copy_tree(prefix / relative, relative)

        # SVG icons are loaded through a plugin, so they aren't in otool's dependency graph.
        rsvg = Path(run("brew", "--prefix", "librsvg", capture=True))
        loaders = list((rsvg / "lib").glob("gdk-pixbuf-*/*/loaders/*svg*"))
        if not loaders:
            raise RuntimeError("librsvg's GdkPixbuf SVG loader is missing")
        loader = loaders[0].resolve()
        bundled_loader = bundler.copy_binary(loader)
        cache = run("gdk-pixbuf-query-loaders", loader, capture=True)
        cache = "\n".join(line for line in cache.splitlines() if not line.startswith("#"))
        cache = cache.replace(str(loader), f"@FRAMEWORKS@/{bundled_loader.name}")
        (bundler.resources / "loaders.cache.in").write_text(cache + "\n\n")

        font_dir = bundler.resources / "etc/fonts"
        font_dir.mkdir(parents=True)
        (font_dir / "fonts.conf").write_text('''<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>/System/Library/Fonts</dir>
  <dir>/Library/Fonts</dir>
  <dir>~/Library/Fonts</dir>
  <cachedir prefix="xdg">fontconfig</cachedir>
</fontconfig>
''')
        (bundler.resources / "lib/gio/modules").mkdir(parents=True)
        run("glib-compile-schemas", bundler.resources / "share/glib-2.0/schemas")
        make_icon(bundler.resources, work)
        bundler.copy_licenses()
        minimum = max(bundler.minimums, key=version_key)
        languages = json.loads((ROOT / "data/languages.json").read_text())
        localizations = [tag for code, _, tag in languages
                         if code == "en" or (bundler.resources / "share/locale" / code /
                                             "LC_MESSAGES/quadrapassel.mo").is_file()]
        info = {
            "CFBundleName": "Quadrapassel", "CFBundleDisplayName": "Quadrapassel",
            "CFBundleIdentifier": "org.gnome.Quadrapassel", "CFBundleExecutable": "quadrapassel",
            "CFBundlePackageType": "APPL", "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleShortVersionString": project["version"], "CFBundleVersion": project["version"],
            "CFBundleIconFile": "Quadrapassel", "LSMinimumSystemVersion": minimum,
            "NSHighResolutionCapable": True, "NSPrincipalClass": "NSApplication",
            "CFBundleDevelopmentRegion": "en", "CFBundleLocalizations": localizations,
            "NSHumanReadableCopyright": "Copyright © Quadrapassel contributors. GPL-3.0-or-later.",
        }
        with (app / "Contents/Info.plist").open("wb") as handle:
            plistlib.dump(info, handle)
        (app / marker).write_text(json.dumps({
            "version": project["version"], "architectures": sorted(bundler.architectures),
            "minimum_macos": minimum, "libraries": len(bundler.copied) - 1,
            "signing": "ad-hoc (local development)",
        }, indent=2) + "\n")
        bundler.verify()
        for binary in bundler.copied.values():
            run("codesign", "--force", "--sign", "-", binary)
        run("codesign", "--force", "--sign", "-", app)
        run("codesign", "--verify", "--deep", "--strict", app)
        if final_app.exists():
            shutil.rmtree(final_app)
        shutil.move(app, final_app)
    print(f"\nBuilt {final_app} ({', '.join(sorted(bundler.architectures))}; macOS {minimum}+)")


if __name__ == "__main__":
    main()
