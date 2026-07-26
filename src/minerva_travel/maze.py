"""Labirinto determinístico da criança até o ponto turístico.

Gera um labirinto perfeito (caminho único entre dois pontos, sem ciclos) por
backtracking recursivo. Perfeito importa aqui: com atalhos, uma criança que
"errou" ainda chegaria ao fim e a atividade perderia a graça.

A grade cresce com a idade — 4-6 anos resolvem uma grade curta sem
frustração; 7-9 precisam de becos sem saída para valer a pena.
"""

import random
from dataclasses import dataclass

# (colunas, linhas) por faixa etária do guia.
MAZE_SIZES: dict[str, tuple[int, int]] = {
    "preschool": (7, 10),
    "early_reader": (10, 14),
    "older_child": (13, 18),
    "family": (10, 14),
}
DEFAULT_MAZE_SIZE = MAZE_SIZES["early_reader"]


class MazeGenerationError(ValueError):
    """The requested maze dimensions cannot produce a solvable path."""


@dataclass(frozen=True)
class Maze:
    columns: int
    rows: int
    # Paredes abertas por célula, indexadas por (coluna, linha).
    open_right: frozenset[tuple[int, int]]
    open_down: frozenset[tuple[int, int]]
    start: tuple[int, int]
    goal: tuple[int, int]
    solution: tuple[tuple[int, int], ...]

    def has_wall_right(self, column: int, row: int) -> bool:
        return (column, row) not in self.open_right

    def has_wall_down(self, column: int, row: int) -> bool:
        return (column, row) not in self.open_down


def maze_size_for(age_complexity: str) -> tuple[int, int]:
    return MAZE_SIZES.get(age_complexity, DEFAULT_MAZE_SIZE)


def build_maze(*, columns: int, rows: int, seed: str) -> Maze:
    """Carve a perfect maze and return it with the single start-to-goal path."""

    if not 4 <= columns <= 20 or not 4 <= rows <= 26:
        raise MazeGenerationError("As dimensões do labirinto são inválidas.")

    rng = random.Random(f"maze:{seed}")
    visited = {(0, 0)}
    open_right: set[tuple[int, int]] = set()
    open_down: set[tuple[int, int]] = set()
    stack = [(0, 0)]
    while stack:
        column, row = stack[-1]
        neighbours = [
            (column + dc, row + dr)
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= column + dc < columns and 0 <= row + dr < rows
            and (column + dc, row + dr) not in visited
        ]
        if not neighbours:
            stack.pop()
            continue
        next_column, next_row = rng.choice(neighbours)
        if next_column > column:
            open_right.add((column, row))
        elif next_column < column:
            open_right.add((next_column, next_row))
        elif next_row > row:
            open_down.add((column, row))
        else:
            open_down.add((next_column, next_row))
        visited.add((next_column, next_row))
        stack.append((next_column, next_row))

    start, goal = (0, 0), (columns - 1, rows - 1)
    maze = Maze(
        columns=columns,
        rows=rows,
        open_right=frozenset(open_right),
        open_down=frozenset(open_down),
        start=start,
        goal=goal,
        solution=(),
    )
    solution = _solve(maze)
    if not solution:
        raise MazeGenerationError("O labirinto gerado não tem caminho até o destino.")
    return Maze(
        columns=columns,
        rows=rows,
        open_right=maze.open_right,
        open_down=maze.open_down,
        start=start,
        goal=goal,
        solution=tuple(solution),
    )


def _solve(maze: Maze) -> list[tuple[int, int]]:
    stack = [maze.start]
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {maze.start: None}
    while stack:
        current = stack.pop()
        if current == maze.goal:
            break
        for neighbour in _open_neighbours(maze, current):
            if neighbour not in came_from:
                came_from[neighbour] = current
                stack.append(neighbour)
    if maze.goal not in came_from:
        return []
    path: list[tuple[int, int]] = []
    node: tuple[int, int] | None = maze.goal
    while node is not None:
        path.append(node)
        node = came_from[node]
    return list(reversed(path))


def _open_neighbours(maze: Maze, cell: tuple[int, int]) -> list[tuple[int, int]]:
    column, row = cell
    neighbours = []
    if not maze.has_wall_right(column, row):
        neighbours.append((column + 1, row))
    if column > 0 and not maze.has_wall_right(column - 1, row):
        neighbours.append((column - 1, row))
    if not maze.has_wall_down(column, row):
        neighbours.append((column, row + 1))
    if row > 0 and not maze.has_wall_down(column, row - 1):
        neighbours.append((column, row - 1))
    return neighbours
