/* SPDX-License-Identifier: GPL-3.0-or-later */

private Games.Scores.Context create_context ()
{
    return new Games.Scores.Context ("quadrapassel-test", "Difficulty",
        (key) => new Games.Scores.Category (key, key),
        Games.Scores.Style.POINTS_GREATER_IS_BETTER);
}

private async void check_reset () throws Error
{
    var context = create_context ();
    assert_false (context.has_scores ());
    yield context.add_score (140, new Games.Scores.Category ("0", "0"), null, null);
    yield context.add_score (56000, new Games.Scores.Category ("4-difficult", "4"), null, null);
    yield context.add_score (10040, new Games.Scores.Category ("old-scores", "Old Scores"), null, null);
    assert_true (create_context ().has_scores ());

    yield context.delete_scores ();
    assert_false (context.has_scores ());
    assert_false (create_context ().has_scores ());
    assert_cmpuint (context.get_categories ().length, CompareOperator.EQ, 0);

    // A new game can save normally after resetting every category.
    yield context.add_score (2540, new Games.Scores.Category ("0", "0"), null, null);
    var reloaded = create_context ();
    assert_cmpuint (reloaded.get_categories ().length, CompareOperator.EQ, 1);
    var scores = reloaded.get_high_scores (new Games.Scores.Category ("0", "0"));
    assert_cmpuint (scores.length, CompareOperator.EQ, 1);
    assert_cmpint ((int) scores[0].score, CompareOperator.EQ, 2540);
    yield reloaded.delete_scores ();
}

private void test_reset ()
{
    var loop = new MainLoop ();
    check_reset.begin ((obj, result) => {
        try { check_reset.end (result); }
        catch (Error e) { error ("Scoreboard test failed: %s", e.message); }
        loop.quit ();
    });
    loop.run ();
}

public int main (string[] args)
{
    Test.init (ref args);
    string temporary_data;
    try { temporary_data = DirUtils.make_tmp ("quadrapassel-scores-XXXXXX"); }
    catch (FileError e) { error ("Cannot create test directory: %s", e.message); }
    // Set before the first GLib data-directory lookup. Never use real scores.
    Environment.set_variable ("XDG_DATA_HOME", temporary_data, true);
    Test.add_func ("/scoreboard/reset-all-categories", test_reset);
    int result = Test.run ();
    DirUtils.remove (Path.build_filename (temporary_data, "quadrapassel-test"));
    DirUtils.remove (temporary_data);
    return result;
}
