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

In **Preferences → Appearance**, **Show grid outlines** adds thin, translucent grey
outlines to the empty board cells. It is off by default, applies immediately to
the game and appearance preview, and is remembered between launches. The outlines
stay aligned with the pieces when the window is resized and work with every theme.

In **Preferences → Game → Scoring → Scoring rules**, choose **Modern** (the default)
or **Classic (40.2)**. When a clear includes the bottom row, Modern adds
`100 × level × rows cleared`; Classic adds a flat `10000 × level`, regardless of
how many rows were cleared. Regular line-clear points are unchanged. Classic
matches version 40.2's points for the same clear at the same level; newer gameplay
features and difficulty settings remain available.

The earlier bonus switch's saved preference carries over: On selects Modern and
Off selects Classic. The intermediate pre-April 2026 formula is no longer offered.
Existing scores are retained unless you choose to reset them; scores earned under
that intermediate formula remain in the scoreboard too.

Changing the scoring rules offers **Keep Scores**, **Reset Scoreboard**, or **Cancel**.
Reset clears scores for every difficulty, including imported old scores; keeping
them permits scores from both rules in the same scoreboard. Cancel leaves the
setting and scores unchanged. The selected rule applies to new games. A running
game keeps its original rule, and resetting prevents that game's score from
being saved on game over or when quitting.

## Languages

**Preferences → Appearance → Language** offers **System** (the default), English,
and the installed GNOME translations, listed by their native names in a searchable
menu. Reopen Quadrapassel after changing the selection; a running game is not
interrupted. Selecting System again restores automatic selection on the next
launch. A manual choice is stored in the same preferences file as the other settings.

On macOS, System reads the OS's ordered preferred languages, including an app
language selected in macOS Language & Region. Region and script variants map to
the GNOME catalogs (for example, `pt-BR` → `pt_BR`, `zh-Hant` → `zh_TW`, and
`sr-Latn` → `sr@latin`). Unsupported languages fall through to the next OS preference,
then English. Manual overrides affect only Quadrapassel, including its native
application menu, and never write macOS language settings. Linux's System option
continues to use its locale environment.

The app advertises its bundled languages in `Info.plist` and resolves the app,
scoreboard, GTK, libadwaita, GLib and GdkPixbuf translation domains inside the bundle.
No Homebrew installation is needed to load translations. Right-to-left languages
use a right-to-left interface. Translation coverage varies by language; missing
strings fall back to English. The new language controls include translations in
German, Spanish, French, Italian, Japanese, Brazilian Portuguese, Russian,
Ukrainian, Simplified Chinese and Traditional Chinese. The new scoring controls
also have German, Spanish and French translations.

`data/languages.json` holds native names and macOS language tags;
`po/LINGUAS` remains the upstream list of translation catalogs. The build generates
the selector's registry from both and fails if a newly added language lacks metadata.
Only installed catalogs appear in the selector and macOS bundle declaration.

## Validation

Run the game scoring and scoreboard tests:

```sh
XDG_DATA_HOME="$PWD/build-macos/test-data" meson test -C build-macos --print-errorlogs
```

Run the bundle integration test on macOS with an available audio output:

```sh
python3 build-aux/macos/test-bundle.py
python3 build-aux/macos/test-localization.py
```

This copies the app to a temporary path containing spaces, renames it, compiles
a small resource probe, and runs it twice with a clean environment and isolated
preferences. It checks SVG loading, settings persistence between processes, all
eight Ogg sound files and OpenAL playback initialization, loaded-library paths,
and code signatures. The original bundle and user preferences are untouched.

The localization test runs a probe in a temporary renamed app with isolated data.
It checks System and manual choices, language/script/region fallbacks, English,
right-to-left layout, app/GTK/libadwaita translations, bundled domain paths,
macOS language metadata and the relocated signature. Its simulated OS preferences
exist only in the test process; your macOS settings are not changed.

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

## Signed DMG releases

`build-app.py` still produces the ad-hoc development app. The separate
`build-aux/macos/release.py` script copies that app to a versioned release folder,
signs every bundled library and the app with Developer ID, enables Hardened
Runtime, and creates a signed drag-to-Applications DMG. With `--notarize`, it
uploads the app and then the DMG to Apple, retains submission IDs and diagnostics,
staples accepted tickets, and verifies Gatekeeper acceptance. It never publishes
to a website, GitHub, or the App Store.

All release tooling lives in this repository. The workflow follows the useful
steps from the LoanExplorer release process, without depending on that checkout,
its app identifiers, its cloud configuration, or its proprietary artwork.

### One-time machine setup

Keep the **Developer ID Application** certificate and its private key in macOS
Keychain. Use an existing `notarytool` Keychain profile for the Apple account;
the email address alone is not a signing identity. No key export is needed.

```sh
cp build-aux/macos/release.example.json build-aux/macos/release.local.json
```

Edit the ignored local JSON with the installed certificate's display name and
the existing Keychain profile's name. Those are references, not passwords or key
contents. The script accepts only those two settings. Alternatively, supply
`QUADRAPASSEL_SIGNING_IDENTITY` and `QUADRAPASSEL_NOTARY_PROFILE` in the environment,
or use `--identity` and `--notary-profile`. Command-line values take precedence.

