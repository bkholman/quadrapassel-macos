/* SPDX-License-Identifier: GPL-3.0-or-later */

private void test_language_tags ()
{
    var languages = LanguageCatalog.all ();
    assert_cmpstr (Localization.match_language ("fr-CA", languages), CompareOperator.EQ, "fr");
    assert_cmpstr (Localization.match_language ("de_DE.UTF-8", languages), CompareOperator.EQ, "de");
    assert_cmpstr (Localization.match_language ("pt-BR", languages), CompareOperator.EQ, "pt_BR");
    assert_cmpstr (Localization.match_language ("pt-Latn-BR", languages), CompareOperator.EQ, "pt_BR");
    assert_cmpstr (Localization.match_language ("en-GB", languages), CompareOperator.EQ, "en_GB");
    assert_cmpstr (Localization.match_language ("zh-Hans-US", languages), CompareOperator.EQ, "zh_CN");
    assert_cmpstr (Localization.match_language ("zh-Hant-US", languages), CompareOperator.EQ, "zh_TW");
    assert_cmpstr (Localization.match_language ("zh-Hant-HK", languages), CompareOperator.EQ, "zh_HK");
    assert_cmpstr (Localization.match_language ("zh-SG", languages), CompareOperator.EQ, "zh_CN");
    assert_cmpstr (Localization.match_language ("sr-Latn-RS", languages), CompareOperator.EQ, "sr@latin");
    assert_cmpstr (Localization.match_language ("sr@latin", languages), CompareOperator.EQ, "sr@latin");
    assert_cmpstr (Localization.match_language ("sr_RS.UTF-8@latin", languages), CompareOperator.EQ, "sr@latin");
    assert_cmpstr (Localization.match_language ("ca-ES-valencia", languages), CompareOperator.EQ, "ca@valencia");
    assert_cmpstr (Localization.match_language ("no-NO", languages), CompareOperator.EQ, "nb");
    assert_null (Localization.match_language ("xx-YY", languages));
}

private void test_system_fallbacks ()
{
    var languages = LanguageCatalog.all ();
    assert_cmpstr (Localization.language_priority ("system", {"fr-CA", "de-DE"}, languages), CompareOperator.EQ, "fr:de:en");
    assert_cmpstr (Localization.language_priority ("system", {"xx", "ja-JP"}, languages), CompareOperator.EQ, "ja:en");
    assert_cmpstr (Localization.language_priority ("system", {"en-US", "fr-FR"}, languages), CompareOperator.EQ, "en");
    assert_cmpstr (Localization.language_priority ("system", {"en-GB", "fr-FR"}, languages), CompareOperator.EQ, "en_GB:en");
    assert_cmpstr (Localization.language_priority ("system", {"fr-CA", "fr-FR"}, languages), CompareOperator.EQ, "fr:en");
    assert_cmpstr (Localization.language_priority ("system", {}, languages), CompareOperator.EQ, "en");
    assert_cmpstr (Localization.language_priority ("system", {"C"}, languages), CompareOperator.EQ, "en");
}

private void test_override ()
{
    var languages = LanguageCatalog.all ();
    assert_cmpstr (Localization.language_priority ("de", {"fr"}, languages), CompareOperator.EQ, "de:en");
    assert_cmpstr (Localization.language_priority ("en", {"fr"}, languages), CompareOperator.EQ, "en");
    assert_cmpstr (Localization.language_priority ("zh_TW", {"en"}, languages), CompareOperator.EQ, "zh_TW:en");
    assert_cmpstr (Localization.language_priority ("unavailable", {"fr"}, languages), CompareOperator.EQ, "fr:en");
    // An uninstalled catalog cannot become a manual choice or a system match.
    LanguageInfo[] english_only = { new LanguageInfo ("en", "English", "en") };
    assert_cmpstr (Localization.language_priority ("de", {"fr"}, english_only), CompareOperator.EQ, "en");
}

private void test_catalog_filter ()
{
    try
    {
        string directory = DirUtils.make_tmp ("quadrapassel-languages-XXXXXX");
        var empty = Localization.available (directory);
        assert_cmpint (empty.length, CompareOperator.EQ, 1);
        assert_cmpstr (empty[0].code, CompareOperator.EQ, "en");
        string messages = Path.build_filename (directory, "fr", "LC_MESSAGES");
        DirUtils.create_with_parents (messages, 0700);
        string catalog = Path.build_filename (messages, "quadrapassel.mo");
        FileUtils.set_contents (catalog, "test fixture");
        assert_cmpint (Localization.available (directory).length, CompareOperator.EQ, 2);
        FileUtils.remove (catalog);
        DirUtils.remove (messages);
        DirUtils.remove (Path.build_filename (directory, "fr"));
        DirUtils.remove (directory);
    }
    catch (Error e) { error ("Cannot create catalog fixture: %s", e.message); }
}

public int main (string[] args)
{
    Test.init (ref args);
    Test.add_func ("/localization/language-tags", test_language_tags);
    Test.add_func ("/localization/system-fallbacks", test_system_fallbacks);
    Test.add_func ("/localization/manual-override", test_override);
    Test.add_func ("/localization/installed-catalogs", test_catalog_filter);
    return Test.run ();
}
