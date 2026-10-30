/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <glib.h>

gchar *quadrapassel_macos_initialize_bundle (void);
gchar **quadrapassel_macos_preferred_languages (void);
void quadrapassel_macos_set_process_language (const gchar *language);
