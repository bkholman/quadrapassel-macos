#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify System/manual language selection and translations in a relocated macOS app."""
import argparse
import gettext
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
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
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build-macos")
    args = parser.parse_args()
    app = args.app.resolve()
    run("meson", "compile", "-C", args.build_dir, "test-localization-runtime")
    run("codesign", "--verify", "--deep", "--strict", app)

    with tempfile.TemporaryDirectory(prefix="quadrapassel-languages-") as temporary:
        work = Path(temporary).resolve()
        moved = work / "A folder with spaces" / "Localized Quadrapassel.app"
        shutil.copytree(app, moved)
        contents = moved / "Contents"
        probe = contents / "MacOS/test-localization-runtime"
        shutil.copy2(args.build_dir / "test-localization-runtime", probe)
        deps, rpaths, _ = bundle.macho_info(probe)
        changes = []
        for dep in deps:
            if dep.startswith(bundle.SYSTEM_PREFIXES):
                continue
            name = Path(dep).resolve().name
            if not (contents / "Frameworks" / name).is_file():
                raise RuntimeError(f"Missing bundled test dependency: {name}")
            changes += ["-change", dep, f"@executable_path/../Frameworks/{name}"]
        for rpath in rpaths:
            changes += ["-delete_rpath", rpath]
        run("install_name_tool", *changes, probe)
        run("codesign", "--force", "--sign", "-", probe)
        run("codesign", "--force", "--sign", "-", moved)

        locale = contents / "Resources/share/locale"
        metadata = json.loads((ROOT / "data/languages.json").read_text())
        with (contents / "Info.plist").open("rb") as handle:
            info = plistlib.load(handle)
        expected = {tag for code, _, tag in metadata
                    if code == "en" or (locale / code / "LC_MESSAGES/quadrapassel.mo").is_file()}
        assert set(info["CFBundleLocalizations"]) == expected
        assert info["CFBundleDevelopmentRegion"] == "en"

        clean = {key: os.environ[key] for key in ("HOME", "USER", "LOGNAME", "TMPDIR") if key in os.environ}
        # Deliberately conflicting terminal locale: System must follow macOS,
        # and a manual preference must win over both the OS and the terminal.
        clean.update(PATH="/usr/bin:/bin", LANG="C", LC_ALL="C", LANGUAGE="it",
                     XDG_DATA_HOME=str(work / "data"), XDG_CACHE_HOME=str(work / "cache"),
                     XDG_CONFIG_HOME=str(work / "config"))
        cases = [("system", "fr-CA", "fr"), ("system", "pt-BR", "pt_BR"),
                 ("system", "zh-Hant-HK", "zh_HK"), ("system", "sr-Latn-RS", "sr@latin"),
                 ("system", "en-US", "en"), ("system", "xx-YY", "en"),
                 ("de", "fr-FR", "de"), ("es", "en-US", "es"),
                 ("ja", "en-US", "ja"), ("en", "fr-FR", "en"),
                 ("ar", "en-US", "ar"), ("missing", "fr-FR", "fr")]
        for selection, os_language, expected_code in cases:
            translations = []
            for domain, msgid in [("quadrapassel", "_Preferences"), ("gtk40", "_Cancel"),
                                   ("libadwaita", "Preferences")]:
                catalog = gettext.translation(domain, locale, [expected_code], fallback=True)
                translations.append(catalog.gettext(msgid))
            run(probe, selection, os_language, expected_code, *translations, env=clean, cwd=work)
        run("codesign", "--verify", "--deep", "--strict", moved)
        print(f"PASS: {len(cases)} language scenarios; {len(expected)} declared languages; relocated app signature valid")


if __name__ == "__main__":
    main()
