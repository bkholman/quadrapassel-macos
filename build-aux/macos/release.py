#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sign and package a local release; --notarize submits it to Apple, never publishes it."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(*args, capture=False, **kwargs):
    result = subprocess.run([str(arg) for arg in args], check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, **kwargs)
    return result.stdout.strip() if capture else None


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def tree_digest(directory):
    result = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            result.update(str(path.relative_to(directory)).encode() + b"\0")
            result.update(digest(path).encode())
    return result.hexdigest()


def signature(path, *, runtime=False):
    run("codesign", "--verify", "--deep", "--strict", path)
    details = run("codesign", "-d", "--verbose=4", path, capture=True, stderr=subprocess.STDOUT)
    if "Authority=Developer ID Application:" not in details or "Timestamp=" not in details:
        raise RuntimeError(f"Expected a timestamped Developer ID signature: {path}")
    if runtime and not re.search(r"^CodeDirectory .*flags=\S*\bruntime\b", details, re.M):
        raise RuntimeError(f"Hardened Runtime is missing: {path}")
    match = re.search(r"^TeamIdentifier=(\S+)$", details, re.M)
    if not match:
        raise RuntimeError(f"No signing team found: {path}")
    return match[1]


def verify_app(app, notarized=False):
    team = signature(app, runtime=True)
    for library in sorted((app / "Contents/Frameworks").iterdir()):
        if signature(library) != team:
            raise RuntimeError(f"Library signed by a different team: {library}")
    if notarized:
        run("xcrun", "stapler", "validate", app)
        run("spctl", "--assess", "--type", "execute", "--verbose=2", app)


def notarize(archive, ticket_target, directory, label, profile):
    submission_file = directory / f"{label}-submission.json"
    result_file = directory / f"{label}-result.json"
    log_file = directory / f"{label}-log.json"
    if submission_file.exists():
        submission = json.loads(submission_file.read_text())
        # A stapled DMG differs from the upload; only permit that change when its
        # accepted ticket can already be validated against this exact file.
        if submission["sha256"] != digest(archive):
            if not result_file.exists() or json.loads(result_file.read_text()).get("status") != "Accepted":
                raise RuntimeError("The uploaded artifact changed; use a new build number.")
            run("xcrun", "stapler", "validate", ticket_target)
            return
    else:
        print(f"Submitting {label} to Apple's notarization service...", flush=True)
        submission = json.loads(run("xcrun", "notarytool", "submit", archive,
                                    "--keychain-profile", profile, "--no-wait",
                                    "--output-format", "json", capture=True))
        submission["sha256"] = digest(archive)
        save_json(submission_file, submission)
    result = json.loads(result_file.read_text()) if result_file.exists() else {}
    if result.get("status") != "Accepted":
        print(f"Waiting for Apple: {submission['id']} (retry with --resume if interrupted)", flush=True)
        # Persist the submission ID before waiting; retries never upload it again.
        process = subprocess.run(["xcrun", "notarytool", "wait", submission["id"],
                                  "--keychain-profile", profile, "--timeout", "10m",
                                  "--output-format", "json"], text=True, capture_output=True)
        if process.stdout.strip():
            result = json.loads(process.stdout)
            save_json(result_file, result)
        if result.get("status") not in {"Accepted", "Invalid", "Rejected"}:
            raise RuntimeError(f"Notarization is incomplete. Run the same command with --resume. {process.stderr.strip()}")
        run("xcrun", "notarytool", "log", submission["id"], "--keychain-profile", profile, log_file)
        if result.get("status") != "Accepted":
            raise RuntimeError(f"Apple rejected {label}; inspect {log_file}.")
    run("xcrun", "stapler", "staple", ticket_target)
    run("xcrun", "stapler", "validate", ticket_target)


def packaging_tools():
    tools = ROOT / "build-macos/dmg-tools"
    python = tools / "bin/python3"
    if not python.exists():
        run(sys.executable, "-m", "venv", tools)
    requirements = HERE / "dmg-requirements.txt"
    marker = tools / "requirements.sha256"
    if not marker.exists() or marker.read_text().strip() != digest(requirements):
        run(python, "-m", "pip", "--disable-pip-version-check", "--no-cache-dir",
            "install", "-r", requirements)
        marker.write_text(digest(requirements) + "\n")
    return tools