The local settings file, release outputs, common private-key/certificate formats,
provisioning profiles, and local environment files are ignored by Git. Never
force-add credentials. The checked-in example contains placeholders only.

The release script creates a local Python environment under
`build-macos/dmg-tools` and installs the pinned versions from
`build-aux/macos/dmg-requirements.txt` when necessary. Packaging requires Python
3.11+, Apple's command-line signing/disk-image tools, and the build dependencies
listed above. Keychain access and internet access to Apple are required for
timestamped signatures and notarization; the first tooling setup also uses PyPI.

### Build, sign, and notarize

```sh
python3 build-aux/macos/build-app.py
python3 build-aux/macos/test-bundle.py
python3 build-aux/macos/release.py --build-number 1 --notarize
```

Use a new positive build number for a changed candidate. For version 51.0, build
1, and Apple silicon, the output is:

```text
dist/releases/Quadrapassel-51.0-1-arm64/
  Quadrapassel.app
  Quadrapassel-51.0-1-arm64.dmg
  Quadrapassel-51.0-1-arm64.dmg.sha256
  release-state.json
  app-submission.json / app-result.json / app-log.json
  dmg-submission.json / dmg-result.json / dmg-log.json
```

The script checks the app inside a read-only mount of the DMG, compares it to the
signed source app, verifies the Applications link and Finder icon/background layout,
and writes the final checksum
only after successful verification. It uses no extra Hardened Runtime exceptions.
Apple silicon/Intel support and minimum macOS version remain those of the input
app; signing does not make the current arm64 build universal.

Omit `--notarize` to produce signed local artifacts without uploading to Apple.
That mode does not claim notarization or Gatekeeper acceptance.

### Retry and verify

If a submission times out or the process is interrupted:

```sh
python3 build-aux/macos/release.py --build-number 1 --notarize --resume
```

Resume requires the same input bundle and signing options. It uses saved
submission IDs instead of uploading again, skips completed stages, and repeats
the final checks. It also works as a verification command for a completed local
release. Preserve the original development bundle until preparation completes;
rebuilding it changes the input fingerprint. A lock prevents simultaneous work
on the same release. After an abrupt termination, confirm no release process is
running before removing a stale `.release-lock` directory inside that release.

To test relocated resources under Developer ID signing and Hardened Runtime:

```sh
python3 build-aux/macos/test-bundle.py \
  dist/releases/Quadrapassel-51.0-1-arm64/Quadrapassel.app \
  --identity 'Developer ID Application: Your Name (TEAMID)'
```

This signs only a temporary test copy and probe; it leaves the release untouched.
Test the signed app's UI as well. Retain completed artifacts for distribution
instead of silently replacing a published release with rebuilt bytes.

References: Apple's [distribution signing](https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac/)
and [notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).

## Publish a GitHub release

The separate `build-aux/macos/publish-release.py` script uploads an existing,
completed notarized release. Install GitHub CLI and sign in once:

```sh
brew install gh
gh auth login --hostname github.com --git-protocol ssh --web --skip-ssh-key
```

Follow the browser device-code flow as the repository owner. GitHub CLI manages
the login outside this checkout; do not put a GitHub token in source files or
release notes. Git push over SSH alone does not authorize release uploads.

For the existing 51.0 build 6 installer:

```sh
python3 build-aux/macos/publish-release.py \
  dist/releases/Quadrapassel-51.0-6-arm64 \
  --repo bkholman/quadrapassel \
  --target 9099f8c981a97416e0282c1293c288682ee3a0e6 \
  --notes-file releases/macos-51.0-6.md \
  --publish
```

For each new release, supply its completed release directory, the exact source
commit used to build it (already pushed to GitHub), and a matching notes file.
The script derives the tag `macos-VERSION-BUILD` from the app metadata. Supply
your own `OWNER/REPO` when publishing from another fork.

The script checks the checksum, notarization, signatures, Gatekeeper acceptance,
DMG contents, and source commit before uploading. It creates a draft, uploads
only the DMG and checksum, downloads both to verify their SHA-256 digests, and
then publishes when `--publish` is supplied. GitHub also provides source archives
for the release tag. Local configuration and Apple submission logs are not uploaded.

Use `--check` instead of `--publish` to validate without changing GitHub. Omit
both flags to leave a draft. Repeating the same command resumes missing uploads
or verifies an already published release; it never replaces an existing asset
or moves a tag. Conflicting metadata or assets require review. A local
`github-release.json` receipt is saved alongside the ignored release artifacts.

## Licensing

Quadrapassel's GPL-3.0-or-later license and existing author credits are retained.
The bundled libgnome-games-support source retains its LGPL-3.0-or-later license.
`Contents/Resources/licenses` contains their license texts, installed third-party
notices, dependency versions, Homebrew formulae with source URLs/build recipes,
and available SPDX metadata. Publish matching source and build instructions with
releases, and satisfy each bundled component's source and redistribution terms;
the generated notice directory is not a corresponding-source archive.

Building the app does not publish, commit, push, or change the repository's remotes.

Reference: [GTK's macOS integration documentation](https://docs.gtk.org/gtk4/osx.html).
