#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Upload a verified macOS DMG and checksum to GitHub; --publish makes it public."""

import argparse
import json
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

from release import ROOT, digest, run, save_json, verify_app, verify_dmg


def local_release(directory):
    state = json.loads((directory / "release-state.json").read_text())
    required = {"Sign application", "Notarize application", "Package and sign disk image",
                "Notarize disk image"}
    if not state.get("notarize") or not required.issubset(state.get("completed", [])):
        raise RuntimeError("Finish signing and notarizing this release before uploading it.")
    for label in ("app", "dmg"):
        result = json.loads((directory / f"{label}-result.json").read_text())
        if result.get("status") != "Accepted":
            raise RuntimeError(f"Apple has not accepted the {label}.")
    app = directory / "Quadrapassel.app"
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    version, build = info["CFBundleShortVersionString"], info["CFBundleVersion"]
    if (info.get("CFBundleIdentifier") != "org.gnome.Quadrapassel" or
            not re.fullmatch(r"\d+(?:\.\d+){0,2}", version) or
            not re.fullmatch(r"[1-9]\d*", build) or
            state.get("version") != version or str(state.get("build")) != build):
        raise RuntimeError("The app and release metadata do not match.")
    archs = run("lipo", "-archs", app / "Contents/MacOS/quadrapassel", capture=True).split()
    name = f"Quadrapassel-{version}-{build}-{'-'.join(sorted(archs))}"
    dmg = directory / f"{name}.dmg"
    checksum = directory / f"{name}.dmg.sha256"
    if checksum.read_text().split() != [digest(dmg), dmg.name]:
        raise RuntimeError("The DMG does not match its checksum file.")
    return app, dmg, checksum, version, build


def api(endpoint, *args):
    return json.loads(run("gh", "api", "--hostname", "github.com", endpoint,
                          *args, capture=True))


def tag_commit(repo, tag):
    refs = api(f"repos/{repo}/git/matching-refs/tags/{quote(tag, safe='')}")
    reference = next((ref for ref in refs if ref["ref"] == f"refs/tags/{tag}"), None)
    if reference is None:
        return None
    obj = reference["object"]
    while obj["type"] == "tag":
        obj = api(f"repos/{repo}/git/tags/{obj['sha']}")["object"]
    if obj["type"] != "commit":
        raise RuntimeError("The release tag must point to a commit.")
    return obj["sha"]


