import pytest

from minerva_travel.maze import MazeGenerationError, build_maze, maze_size_for


def _cells(maze):
    return {(column, row) for column in range(maze.columns) for row in range(maze.rows)}


def _reachable(maze):
    seen = {maze.start}
    stack = [maze.start]
    while stack:
        column, row = stack.pop()
        moves = []
        if not maze.has_wall_right(column, row):
            moves.append((column + 1, row))
        if column > 0 and not maze.has_wall_right(column - 1, row):
            moves.append((column - 1, row))
        if not maze.has_wall_down(column, row):
            moves.append((column, row + 1))
        if row > 0 and not maze.has_wall_down(column, row - 1):
            moves.append((column, row - 1))
        for move in moves:
            if move not in seen:
                seen.add(move)
                stack.append(move)
    return seen


def test_every_cell_is_reachable_so_no_corner_is_a_dead_room():
    maze = build_maze(columns=10, rows=14, seed="eiffel")

    assert _reachable(maze) == _cells(maze)


def test_the_maze_is_perfect_so_there_is_exactly_one_route():
    maze = build_maze(columns=10, rows=14, seed="eiffel")

    # Num labirinto perfeito o número de passagens é sempre células - 1;
    # qualquer passagem a mais criaria um atalho e um segundo caminho.
    passages = len(maze.open_right) + len(maze.open_down)
    assert passages == maze.columns * maze.rows - 1


def test_the_solution_walks_from_the_child_to_the_landmark_step_by_step():
    maze = build_maze(columns=8, rows=10, seed="louvre")

    assert maze.solution[0] == maze.start == (0, 0)
    assert maze.solution[-1] == maze.goal == (7, 9)
    for (column, row), (next_column, next_row) in zip(
        maze.solution, maze.solution[1:], strict=False
    ):
        assert abs(column - next_column) + abs(row - next_row) == 1


def test_the_same_seed_always_prints_the_same_maze():
    first = build_maze(columns=8, rows=10, seed="louvre")
    again = build_maze(columns=8, rows=10, seed="louvre")
    other = build_maze(columns=8, rows=10, seed="eiffel")

    assert first.open_right == again.open_right
    assert first.open_right != other.open_right


def test_the_grid_grows_with_the_age_band():
    preschool = maze_size_for("preschool")
    older = maze_size_for("older_child")

    assert preschool[0] * preschool[1] < older[0] * older[1]
    assert maze_size_for("desconhecido") == maze_size_for("early_reader")


def test_impossible_dimensions_are_refused():
    for columns, rows in ((2, 10), (10, 2), (40, 10), (10, 40)):
        with pytest.raises(MazeGenerationError):
            build_maze(columns=columns, rows=rows, seed="qualquer")