def verify_dmg(dmg, app, directory, notarized):
    run("hdiutil", "verify", dmg)
    signature(dmg)
    if notarized:
        run("xcrun", "stapler", "validate", dmg)
        run("spctl", "--assess", "--type", "open", "--context", "context:primary-signature",
            "--verbose=2", dmg)
    with tempfile.TemporaryDirectory(prefix="mount-", dir=directory) as mount:
        attached = False
        try:
            run("hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", mount, dmg)
            attached = True
            mounted = Path(mount)
            verify_app(mounted / "Quadrapassel.app", notarized)
            if tree_digest(mounted / "Quadrapassel.app") != tree_digest(app):
                raise RuntimeError("The app inside the DMG differs from the signed release app.")
            if not (mounted / "Applications").is_symlink() or os.readlink(mounted / "Applications") != "/Applications":
                raise RuntimeError("The Applications installation link is missing or incorrect.")
            run(packaging_tools() / "bin/python3", HERE / "verify-dmg-layout.py", mounted)
        finally:
            if attached:
                run("hdiutil", "detach", mount)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=ROOT / "dist/Quadrapassel.app")
    parser.add_argument("--build-number", required=True, type=int)
    parser.add_argument("--identity", help="Developer ID Application certificate name; private key stays in Keychain")
    parser.add_argument("--notary-profile", help="Existing notarytool Keychain profile name")
    parser.add_argument("--notarize", action="store_true", help="Upload app and DMG to Apple and staple accepted tickets")
    parser.add_argument("--resume", action="store_true", help="Continue the exact same local release without resubmitting uploads")
    args = parser.parse_args()
    if platform.system() != "Darwin" or sys.version_info < (3, 11):
        parser.error("Run on macOS with Python 3.11 or later.")
    if args.build_number < 1:
        parser.error("--build-number must be a positive integer.")
    settings_path = HERE / "release.local.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    if set(settings) - {"signing_identity", "notary_profile"}:
        parser.error("Local settings may contain only signing_identity and notary_profile; keep secrets in Keychain.")
    identity = args.identity or os.environ.get("QUADRAPASSEL_SIGNING_IDENTITY") or settings.get("signing_identity")
    profile = args.notary_profile or os.environ.get("QUADRAPASSEL_NOTARY_PROFILE") or settings.get("notary_profile")
    if not identity or not identity.startswith("Developer ID Application:"):
        parser.error("Configure a Developer ID Application identity; see release.example.json.")
    if args.notarize and not profile:
        parser.error("--notarize requires an existing Keychain profile name.")
    identities = run("security", "find-identity", "-v", "-p", "codesigning", capture=True)
    if f'"{identity}"' not in identities:
        parser.error("The configured Developer ID identity is not available in the unlocked Keychain.")
    source = args.app.resolve()
    run("codesign", "--verify", "--deep", "--strict", source)
    with (source / "Contents/Info.plist").open("rb") as handle:
        info = plistlib.load(handle)
    if info.get("CFBundleIdentifier") != "org.gnome.Quadrapassel":
        parser.error("Expected the Quadrapassel application bundle.")
    version = info["CFBundleShortVersionString"]
    if not re.fullmatch(r"\d+(?:\.\d+){0,2}", version):
        parser.error("Expected a numeric release version in Info.plist.")
    archs = run("lipo", "-archs", source / "Contents/MacOS/quadrapassel", capture=True).split()
    name = f"Quadrapassel-{version}-{args.build_number}-{'-'.join(sorted(archs))}"
    directory = ROOT / "dist/releases" / name
    app = directory / "Quadrapassel.app"
    dmg = directory / f"{name}.dmg"
    state_file = directory / "release-state.json"
    expected = {"source_sha256": tree_digest(source), "identity": identity,
                "notarize": args.notarize, "version": version, "build": args.build_number}
    if directory.exists():
        if not args.resume or not state_file.is_file():
            parser.error(f"Release directory already exists: {directory}. Use --resume for the same input, or a new build number.")
        state = json.loads(state_file.read_text())
        if any(state.get(key) != value for key, value in expected.items()):
            parser.error("Release input or signing options changed; use a new build number.")
    else:
        directory.mkdir(parents=True)
        state = dict(expected, completed=[])
        save_json(state_file, state)
    lock = directory / ".release-lock"
    try:
        lock.mkdir()
    except FileExistsError:
        parser.error(f"A release may already be running. Inspect {lock} before removing a stale lock.")

    def step(label, action):
        if label not in state["completed"]:
            print(f"\n{label}", flush=True)
            action()
            state["completed"].append(label)
            save_json(state_file, state)

    def sign_app():
        if app.exists():
            shutil.rmtree(app)
        shutil.copytree(source, app)
        release_info = dict(info, CFBundleVersion=str(args.build_number))
        with (app / "Contents/Info.plist").open("wb") as handle:
            plistlib.dump(release_info, handle)
        marker = app / "Contents/Resources/quadrapassel-build.json"
        metadata = json.loads(marker.read_text())
        metadata.update(signing="Developer ID; Hardened Runtime; secure timestamp", build=args.build_number)
        save_json(marker, metadata)
        for library in sorted((app / "Contents/Frameworks").iterdir()):
            run("codesign", "--force", "--timestamp", "--sign", identity, library)
        run("codesign", "--force", "--timestamp", "--options", "runtime", "--sign", identity, app)
        verify_app(app)

    def notarize_app():
        archive = directory / "app-notarization.zip"
        if not archive.exists():
            run("ditto", "-c", "-k", "--keepParent", app, archive)
        notarize(archive, app, directory, "app", profile)
        verify_app(app, True)

    def package_dmg():
        verify_app(app, args.notarize)
        tools = packaging_tools()
        background = directory / "dmg-background.png"
        run("rsvg-convert", "-o", background, HERE / "dmg-background.svg")
        temporary = directory / "packaging.dmg"
        if temporary.exists():
            temporary.unlink()
        run(tools / "bin/dmgbuild", "-s", HERE / "dmg-settings.py", "-D", f"app={app}",
            "-D", f"background={background}", "Quadrapassel", temporary)
        run("codesign", "--force", "--timestamp", "--sign", identity, temporary)
        verify_dmg(temporary, app, directory, False)
        temporary.replace(dmg)

    try:
        step("Sign application", sign_app)
        if args.notarize:
            step("Notarize application", notarize_app)
        step("Package and sign disk image", package_dmg)
        if args.notarize:
            step("Notarize disk image", lambda: notarize(dmg, dmg, directory, "dmg", profile))
        # Always reverify on --resume, even when all checkpoints were completed.
        verify_app(app, args.notarize)
        verify_dmg(dmg, app, directory, args.notarize)
        checksum = dmg.with_suffix(".dmg.sha256")
        checksum.write_text(f"{digest(dmg)}  {dmg.name}\n")
        print(f"\nVerified {'notarized' if args.notarize else 'signed (not notarized)'} DMG: {dmg}")
    finally:
        lock.rmdir()


if __name__ == "__main__":
    main()
