/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "macos-support.h"
#include <mach-o/dyld.h>
#include <stdlib.h>
#include <string.h>

static void
set_resource_path (const char *variable, const char *resources, const char *relative)
{
    g_autofree gchar *path = g_build_filename (resources, relative, NULL);
    g_setenv (variable, path, TRUE);
}

gchar *
quadrapassel_macos_initialize_bundle (void)
{
    uint32_t size = 0;
    _NSGetExecutablePath (NULL, &size);
    g_autofree gchar *executable = g_malloc (size);
    if (_NSGetExecutablePath (executable, &size) != 0)
        return NULL;

    g_autofree gchar *resolved = realpath (executable, NULL);
    if (resolved == NULL)
        return NULL;
    g_autofree gchar *bin_dir = g_path_get_dirname (resolved);
    if (!g_str_has_suffix (bin_dir, ".app/Contents/MacOS"))
        return NULL; /* An ordinary Meson build or installation. */

    g_autofree gchar *contents = g_path_get_dirname (bin_dir);
    gchar *resources = g_build_filename (contents, "Resources", NULL);
    set_resource_path ("GSETTINGS_SCHEMA_DIR", resources, "share/glib-2.0/schemas");
    set_resource_path ("XDG_DATA_DIRS", resources, "share");
    set_resource_path ("GIO_MODULE_DIR", resources, "lib/gio/modules");
    set_resource_path ("FONTCONFIG_FILE", resources, "etc/fonts/fonts.conf");
    g_setenv ("GDK_BACKEND", "macos", TRUE);

    /* Loader caches contain absolute paths. Materialize the bundled template in
     * the user's cache, so moving the signed app never modifies its contents. */
    g_autofree gchar *template_path = g_build_filename (resources, "loaders.cache.in", NULL);
    g_autofree gchar *template = NULL;
    g_autoptr(GError) error = NULL;
    if (!g_file_get_contents (template_path, &template, NULL, &error))
        g_error ("Cannot read bundled image loaders: %s", error->message);

    g_autofree gchar *frameworks = g_build_filename (contents, "Frameworks", NULL);
    g_autofree gchar *escaped = g_strescape (frameworks, NULL);
    g_auto(GStrv) parts = g_strsplit (template, "@FRAMEWORKS@", -1);
    g_autofree gchar *cache = g_strjoinv (escaped, parts);
    g_autofree gchar *hash = g_compute_checksum_for_string (G_CHECKSUM_SHA256, resources, -1);
    g_autofree gchar *cache_dir = g_build_filename (g_get_user_cache_dir (), APP_ID, hash, NULL);
    g_autofree gchar *cache_path = g_build_filename (cache_dir, "loaders.cache", NULL);
    if (g_mkdir_with_parents (cache_dir, 0700) != 0 ||
        !g_file_set_contents (cache_path, cache, -1, &error))
        g_error ("Cannot prepare bundled image loaders: %s", error ? error->message : "cannot create cache directory");
    g_setenv ("GDK_PIXBUF_MODULE_FILE", cache_path, TRUE);
    return resources;
}
