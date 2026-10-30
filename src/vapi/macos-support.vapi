/* SPDX-License-Identifier: GPL-3.0-or-later */
[CCode (cheader_filename = "macos-support.h")]
namespace MacOS {
    [CCode (cname = "quadrapassel_macos_initialize_bundle")]
    public string? initialize_bundle ();
}
