/* SPDX-License-Identifier: GPL-3.0-or-later */
[CCode (cheader_filename = "macos-support.h")]
namespace MacOS {
    [CCode (cname = "quadrapassel_macos_initialize_bundle")]
    public string? initialize_bundle ();
    [CCode (cname = "quadrapassel_macos_preferred_languages", array_length = false, array_null_terminated = true)]
    public string[] preferred_languages ();
    [CCode (cname = "quadrapassel_macos_set_process_language")]
    public void set_process_language (string language);
}
