/* SPDX-License-Identifier: GPL-3.0-or-later */

public class LanguageInfo : Object
{
    public string code;
    public string name;
    public string tag;

    public LanguageInfo (string code, string name, string tag)
    {
        this.code = code;
        this.name = name;
        this.tag = tag;
    }
}

namespace Localization
{
    private string? active_language = null;

    public bool is_right_to_left ()
    {
        // These are the RTL languages in the application's supported catalogs.
        return active_language == "ar" || active_language == "fa" ||
               active_language == "he" || active_language == "ug";
    }

    public LanguageInfo[] available (string locale_dir)
    {
        LanguageInfo[] result = {};
        foreach (var language in LanguageCatalog.all ())
            if (language.code == "en" || FileUtils.test (Path.build_filename (locale_dir,
                    language.code, "LC_MESSAGES", GETTEXT_PACKAGE + ".mo"), FileTest.IS_REGULAR))
                result += language;
        return result;
    }

    // Accept POSIX locale names and Apple's BCP 47 language/script/region tags.
    public string? match_language (string requested, LanguageInfo[] languages)
    {
        string[] locale_parts = requested.split ("@", 2);
        string modifier = locale_parts.length > 1 ? locale_parts[1].ascii_down () : "";
        string tag = locale_parts[0].split (".")[0].replace ("_", "-").ascii_down ();
        if (modifier != "")
            tag += "@" + modifier;
        if (tag == "c" || tag == "posix")
            return "en";
        foreach (var language in languages)
            if (tag == language.code.replace ("_", "-").ascii_down () || tag == language.tag.ascii_down ())
                return language.code;

        string[] parts = tag.split ("@")[0].split ("-");
        string base_language = parts[0];
        string candidate = base_language;
        if (base_language == "zh")
        {
            if ("hans" in parts)
                candidate = "zh_CN";
            else if ("hk" in parts || "mo" in parts)
                candidate = "zh_HK";
            else if ("hant" in parts || "tw" in parts)
                candidate = "zh_TW";
            else
                candidate = "zh_CN";
        }
        else if (base_language == "sr" && ("latn" in parts || modifier == "latin"))
            candidate = "sr@latin";
        else if (base_language == "en" && ("shaw" in parts || modifier == "shaw"))
            candidate = "en@shaw";
        else if (base_language == "ca" && ("valencia" in parts || modifier == "valencia"))
            candidate = "ca@valencia";
        else if (base_language == "no")
            candidate = "nb";
        else if (base_language == "iw")
            candidate = "he";
        else if (base_language == "in")
            candidate = "id";
        else
        {
            // Preserve regional catalogs such as pt_BR and en_GB with a script tag.
            foreach (var language in languages)
                if (language.code.has_prefix (base_language + "_") &&
                    language.code.split ("_")[1].ascii_down () in parts)
                    return language.code;
        }
        foreach (var language in languages)
            if (language.code == candidate)
                return candidate;
        return null;
    }

    public string language_priority (string selection, string[] system_languages, LanguageInfo[] languages)
    {
        foreach (var language in languages)
            if (selection == language.code)
                return selection == "en" ? "en" : selection + ":en";

        string[] result = {};
        foreach (string requested in system_languages)
        {
            string? code = match_language (requested, languages);
            if (code == null || code in result)
                continue;
            result += code;
            // English is a real preference, not a missing catalog to skip.
            if (code == "en" || code.has_prefix ("en_") || code.has_prefix ("en@"))
                break;
        }
        if (!("en" in result))
            result += "en";
        return string.joinv (":", result);
    }

    public void initialize (string selection, string locale_dir)
    {
        var languages = available (locale_dir);
#if MACOS
        string[] system_languages = MacOS.preferred_languages ();
#else
        string[] system_languages = Intl.get_language_names ();
#endif
        string priority = language_priority (selection, system_languages, languages);
        active_language = priority.split (":")[0];
        Environment.set_variable ("LANGUAGE", priority, true);
        foreach (var language in languages)
            if (language.code == active_language)
                Environment.set_variable ("PANGO_LANGUAGE", language.tag, true);
        Intl.setlocale (LocaleCategory.ALL, "");
        // libintl also consults the environment on macOS. A terminal's LC_ALL=C
        // must not disable an explicit app language or the macOS System choice.
        // Preserve its formatting categories before separating LC_MESSAGES.
        string? all_locale = Environment.get_variable ("LC_ALL");
        if (all_locale != null && all_locale != "")
        {
            foreach (string category in new string[] { "LC_CTYPE", "LC_NUMERIC", "LC_TIME", "LC_COLLATE", "LC_MONETARY" })
                Environment.set_variable (category, all_locale, true);
            Environment.unset_variable ("LC_ALL");
        }
        // Finder can start with a C locale. gettext needs an enabled message
        // locale even though LANGUAGE selects the actual translation catalog.
        unowned string? messages = Intl.setlocale (LocaleCategory.MESSAGES, null);
        if (messages == null || messages == "C" || messages == "POSIX" || messages.has_prefix ("C."))
        {
#if MACOS
            Intl.setlocale (LocaleCategory.MESSAGES, "en_US.UTF-8");
#else
            if (Intl.setlocale (LocaleCategory.MESSAGES, "C.UTF-8") == null)
                Intl.setlocale (LocaleCategory.MESSAGES, "en_US.UTF-8");
#endif
        }
        Environment.set_variable ("LC_MESSAGES", Intl.setlocale (LocaleCategory.MESSAGES, null) ?? "en_US.UTF-8", true);
#if MACOS
        // Keep Cocoa's standard application menu in the selected language too.
        foreach (var language in languages)
            if (language.code == active_language)
                MacOS.set_process_language (language.tag);
#endif
        bind_domains (locale_dir);
        Intl.textdomain (GETTEXT_PACKAGE);
    }

    public void bind_domains (string locale_dir)
    {
        Intl.bindtextdomain (GETTEXT_PACKAGE, locale_dir);
        Intl.bind_textdomain_codeset (GETTEXT_PACKAGE, "UTF-8");
        Intl.bindtextdomain (GETTEXT_PACKAGE + "_libgnome-games-support", locale_dir);
        Intl.bind_textdomain_codeset (GETTEXT_PACKAGE + "_libgnome-games-support", "UTF-8");
#if MACOS
        // GTK and libadwaita reset their own domains during initialization, so
        // call this again afterwards, before constructing any application UI.
        foreach (string domain in new string[] { "gtk40", "gtk40-properties", "libadwaita", "glib20", "gdk-pixbuf" })
        {
            Intl.bindtextdomain (domain, locale_dir);
            Intl.bind_textdomain_codeset (domain, "UTF-8");
        }
#endif
    }
}
