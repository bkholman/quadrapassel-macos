# Quadrapassel

Fit falling blocks together: move and rotate pieces to complete rows, clear the
board, and earn points.

This fork of [GNOME Quadrapassel](https://gitlab.gnome.org/GNOME/quadrapassel)
adds a native macOS port, optional Classic scoring, language selection, and
visual refinements. It retains the Vala, GTK4, and libadwaita interface, existing
gameplay features, themes, sounds, and Linux desktop integration.

## macOS app

- A self-contained `Quadrapassel.app` runs with the native macOS display backend
  and keeps the GNOME-style interface. Homebrew and the build tools are not needed
  to run the packaged app.
- Native Game and Help menus and Command shortcuts integrate with macOS.
  Command shortcuts work independently of the game's movement and rotation keys.
- Gameplay uses keyboard controls on macOS. Linux retains its controller support,
  with an optional keyboard-only build.
- Preferences, high scores, and window size are saved between launches. The app
  continues to find its sounds, icons, and translations when moved or renamed.
- Repeatable scripts produce a signed, notarized drag-to-Applications DMG and
  verify both the app and disk image.

The current tested bundle is **Apple silicon (arm64), macOS 27.2 or later**.
Intel builds are not yet tested, and the app is not a universal binary. Each
build derives its minimum macOS version from its bundled dependencies.

| Action | Mac shortcut |
| --- | --- |
| New game | Command-N |
| Preferences | Command-comma |
| Keyboard shortcuts | Command-Shift-/ |
| Close window | Command-W |
| Quit | Command-Q |

During play, use Left/Right or A/D to move, Up/W to rotate in the preferred
direction, Q/E to rotate left/right, Down/S to move down, Space to drop, H to
hold, and P to pause or resume. Return starts a game when none is active.

## Scoring rules

In **Preferences → Game → Scoring → Scoring rules**, choose **Modern** (the
default) or **Classic (40.2)**. The difference is the extra bonus awarded when
a clear includes the bottom row:

| Rule | Bottom-row bonus |
| --- | --- |
| Modern | `100 × level × rows cleared` |
| Classic (40.2) | `10000 × level`, regardless of the number of rows cleared |

Both rules also award the regular line-clear points: `40 × level`, `100 × level`,
`300 × level`, or `1200 × level` for clearing one, two, three, or four rows
respectively. Classic restores version 40.2's scoring
for the same clear at the same level while retaining the newer gameplay features.

Changing the rule warns that the scoreboard may contain scores from different
rules and offers **Keep Scores**, **Reset Scoreboard**, or **Cancel**. Resetting
clears scores for every difficulty, including imported scores. The selected rule
applies to new games; a running game keeps its original rule. If you reset while
a game is running, it can continue, but its score will not be saved.

The starting difficulty remains **0** by default: level 1 with an empty board.

## Appearance

- **Preferences → Appearance → Show grid outlines** adds thin, light grey borders
  around empty cells. It is **off by default**, applies immediately to the board
  and appearance preview, and is saved between launches. The outlines use 45%
  opacity, work with all themes, and stay aligned when the window is resized.
- **Preferences → Game → In-Game → Show where the block will land** displays the
  landing preview at **37.5% opacity**, reduced from the upstream 50%. The option
  remains **off by default**; opacity is fixed rather than a separate preference.

To make the board larger, resize or maximize the window. The blocks and grid are
drawn at the new size, keeping their edges sharp. There is no separate zoom setting.

## Languages

**Preferences → Appearance → Language** provides **System** (the default),
English, and the installed GNOME translations in a searchable list using their
native names. Restart Quadrapassel to apply a language change.

On macOS, System follows the OS's preferred languages, including an app-specific
language selected in Language & Region. Regional and script variants map to the
available translations; unsupported choices fall through to the next preferred
language, then English. Linux's System choice follows its locale environment.

A manual selection affects only Quadrapassel, including its native Mac
application menu. Translations for the game, scoreboard, and interface libraries
are included in the app bundle, and right-to-left languages use a right-to-left
layout. Translation coverage varies, especially for newly added controls;
untranslated text falls back to English.

## Build and package

### macOS

Install the dependencies listed in [MACOS.md](MACOS.md#build-a-self-contained-app),
then run from the repository root:

```sh
python3 build-aux/macos/build-app.py
open dist/Quadrapassel.app
```

This creates an ad-hoc-signed app for local use. The separate
[`release.py`](build-aux/macos/release.py) script creates versioned DMGs, signs
the app and bundled libraries with Developer ID and Hardened Runtime, notarizes
the app and DMG when requested, staples Apple's tickets, and verifies Gatekeeper
acceptance. It also checks the packaged app and Finder layout and generates a
SHA-256 checksum. Interrupted notarization can be resumed.

See [Signed DMG releases](MACOS.md#signed-dmg-releases) for machine setup,
build-number selection, signing, notarization, and verification commands.
Developer keys and notarization credentials stay in Keychain; local signing
configuration and generated artifacts are ignored by Git. The scripts do not
publish releases automatically.

The [validation instructions](MACOS.md#validation) cover scoring, scoreboard
reset, language selection, and bundle checks for relocated apps, persistent
settings, sounds, translations, and signatures. [Controls and saved data](MACOS.md#controls-and-saved-data)
documents Mac shortcuts and preference and score locations.

### Linux

The normal Meson build remains available with the existing development dependencies:

```sh
meson setup build
meson compile -C build
meson test -C build --print-errorlogs
meson install -C build
```

Controller support is enabled by default on Linux. Use
`meson setup build -Dgamepad=disabled` for a keyboard-only build. Scoring selection,
language selection, grid outlines, and the lighter landing preview are shared
with Linux; macOS packaging and integration are platform-specific.

## Credits and licensing

Original GNOME author credits are retained. The About dialog credits
**Brian Holman (MacOS port)** below Will Warner.

Quadrapassel remains licensed under **GPL-3.0-or-later**; see [COPYING](COPYING).
The included libgnome-games-support retains its **LGPL-3.0-or-later** license.
Mac bundles include third-party notices and dependency information in
`Contents/Resources/licenses`. See [Licensing](MACOS.md#licensing) for distribution
and source information.

This project follows [GNOME's Code of Conduct](https://conduct.gnome.org/).
