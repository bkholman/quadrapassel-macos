# Quadrapassel on macOS

The macOS port keeps the Vala, GTK4, and libadwaita interface and game engine.
It uses the native macOS display backend and keyboard input. Linux keeps its
existing desktop integration and controller support.

## Build a self-contained app

Install Apple's Command Line Tools (`xcode-select --install`) and these Homebrew
build dependencies:

```sh
brew install vala gtk4 libadwaita adwaita-icon-theme hicolor-icon-theme \
  meson ninja pkgconf gettext blueprint-compiler libsndfile openal-soft librsvg
```

From the repository root:

```sh
python3 build-aux/macos/build-app.py
open dist/Quadrapassel.app
```

The result is `dist/Quadrapassel.app`. You can move it to Applications or another
folder and open it in Finder. Homebrew, Python, Vala, and the build tools are
needed to **build**, but are not needed to **run** the resulting app.

The script builds and installs into `build-macos/install`, copies all transitive
non-system libraries into the app, rewrites their references to relative paths,
bundles resources and license notices, and applies an ad-hoc signature for local
use. It checks library architectures, missing dependencies, external symlinks,
and the signature before replacing a previous generated app.

Optional output locations:

```sh
python3 build-aux/macos/build-app.py --build-dir build-macos-release --output-dir dist
```

Quit the app before rebuilding it. Generated builds and bundles are ignored by Git.

## Architecture and minimum macOS version

The script builds for the architecture of the active compiler and Homebrew
installation. The first tested bundle is **Apple silicon (arm64), macOS 27.2 or
later**. Its minimum version is calculated from the executable and every bundled
library and stored in `Contents/Info.plist`, rather than promising support below
the dependencies' actual requirements.

The scripts do not hard-code `/opt/homebrew`, so they can also be used with an
Intel Homebrew installation. An Intel build still needs to be produced and tested
on an Intel Mac or an appropriate x86_64 build environment. This is not yet a
universal binary. Supporting older macOS versions requires rebuilding with a
compatible SDK deployment target and dependencies that support those versions;
editing the app's plist alone is insufficient.

## Controls and saved data

| Action | Mac shortcut |
| --- | --- |
| New game | Command-N; Return when no game is active |
| Preferences | Command-comma |
| Keyboard shortcuts | Command-Shift-/ |
| Close window | Command-W |
| Quit | Command-Q |
| Pause/resume | P |
| Move | Left/Right or A/D |
| Rotate | Up/W, Q, or E |
| Move down | Down/S |
| Drop | Space |
| Hold | H |

GTK4 represents Command as `Meta`; the Mac build sets those accelerators explicitly.
Modified key presses are passed through to GTK so, for example, Command-Q does
not rotate a piece. Native Game and Help menus complement the existing in-window
menu. The interface otherwise retains its GNOME appearance.

Preferences use a persistent GSettings key-file backend, without requiring a
D-Bus session. They are stored under GLib's user data directory in
`org.gnome.Quadrapassel/preferences.ini`. High scores remain under
`quadrapassel/scores` in the same user data directory. On macOS that directory is
`~/.local/share` with the tested Homebrew GLib build; `XDG_DATA_HOME` can override it.
The app resolves resources relative to its executable, including when renamed or
moved. Image-loader cache files are written under GLib's user cache directory,
outside the signed app bundle.

## Validation

Run the existing score tests:

```sh
XDG_DATA_HOME="$PWD/build-macos/test-data" meson test -C build-macos --print-errorlogs
```

Run the bundle integration test on macOS with an available audio output:

```sh
python3 build-aux/macos/test-bundle.py
```

This copies the app to a temporary path containing spaces, renames it, compiles
a small resource probe, and runs it twice with a clean environment and isolated
preferences. It checks SVG loading, settings persistence between processes, all
eight Ogg sound files and OpenAL playback initialization, loaded-library paths,
and code signatures. The original bundle and user preferences are untouched.

Also test through Finder: start a game, move/rotate/drop pieces, pause, change a
theme, reopen Preferences, view rules and scores, quit, and relaunch. Check the
Command shortcuts and try moving the app to another folder. A clean Mac without
Homebrew remains a useful release test beyond the automated dependency checks.

## Linux builds

The normal Meson commands still apply. Gamepad support defaults to enabled on
Linux, with libmanette and Linux input headers required as before. To build with
keyboard input only:

```sh
meson setup build -Dgamepad=disabled
meson compile -C build
meson test -C build --print-errorlogs
```

On macOS gamepads are disabled automatically; requesting `-Dgamepad=enabled`
reports that the controller backend requires Linux. Linux desktop, D-Bus, and
AppStream files are omitted from the Mac install.

## Releases and licensing

The generated app is signed locally, not Developer ID signed or notarized for
public distribution. Public releases should add Developer ID signing and Apple
notarization, and be tested on the supported architectures and macOS versions.

Quadrapassel's GPL-3.0-or-later license and existing author credits are retained.
The bundled libgnome-games-support source retains its LGPL-3.0-or-later license.
`Contents/Resources/licenses` contains their license texts, installed third-party
notices, dependency versions, Homebrew formulae with source URLs/build recipes,
and available SPDX metadata. Publish matching source and build instructions with
releases, and satisfy each bundled component's source and redistribution terms;
the generated notice directory is not a corresponding-source archive.

Development can remain on the private Gitea remote. Building the app does not
publish, commit, push, or change the repository's remotes.

Reference: [GTK's macOS integration documentation](https://docs.gtk.org/gtk4/osx.html).
