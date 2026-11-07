"""Incremental backtracking solver used by direct and animated solving."""

from typing import Iterator
from model import Board, CellPosition, SolverStatus


class SudokuSolver:
    def __init__(self) -> None:
        self._status = SolverStatus.NOT_STARTED

        self._search_state: Iterator[bool] | None = None

        self._animate = False

    @property
    def status(self) -> SolverStatus:
        return self._status

    def start(self, board: Board, animate: bool) -> None:
        self._animate = animate

        if board.is_complete() and board.is_consistent():
            self._status = SolverStatus.SOLVED
            self._search_state = None

            return

        self._search_state = self._search(board)
        self._status = SolverStatus.RUNNING

        if not board.is_consistent():
            self._status = SolverStatus.UNSOLVABLE
            self._search_state = None

    def _search(self, board: Board) -> Iterator[bool]:
        empty = [CellPosition(r, c) for r in range(9) for c in range(9)
                 if board.get_cell(CellPosition(r, c)).value == 0]

        def visit(index: int) -> Iterator[bool]:
            if index == len(empty):
                return

            position = empty[index]

            for value in range(1, 10):
                if board.is_valid_move(position, value):
                    board.set_value(position, value)

                    yield True

                    yield from visit(index + 1)

                    if board.is_complete() and board.is_consistent():
                        return

                    board.clear_value(position)

                    yield True

            return

        yield from visit(0)

    def solve_step(self, board: Board) -> bool:
        if self._status is not SolverStatus.RUNNING or self._search_state is None:
            return False

        try:
            next(self._search_state)

            if board.is_complete() and board.is_consistent():
                self._status = SolverStatus.SOLVED
                self._search_state = None

            return True
        except StopIteration:
            self._status = SolverStatus.UNSOLVABLE
            self._search_state = None

            return False

    def reset(self) -> None:
        self._status = SolverStatus.NOT_STARTED
        self._search_state = None
        self._animate = False


def display_brd(brd: list[list[int]]) -> None:
    for row_num, row in enumerate(brd, start=1):
        print(" ".join(str(value) for value in row[:3]), "|",
              " ".join(str(value) for value in row[3:6]), "|",
              " ".join(str(value) for value in row[6:]))
        if row_num in (3, 6):
            print("---------------------")


def isFull(board: list[list[int]]) -> bool:
    return all(value != 0 for row in board for value in row)


def findEmpty(board: list[list[int]]) -> tuple[int, int] | None:
    for y, row in enumerate(board):
        for x, value in enumerate(row):
            if value == 0:
                return y, x

    return None


def possible(board: list[list[int]], x: int, y: int, num: int) -> bool:
    return (1 <= num <= 9 and
            all(board[y][col] != num for col in range(9) if col != x) and
            all(board[row][x] != num for row in range(9) if row != y) and
            all(board[row][col] != num
                for row in range(y // 3 * 3, y // 3 * 3 + 3)
                for col in range(x // 3 * 3, x // 3 * 3 + 3)
                if (row, col) != (y, x)))


def autosolve(board: list[list[int]]) -> bool:
    """Solve a mutable 9x9 board in place; return whether a solution exists."""
    empty = findEmpty(board)

    if empty is None:
        return all(possible(board, x, y, board[y][x])
                   for y in range(9) for x in range(9) if board[y][x])

    y, x = empty

    for num in range(1, 10):
        if possible(board, x, y, num):
            board[y][x] = num

            if autosolve(board):
                return True

            board[y][x] = 0

    return False


if __name__ == "__main__":
    from boards import giveBoard

    puzzle = giveBoard("easy")
    display_brd(puzzle)

    autosolve(puzzle)

    print("\nSolution:")
    display_brd(puzzle)
