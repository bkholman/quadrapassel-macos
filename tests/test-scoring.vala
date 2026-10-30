/* SPDX-License-Identifier: GPL-3.0-or-later */

// Drop an actual four-block piece into nearly complete rows. This exercises
// landing, bottom-row detection, level changes and scoring together.
private Game clear_rows (int count, bool reduced, int difficulty = 0,
                         int previous_rows = 0, bool include_bottom = true)
{
    var game = new Game (20, 10, difficulty, 0, 5, false, reduced);
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

private void test_reduced_bonus ()
{
    int[] totals = { 140, 300, 600, 1600 };
    for (int rows = 1; rows <= 4; rows++)
        assert_cmpint (clear_rows (rows, true).score, CompareOperator.EQ, totals[rows - 1]);
}

private void test_pre_april_bonus ()
{
    // Immediately before April 2026: 2500 per cleared row, not 40.2's flat 10000.
    int[] totals = { 2540, 5100, 7800, 11200 };
    for (int rows = 1; rows <= 4; rows++)
        assert_cmpint (clear_rows (rows, false).score, CompareOperator.EQ, totals[rows - 1]);
}

private void test_no_bottom_bonus ()
{
    int[] totals = { 40, 100, 300, 1200 };
    for (int rows = 1; rows <= 4; rows++)
    {
        assert_cmpint (clear_rows (rows, true, 0, 0, false).score, CompareOperator.EQ, totals[rows - 1]);
        assert_cmpint (clear_rows (rows, false, 0, 0, false).score, CompareOperator.EQ, totals[rows - 1]);
    }
    assert_cmpint (clear_rows (0, true).score, CompareOperator.EQ, 0);
    assert_cmpint (clear_rows (0, false).score, CompareOperator.EQ, 0);
}

private void test_level_multiplier ()
{
    assert_cmpint (clear_rows (4, true, 4).score, CompareOperator.EQ, 8000);
    assert_cmpint (clear_rows (4, false, 4).score, CompareOperator.EQ, 56000);
    // Both scoring modes use the new level on a clear that passes ten rows.
    assert_cmpint (clear_rows (1, true, 0, 9).score, CompareOperator.EQ, 280);
    assert_cmpint (clear_rows (1, false, 0, 9).score, CompareOperator.EQ, 5080);
    // Relaxed difficulty stays at level one.
    assert_cmpint (clear_rows (1, false, -1, 19).score, CompareOperator.EQ, 2540);
}

private void test_default_and_copy ()
{
    var modern = new Game ();
    var legacy = new Game (20, 10, 0, 0, 5, false, false);
    assert_true (modern.reduce_base_row_bonus);
    assert_true (modern.copy ().reduce_base_row_bonus);
    assert_false (legacy.reduce_base_row_bonus);
    assert_false (legacy.copy ().reduce_base_row_bonus);
    assert_true (modern.reduce_base_row_bonus);
}

public int main (string[] args)
{
    Test.init (ref args);
    Test.add_func ("/scoring/reduced", test_reduced_bonus);
    Test.add_func ("/scoring/pre-april-2026", test_pre_april_bonus);
    Test.add_func ("/scoring/no-bottom-bonus", test_no_bottom_bonus);
    Test.add_func ("/scoring/level-multiplier", test_level_multiplier);
    Test.add_func ("/scoring/default-and-copy", test_default_and_copy);
    return Test.run ();
}