def verify_assets(repo, tag, release, files):
    assets = {asset["name"]: asset for asset in release["assets"]}
    if set(assets) != {path.name for path in files}:
        raise RuntimeError("Expected exactly the DMG and its checksum as release assets.")
    # Downloading also verifies uploads on GitHub versions without asset digests.
    with tempfile.TemporaryDirectory(prefix="quadrapassel-download-") as temporary:
        for path in files:
            asset = assets[path.name]
            if asset["state"] != "uploaded" or asset["size"] != path.stat().st_size:
                raise RuntimeError(f"Incomplete or different upload: {path.name}")
            run("gh", "release", "download", tag, "--repo", f"github.com/{repo}",
                "--pattern", path.name, "--dir", temporary)
            if digest(Path(temporary) / path.name) != digest(path):
                raise RuntimeError(f"Downloaded asset differs from the local release: {path.name}")
    print("Verified both uploaded files against their local SHA-256 digests.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_dir", type=Path, help="Completed directory under dist/releases")
    parser.add_argument("--repo", required=True, help="Destination GitHub OWNER/REPO")
    parser.add_argument("--target", required=True, help="Git commit used to build this app")
    parser.add_argument("--notes-file", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--publish", action="store_true", help="Publish after verifying both uploads")
    mode.add_argument("--check", action="store_true", help="Validate locally and on GitHub without uploading")
    args = parser.parse_args()
    if platform.system() != "Darwin" or sys.version_info < (3, 11):
        parser.error("Run on macOS with Python 3.11 or later.")
    if not shutil.which("gh"):
        parser.error("Install GitHub CLI with brew install gh, then run gh auth login.")
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo must be a GitHub OWNER/REPO, without a URL or hostname.")
    notes = args.notes_file.resolve()
    if not notes.is_file() or not notes.read_text().strip():
        parser.error("Supply a non-empty release notes file.")
    directory = args.release_dir.resolve()
    app, dmg, checksum, version, build = local_release(directory)
    tag = f"macos-{version}-{build}"
    title = f"Quadrapassel {version} — macOS build {build}"
    target = run("git", "rev-parse", "--verify", "--end-of-options",
                 f"{args.target}^{{commit}}", capture=True, cwd=ROOT)
    repo = args.repo
    destination = api(f"repos/{repo}")
    if not destination.get("permissions", {}).get("push"):
        raise RuntimeError("Sign into GitHub CLI with an account that can publish to this repository.")
    if api(f"repos/{repo}/commits/{target}")["sha"] != target:
        raise RuntimeError("Push the source commit to GitHub before creating its release.")
    remote_target = tag_commit(repo, tag)
    if remote_target is not None and remote_target != target:
        raise RuntimeError("This tag already points to a different commit; use a new build number.")
    pages = api(f"repos/{repo}/releases?per_page=100", "--paginate", "--slurp")
    release = next((item for page in pages for item in page if item["tag_name"] == tag), None)
    if release is not None:
        if remote_target is None and release["target_commitish"] != target:
            raise RuntimeError("The existing draft has a different source commit.")
        if release["name"] != title or (release.get("body") or "").strip() != notes.read_text().strip():
            raise RuntimeError("Existing release notes/title differ; review them before retrying.")
        if release["prerelease"]:
            raise RuntimeError("This tag belongs to a prerelease; review it before continuing.")
        if {asset["name"] for asset in release["assets"]} - {dmg.name, checksum.name}:
            raise RuntimeError("The existing release has unexpected assets; review it before continuing.")

    verify_app(app, notarized=True)
    verify_dmg(dmg, app, directory, notarized=True)
    print(f"Release: {repo}, {tag}, source {target}", flush=True)
    print(f"Assets: {dmg.name}, {checksum.name}", flush=True)
    if args.check:
        print("Checks passed; no GitHub changes made.")
        return
    if release is None:
        run("gh", "release", "create", tag, "--repo", f"github.com/{repo}", "--draft",
            "--target", target, "--title", title, "--notes-file", notes)
        release_id = json.loads(run("gh", "release", "view", tag, "--repo", f"github.com/{repo}",
                                    "--json", "databaseId", capture=True))["databaseId"]
        release = api(f"repos/{repo}/releases/{release_id}")
    if release["draft"]:
        names = {asset["name"] for asset in release["assets"]}
        for path in (dmg, checksum):
            if path.name not in names:
                # No --clobber: retrying never replaces an uploaded artifact.
                run("gh", "release", "upload", tag, path, "--repo", f"github.com/{repo}")
        release = api(f"repos/{repo}/releases/{release['id']}")
    verify_assets(repo, tag, release, (dmg, checksum))
    if args.publish and release["draft"]:
        if tag_commit(repo, tag) not in (None, target):
            raise RuntimeError("The tag changed during upload; leaving the release as a draft.")
        run("gh", "release", "edit", tag, "--repo", f"github.com/{repo}",
            "--draft=false", "--latest", "--target", target)
        release = api(f"repos/{repo}/releases/{release['id']}")
    if not release["draft"] and tag_commit(repo, tag) != target:
        raise RuntimeError("The published release tag does not match the requested source commit.")
    save_json(directory / "github-release.json", {
        "repository": repo, "tag": tag, "source_commit": target,
        "url": release["html_url"], "draft": release["draft"],
        "assets": {path.name: digest(path) for path in (dmg, checksum)},
    })
    print(f"{'Draft' if release['draft'] else 'Published'} release: {release['html_url']}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
