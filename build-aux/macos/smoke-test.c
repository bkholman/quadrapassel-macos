/* SPDX-License-Identifier: GPL-3.0-or-later */
#define G_SETTINGS_ENABLE_BACKEND
#include <gio/gsettingsbackend.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <sndfile.h>
#include <AL/al.h>
#include <AL/alc.h>
#include <mach-o/dyld.h>
#include "macos-support.h"

int main (int argc, char **argv)
{
    g_assert_cmpint (argc, ==, 2);
    g_autofree gchar *resources = quadrapassel_macos_initialize_bundle ();
    g_assert_nonnull (resources);
    g_autofree gchar *contents = g_path_get_dirname (resources);
    g_autofree gchar *svg = g_build_filename (resources, "share/icons/hicolor/scalable/apps",
                                             APP_ID ".svg", NULL);
    g_autoptr(GError) error = NULL;
    g_autoptr(GdkPixbuf) icon = gdk_pixbuf_new_from_file (svg, &error);
    g_assert_no_error (error);
    g_assert_nonnull (icon);

    g_autofree gchar *prefs = g_build_filename (g_get_user_data_dir (), APP_ID, "preferences.ini", NULL);
    g_autoptr(GSettingsBackend) backend = g_keyfile_settings_backend_new (prefs, "/", NULL);
    g_autoptr(GSettings) settings = g_settings_new_with_backend (APP_ID, backend);
    if (g_str_equal (argv[1], "write")) {
        g_assert_true (g_settings_set_int (settings, "window-width", 777));
        g_settings_sync ();
    } else {
        g_assert_cmpint (g_settings_get_int (settings, "window-width"), ==, 777);
    }

    ALCdevice *device = alcOpenDevice (NULL);
    g_assert_nonnull (device);
    ALCcontext *context = alcCreateContext (device, NULL);
    g_assert_nonnull (context);
    g_assert_true (alcMakeContextCurrent (context));
    g_autofree gchar *sound_dir = g_build_filename (resources, "share/sounds/quadrapassel", NULL);
    g_autoptr(GDir) sounds = g_dir_open (sound_dir, 0, &error);
    g_assert_no_error (error);
    const gchar *name;
    int count = 0;
    while ((name = g_dir_read_name (sounds)) != NULL) {
        if (!g_str_has_suffix (name, ".ogg"))
            continue;
        g_autofree gchar *path = g_build_filename (sound_dir, name, NULL);
        SF_INFO info = {0};
        SNDFILE *sound = sf_open (path, SFM_READ, &info);
        g_assert_nonnull (sound);
        g_assert_true (info.channels == 1 || info.channels == 2);
        g_autofree short *samples = g_new (short, info.frames * info.channels);
        g_assert_cmpint (sf_readf_short (sound, samples, info.frames), ==, info.frames);
        sf_close (sound);
        ALuint buffer, source;
        alGenBuffers (1, &buffer);
        alBufferData (buffer, info.channels == 1 ? AL_FORMAT_MONO16 : AL_FORMAT_STEREO16,
                      samples, info.frames * info.channels * sizeof (short), info.samplerate);
        alGenSources (1, &source);
        alSourcei (source, AL_BUFFER, buffer);
        alSourcePlay (source);
        g_assert_cmpint (alGetError (), ==, AL_NO_ERROR);
        ALint state;
        alGetSourcei (source, AL_SOURCE_STATE, &state);
        g_assert_cmpint (state, ==, AL_PLAYING);
        alSourceStop (source);
        alDeleteSources (1, &source);
        alDeleteBuffers (1, &buffer);
        count++;
    }
    g_assert_cmpint (count, ==, 8);
    alcMakeContextCurrent (NULL);
    alcDestroyContext (context);
    alcCloseDevice (device);

    /* Include libraries loaded dynamically (SVG and sound), not just link-time dependencies. */
    g_autofree gchar *bundle_prefix = g_strconcat (contents, "/", NULL);
    for (uint32_t i = 0; i < _dyld_image_count (); i++) {
        const char *path = _dyld_get_image_name (i);
        if (!g_str_has_prefix (path, "/System/Library/") &&
            !g_str_has_prefix (path, "/usr/lib/") &&
            !g_str_has_prefix (path, "/System/Volumes/Preboot/Cryptexes/OS/") &&
            !g_str_has_prefix (path, bundle_prefix))
            g_error ("Loaded a library outside the app bundle: %s", path);
    }
    g_print ("PASS: relocated resources, SVG loader, persistent settings, eight sounds, bundled libraries (%s)\n", argv[1]);
    return 0;
}
