/* SPDX-License-Identifier: GPL-3.0-or-later */

// Drop an actual four-block piece into nearly complete rows. This exercises
// landing, bottom-row detection, level changes and scoring together.
private Game clear_rows (int count, ScoringRules rules, int difficulty = 0,
                         int previous_rows = 0, bool include_bottom = true)
{
    var game = new Game (20, 10, difficulty, 0, 5, false, rules);
    game.paused = true;
    game.n_lines_destroyed = previous_rows;
    int bottom = include_bottom ? 19 : 18;

    for (int y = bottom - count + 1; y <= bottom; y++)
        for (int x = 0; x < 10; x++)
            if (x != 4)
                game.blocks[x, y] = new Block () { x = x, y = y };

    if (!include_bottom)
        game.blocks[4, 19] = new Block () { x = 4, y = 19 };

    var piece = new Shape () { x = 4, y = 0 };
    for (int y = 0; y < 4; y++)
        piece.blocks.append (new Block () { x = 0, y = y });
    game.shape = piece;
    game.drop ();
    game.stop ();
    assert_cmpint (game.n_lines_destroyed, CompareOperator.EQ, previous_rows + count);
    return game;
}

private void test_modern_bonus ()
{
    int[] totals = { 140, 300, 600, 1600 };
    for (int rows = 1; rows <= 4; rows++)
        assert_cmpint (clear_rows (rows, ScoringRules.MODERN).score, CompareOperator.EQ, totals[rows - 1]);
}

private void test_classic_bonus ()
{
    // Version 40.2: a flat 10000 bonus whenever the bottom row is cleared.
    int[] totals = { 10040, 10100, 10300, 11200 };
    for (int rows = 1; rows <= 4; rows++)
    {
        assert_cmpint (clear_rows (rows, ScoringRules.CLASSIC).score, CompareOperator.EQ, totals[rows - 1]);
        assert_cmpint (clear_rows (rows, ScoringRules.CLASSIC, 4).score, CompareOperator.EQ, totals[rows - 1] * 5);
    }
}

private void test_no_bottom_bonus ()
{
    int[] totals = { 40, 100, 300, 1200 };
    for (int rows = 1; rows <= 4; rows++)
    {
        assert_cmpint (clear_rows (rows, ScoringRules.MODERN, 0, 0, false).score, CompareOperator.EQ, totals[rows - 1]);
        assert_cmpint (clear_rows (rows, ScoringRules.CLASSIC, 0, 0, false).score, CompareOperator.EQ, totals[rows - 1]);
    }
    assert_cmpint (clear_rows (0, ScoringRules.MODERN).score, CompareOperator.EQ, 0);
    assert_cmpint (clear_rows (0, ScoringRules.CLASSIC).score, CompareOperator.EQ, 0);
}

private void test_level_multiplier ()
{
    assert_cmpint (clear_rows (4, ScoringRules.MODERN, 4).score, CompareOperator.EQ, 8000);
    assert_cmpint (clear_rows (4, ScoringRules.CLASSIC, 4).score, CompareOperator.EQ, 56000);
    // Both scoring modes use the new level on a clear that passes ten rows.
    assert_cmpint (clear_rows (1, ScoringRules.MODERN, 0, 9).score, CompareOperator.EQ, 280);
    assert_cmpint (clear_rows (1, ScoringRules.CLASSIC, 0, 9).score, CompareOperator.EQ, 20080);
    // Relaxed difficulty stays at level one.
    assert_cmpint (clear_rows (1, ScoringRules.CLASSIC, -1, 19).score, CompareOperator.EQ, 10040);
}

private void test_default_and_copy ()
{
    var modern = new Game ();
    var classic = new Game (20, 10, 0, 0, 5, false, ScoringRules.CLASSIC);
    assert_true (modern.scoring_rules == ScoringRules.MODERN);
    assert_true (modern.copy ().scoring_rules == ScoringRules.MODERN);
    assert_true (classic.scoring_rules == ScoringRules.CLASSIC);
    assert_true (classic.copy ().scoring_rules == ScoringRules.CLASSIC);
    assert_true (modern.scoring_rules == ScoringRules.MODERN);
}

public int main (string[] args)
{
    Test.init (ref args);
    Test.add_func ("/scoring/modern", test_modern_bonus);
    Test.add_func ("/scoring/classic-40.2", test_classic_bonus);
    Test.add_func ("/scoring/no-bottom-bonus", test_no_bottom_bonus);
    Test.add_func ("/scoring/level-multiplier", test_level_multiplier);
    Test.add_func ("/scoring/default-and-copy", test_default_and_copy);
    return Test.run ();
}
