#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the installed Finder layout in a mounted Quadrapassel disk image."""
from pathlib import Path
import re
import sys

from ds_store import DSStore

mount = Path(sys.argv[1])
with DSStore.open(str(mount / ".DS_Store"), "r") as store:
    view = store["."]["icvl"]
    if view != (b"type", b"icnv"):
        raise RuntimeError(f"The installer must open in Finder Icon View: {view!r}")
    window = store["."]["bwsp"]
    bounds = [int(value) for value in re.findall(r"\d+", window["WindowBounds"])]
    width, height = bounds[-2:]
    icons = store["."]["icvp"]
    if icons["backgroundType"] != 2 or not icons.get("backgroundImageAlias"):
        raise RuntimeError("The installer background is not configured.")
    if not (mount / ".background.png").is_file():
        raise RuntimeError("The installer background image is missing.")
    locations = [store[name]["Iloc"] for name in ("Quadrapassel.app", "Applications")]
    radius = icons["iconSize"] / 2
    for x, y in locations:
        if not (radius < x < width - radius and radius < y < height - radius - 30):
            raise RuntimeError("An installer icon or its label would be outside the window.")
    if abs(locations[0][0] - locations[1][0]) <= 2 * radius:
        raise RuntimeError("Installer icons overlap.")
    try:
        store["."]["pBBk"]
    except KeyError:
        pass
    else:
        raise RuntimeError("The installer contains an incompatible background bookmark.")
print("PASS: Finder Icon View, background, and visible installation icons")
