/* SPDX-License-Identifier: GPL-3.0-or-later */

// Runs inside a copied .app with only bundled libraries and isolated settings.
public int main (string[] args)
{
    assert_cmpint (args.length, CompareOperator.EQ, 7);
    RuntimePaths.initialize ();
    string locale_dir = RuntimePaths.locale ();
    // Simulate an OS language in this process, without changing macOS settings.
    MacOS.set_process_language (args[2]);
    Localization.initialize (args[1], locale_dir);
    assert_cmpstr (Environment.get_variable ("LANGUAGE").split (":")[0], CompareOperator.EQ, args[3]);
    Gtk.disable_setlocale ();
    Adw.init ();
    Localization.bind_domains (locale_dir);
    Gtk.Widget.set_default_direction (Localization.is_right_to_left () ? Gtk.TextDirection.RTL : Gtk.TextDirection.LTR);

    foreach (string domain in new string[] { "quadrapassel", "quadrapassel_libgnome-games-support",
                "gtk40", "gtk40-properties", "libadwaita", "glib20", "gdk-pixbuf" })
        assert_cmpstr (Intl.bindtextdomain (domain, null), CompareOperator.EQ, locale_dir);
    assert_cmpstr (GLib.dgettext ("quadrapassel", "_Preferences"), CompareOperator.EQ, args[4]);
    assert_cmpstr (GLib.dgettext ("gtk40", "_Cancel"), CompareOperator.EQ, args[5]);
    assert_cmpstr (GLib.dgettext ("libadwaita", "Preferences"), CompareOperator.EQ, args[6]);
    bool rtl = args[3] == "ar" || args[3] == "he" || args[3] == "fa" || args[3] == "ug";
    assert_true (Gtk.Widget.get_default_direction () == (rtl ? Gtk.TextDirection.RTL : Gtk.TextDirection.LTR));
    print ("PASS: %s / OS %s → %s; app, GTK, libadwaita, text direction, bundled domains\n", args[1], args[2], args[3]);
    return 0;
}
