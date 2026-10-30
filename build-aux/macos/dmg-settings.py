# SPDX-License-Identifier: GPL-3.0-or-later
"""Finder layout consumed by dmgbuild; all paths are supplied by release.py."""
from pathlib import Path

app = Path(defines["app"]).resolve()
format = "UDZO"
filesystem = "HFS+"
files = [(str(app), "Quadrapassel.app")]
symlinks = {"Applications": "/Applications"}
icon = str(app / "Contents/Resources/Quadrapassel.icns")
background = defines["background"]
window_rect = ((180, 180), (640, 420))
default_view = "icon-view"
show_toolbar = False
show_sidebar = False
show_status_bar = False
show_pathbar = False
show_tab_view = False
include_icon_view_settings = True
include_list_view_settings = False
icon_size = 96
text_size = 14
icon_locations = {"Quadrapassel.app": (175, 230), "Applications": (465, 230)}
# Finder flags are part of the signed bundle; don't mutate them during packaging.
hide_extensions = []
