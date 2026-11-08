"""Sudoku domain model and observer contracts."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "veryHard"


class GameMode(Enum):
    PUZZLE = auto()
    SOLVER = auto()


class GameStatus(Enum):
    READY = auto()
    PLAYING = auto()
    SOLVING = auto()
    SOLVED = auto()
    UNSOLVABLE = auto()


class SolverStatus(Enum):
    NOT_STARTED = auto()
    RUNNING = auto()
    SOLVED = auto()
    UNSOLVABLE = auto()


class ModelEventType(Enum):
    INITIAL_STATE = auto()
    BOARD_CHANGED = auto()
    CELL_SELECTED = auto()
    TIMER_CHANGED = auto()
    STATUS_CHANGED = auto()
    MESSAGE_CHANGED = auto()


@dataclass(frozen=True)
class CellPosition:
    row: int
    col: int

    def __post_init__(self) -> None:
        if not 0 <= self.row < 9 or not 0 <= self.col < 9:
            raise ValueError("Cell coordinates must be between 0 and 8")


class Cell:
    def __init__(self, position: CellPosition, value: int = 0,
                 is_fixed: bool = False) -> None:
        self.position = position
        self._value = value
        self._is_fixed = is_fixed

    @property
    def value(self) -> int:
        return self._value

    @property
    def is_fixed(self) -> bool:
        return self._is_fixed

    def set_value(self, value: int) -> None:
        if not 0 <= value <= 9:
            raise ValueError("Cell value must be between 0 and 9")

        if self._is_fixed:
            raise ValueError("A fixed cell cannot be changed")

        self._value = value

    def clear(self) -> None:
        self.set_value(0)


class Board:
    def __init__(self, values: list[list[int]] | tuple[tuple[int, ...], ...] | None = None,
                 fixed: bool = False,
                 fixed_cells: tuple[tuple[bool, ...], ...] | None = None) -> None:
        data = values if values is not None else [[0] * 9 for _ in range(9)]

        if len(data) != 9 or any(len(row) != 9 for row in data):
            raise ValueError("A Sudoku board must be 9 by 9")

        self._cells = [[Cell(CellPosition(r, c), int(data[r][c]),
                             (fixed and data[r][c] != 0) or
                             (fixed_cells is not None and fixed_cells[r][c]))
                        for c in range(9)]
                       for r in range(9)]

        if any(not 0 <= cell.value <= 9 for row in self._cells for cell in row):
            raise ValueError("Board values must be between 0 and 9")

    def get_cell(self, position: CellPosition) -> Cell:
        return self._cells[position.row][position.col]

    def set_value(self, position: CellPosition, value: int) -> bool:
        cell = self.get_cell(position)

        if cell.is_fixed or not 0 <= value <= 9:
            return False

        cell.set_value(value)

        return True

    def clear_value(self, position: CellPosition) -> bool:
        return self.set_value(position, 0)

    def is_fixed(self, position: CellPosition) -> bool:
        return self.get_cell(position).is_fixed

    def is_valid_move(self, position: CellPosition, value: int) -> bool:
        if not 1 <= value <= 9:
            return False

        row, col = position.row, position.col

        if any(c != col and self._cells[row][c].value == value for c in range(9)):
            return False

        if any(r != row and self._cells[r][col].value == value for r in range(9)):
            return False

        box_row, box_col = row // 3 * 3, col // 3 * 3

        return not any((r, c) != (row, col) and self._cells[r][c].value == value
                       for r in range(box_row, box_row + 3)
                       for c in range(box_col, box_col + 3))

    def is_complete(self) -> bool:
        return all(cell.value != 0 for row in self._cells for cell in row)

    def is_consistent(self) -> bool:
        return all(self.is_valid_move(CellPosition(r, c), self._cells[r][c].value)
                   for r in range(9) for c in range(9) if self._cells[r][c].value)

    def to_tuple(self) -> tuple[tuple[int, ...], ...]:
        return tuple(tuple(cell.value for cell in row) for row in self._cells)

    def fixed_to_tuple(self) -> tuple[tuple[bool, ...], ...]:
        return tuple(tuple(cell.is_fixed for cell in row) for row in self._cells)

    def copy(self) -> Board:
        return Board(self.to_tuple(), fixed_cells=self.fixed_to_tuple())

    def invalid_positions(self) -> tuple[CellPosition, ...]:
        return tuple(CellPosition(r, c) for r in range(9) for c in range(9)
                     if self._cells[r][c].value and
                     not self.is_valid_move(CellPosition(r, c), self._cells[r][c].value))


class IObserver(Protocol):
    def update(self, event: ModelEvent) -> None: ...


class ISubject(Protocol):
    def attach(self, observer: IObserver) -> None: ...
    def detach(self, observer: IObserver) -> None: ...

    def notify(self, event: ModelEvent) -> None: ...


@dataclass(frozen=True)
class GameSnapshot:
    version: int

    board_data: tuple[tuple[int, ...], ...]
    fixed_cells: tuple[tuple[bool, ...], ...]

    invalid_cells: tuple[CellPosition, ...]

    selected_cell: CellPosition | None

    difficulty: Difficulty
    mode: GameMode
    status: GameStatus
    solver_status: SolverStatus

    elapsed_seconds: float
    message: str


@dataclass(frozen=True)
class ModelEvent:
    event_type: ModelEventType
    snapshot: GameSnapshot

    changed_cells: tuple[CellPosition, ...] = ()


class BoardRepository:
    def get_board(self, difficulty: Difficulty) -> Board:
        from .boards import giveBoard

        return Board(giveBoard(difficulty.value), fixed=True)

    def get_random_board(self, difficulty: Difficulty) -> Board:
        return self.get_board(difficulty)


class SudokuGame(ISubject):
    def __init__(self, repository: BoardRepository | None = None) -> None:
        from .solver import SudokuSolver

        self._observers: list[IObserver] = []

        self._difficulty = Difficulty.EASY
        self._mode = GameMode.PUZZLE
        self._status = GameStatus.READY

        self._selected_cell: CellPosition | None = None

        self._elapsed_seconds = 0.0
        self._version = 0
        self._message = ""

        self._board = Board()
        self._solver = SudokuSolver()
        self._repository = repository or BoardRepository()

    def get_current_snapshot(self) -> GameSnapshot:
        return GameSnapshot(self._version, self._board.to_tuple(), self._board.fixed_to_tuple(),
                            self._board.invalid_positions(), self._selected_cell,
                            self._difficulty, self._mode, self._status,
                            self._solver.status, self._elapsed_seconds, self._message)

    def _publish(self, event_type: ModelEventType,
                 changed: tuple[CellPosition, ...] = ()) -> None:
        self._version += 1

        self.notify(ModelEvent(event_type, self.get_current_snapshot(), changed))

    def start_game(self, difficulty: Difficulty) -> None:
        self._difficulty, self._mode = difficulty, GameMode.PUZZLE

        self._board = self._repository.get_board(difficulty)

        self._solver.reset()

        self._status, self._selected_cell = GameStatus.PLAYING, None
        self._elapsed_seconds, self._message = 0.0, ""

        self._publish(ModelEventType.STATUS_CHANGED)

    def start_solver_mode(self) -> None:
        self._mode, self._status = GameMode.SOLVER, GameStatus.PLAYING
        self._difficulty, self._board = Difficulty.EASY, Board()

        self._solver.reset()

        self._selected_cell, self._elapsed_seconds, self._message = None, 0.0, ""

        self._publish(ModelEventType.STATUS_CHANGED)

    def select_cell(self, position: CellPosition | None) -> None:
        self._selected_cell = position

        changed = (position,) if position is not None else ()

        self._publish(ModelEventType.CELL_SELECTED, changed)

    def set_cell_value(self, value: int) -> bool:
        if (self._status is GameStatus.SOLVING or self._selected_cell is None or
                not 0 <= value <= 9):
            return False

        position = self._selected_cell

        changed = self._board.set_value(position, value)
        if changed:
            self._message = ""
            self._publish(ModelEventType.BOARD_CHANGED, (position,))
            self.check_completion()

        return changed

    def clear_selected_cell(self) -> bool:
        return self.set_cell_value(0)

    def start_solving(self, animate: bool) -> None:
        self._solver.start(self._board, animate)

        self._status = GameStatus.SOLVING

        if not animate:
            while self._solver.status is SolverStatus.RUNNING:
                self._solver.solve_step(self._board)

        self._sync_solver_status()

        self._publish(ModelEventType.STATUS_CHANGED)

    def advance_solver_step(self) -> bool:
        if self._solver.status is not SolverStatus.RUNNING:
            return False

        changed = self._solver.solve_step(self._board)

        self._sync_solver_status()

        self._publish(ModelEventType.BOARD_CHANGED if changed else ModelEventType.STATUS_CHANGED)
        return self._solver.status is SolverStatus.RUNNING

    def _sync_solver_status(self) -> None:
        if self._solver.status is SolverStatus.SOLVED:
            self._status, self._message = GameStatus.SOLVED, "Puzzle solved"
        elif self._solver.status is SolverStatus.UNSOLVABLE:
            self._status, self._message = GameStatus.UNSOLVABLE, "This board has no solution"

    def update_elapsed_time(self, delta_seconds: float) -> None:
        if delta_seconds > 0 and self._status is GameStatus.PLAYING and self._mode is GameMode.PUZZLE:
            self._elapsed_seconds += delta_seconds

            self._publish(ModelEventType.TIMER_CHANGED)

    def check_completion(self) -> bool:
        complete = self._board.is_complete() and self._board.is_consistent()
        if complete and self._status is GameStatus.PLAYING:
            self._status, self._message = GameStatus.SOLVED, "Puzzle solved"

            self._publish(ModelEventType.STATUS_CHANGED)

        return complete

    def attach(self, observer: IObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

            observer.update(ModelEvent(ModelEventType.INITIAL_STATE, self.get_current_snapshot()))

    def detach(self, observer: IObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: ModelEvent) -> None:
        for observer in tuple(self._observers):
            observer.update(event)
