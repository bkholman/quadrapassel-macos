/* SPDX-License-Identifier: GPL-3.0-or-later */

/* Installed Linux builds use Meson's paths; a Mac app resolves its own resources. */
namespace RuntimePaths {
    private string? resources = null;

    public void initialize () {
#if MACOS
        resources = MacOS.initialize_bundle ();
#endif
    }

    public string sounds () {
        if (resources != null)
            return Path.build_filename (resources, "share", "sounds", "quadrapassel");
        return SOUND_DIRECTORY;
    }

    public string locale () {
        if (resources != null)
            return Path.build_filename (resources, "share", "locale");
        return LOCALEDIR;
    }
}
