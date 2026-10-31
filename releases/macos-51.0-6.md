# Quadrapassel 51.0 — macOS build 6

The first public macOS release of this Quadrapassel fork, with a self-contained
GTK4/libadwaita app and the gameplay options developed for the port.

## Download and install

Requires **Apple silicon (arm64) and macOS 27.2 or later**. Intel Macs are not
supported by this download.

1. Download `Quadrapassel-51.0-6-arm64.dmg` from the assets below.
2. Open the DMG and drag **Quadrapassel** to **Applications**.
3. Open Quadrapassel from Applications.

The app and DMG are Developer ID signed, notarized by Apple, and have their
notarization tickets stapled. Homebrew and the build tools are not needed to play.

## Included changes

- Native Mac Game and Help menus, Command shortcuts, and keyboard gameplay.
- Persistent preferences and high scores; the app can be moved or renamed.
- **Modern** scoring (default) or **Classic (40.2)** scoring, with a choice to keep
  or reset the scoreboard when changing rules. New rules apply to the next game.
- **System** language selection (default), manual overrides, bundled GNOME
  translations, and right-to-left layout. Restart to apply a language change.
- Optional **Show grid outlines**, off by default, with subtle translucent grey
  borders that scale with the board.
- A lighter landing preview at **37.5% opacity** when **Show where the block will
  land** is enabled.
- Existing themes, sounds, difficulty controls, and resizable game board.

## Verify the download

Download the accompanying `.dmg.sha256` file into the same folder as the DMG,
then run:

```sh
shasum -a 256 -c Quadrapassel-51.0-6-arm64.dmg.sha256
```

This installer was built from commit
[`9099f8c`](https://github.com/bkholman/quadrapassel/commit/9099f8c981a97416e0282c1293c288682ee3a0e6).
The `macos-51.0-6` tag and GitHub's source archives identify the matching application
source. Build and release instructions are in
[MACOS.md](https://github.com/bkholman/quadrapassel/blob/main/MACOS.md).

Quadrapassel retains its GPL-3.0-or-later license and GNOME author credits, with
Brian Holman credited for the MacOS port. Bundled dependency notices, versions,
and source/build references are included in the app's `Contents/Resources/licenses`
directory. Translation coverage varies; missing text falls back to English.
