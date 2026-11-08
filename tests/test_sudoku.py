"""Unit tests for the Sudoku model, solver, repository, and controller."""

import unittest

from src.audio import SoundEffect
from src.controller import GameController, InputEvent, InputEventType
from src.model import (Board, CellPosition, Difficulty, GameMode, GameStatus,
                       BoardRepository, ModelEvent, ModelEventType, SolverStatus,
                       SudokuGame)
from src.solver import SudokuSolver
from src.view import (DialogType, ScreenType, SudokuView, UIAction, UIActionType)


PUZZLE = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]


class RecordingObserver:
    def __init__(self) -> None:
        self.events: list[ModelEvent] = []

    def update(self, event: ModelEvent) -> None:
        self.events.append(event)


class FakeRenderer:
    def __init__(self) -> None:
        self.frames = 0
        self.closed = False

    def render_screen(self, screen: object, snapshot: object) -> None:
        self.frames += 1

    def render_dialog(self, dialog: object) -> None:
        self.frames += 1

    def present(self) -> None:
        self.frames += 1

    def close(self) -> None:
        self.closed = True


class FakeEvents:
    def poll_events(self) -> list[InputEvent]:
        return []


class FakeAudio:
    def __init__(self) -> None:
        self.played: list[SoundEffect] = []
        self.paused = False
        self.resumed = False

    def play_effect(self, effect: SoundEffect) -> None:
        self.played.append(effect)

    def play_background_music(self) -> None:
        pass

    def pause_background_music(self) -> None:
        self.paused = True

    def resume_background_music(self) -> None:
        self.resumed = True


class BoardTests(unittest.TestCase):
    def test_repository_returns_independent_puzzles_for_each_difficulty(self) -> None:
        repository = BoardRepository()
        for difficulty in Difficulty:
            first = repository.get_board(difficulty)
            second = repository.get_random_board(difficulty)
            self.assertEqual(len(first.to_tuple()), 9)
            self.assertTrue(first.is_consistent())
            empty_row, empty_col = next(
                (row, col) for row in range(9) for col in range(9)
                if first.to_tuple()[row][col] == 0
            )
            position = CellPosition(empty_row, empty_col)
            second_value = second.get_cell(position).value
            self.assertTrue(first.set_value(position, 1))
            self.assertEqual(second.get_cell(position).value, second_value)
            self.assertNotEqual(id(first), id(second))

    def test_repository_puzzles_can_be_solved_at_every_difficulty(self) -> None:
        for difficulty in Difficulty:
            board = BoardRepository().get_board(difficulty)
            solver = SudokuSolver()
            solver.start(board, animate=False)
            while solver.status is SolverStatus.RUNNING:
                solver.solve_step(board)
            self.assertEqual(solver.status, SolverStatus.SOLVED, difficulty.value)

    def test_board_marks_givens_fixed_and_rejects_edits(self) -> None:
        board = Board(PUZZLE, fixed=True)
        self.assertTrue(board.is_fixed(CellPosition(0, 0)))
        self.assertFalse(board.set_value(CellPosition(0, 0), 4))
        self.assertEqual(board.get_cell(CellPosition(0, 0)).value, 5)

    def test_board_updates_cells_through_their_mutator(self) -> None:
        board = Board()
        cell = board.get_cell(CellPosition(0, 0))
        self.assertTrue(board.set_value(CellPosition(0, 0), 4))
        self.assertEqual(cell.value, 4)
        with self.assertRaises(AttributeError):
            cell.value = 8  # type: ignore[misc]

    def test_board_allows_conflicts_for_red_ui_feedback(self) -> None:
        board = Board()
        self.assertTrue(board.set_value(CellPosition(0, 0), 1))
        self.assertTrue(board.set_value(CellPosition(0, 1), 1))
        self.assertFalse(board.is_consistent())
        self.assertEqual(len(board.invalid_positions()), 2)

    def test_board_detects_valid_move_and_completion(self) -> None:
        board = Board(PUZZLE)
        self.assertTrue(board.is_valid_move(CellPosition(0, 2), 4))
        self.assertFalse(board.is_valid_move(CellPosition(0, 2), 5))
        self.assertFalse(board.is_complete())


class SolverTests(unittest.TestCase):
    def test_solver_fills_puzzle_and_reports_solved(self) -> None:
        board = Board(PUZZLE, fixed=True)
        solver = SudokuSolver()
        solver.start(board, animate=False)
        while solver.status is SolverStatus.RUNNING:
            solver.solve_step(board)
        self.assertEqual(solver.status, SolverStatus.SOLVED)
        self.assertTrue(board.is_complete())
        self.assertTrue(board.is_consistent())

    def test_solver_reports_inconsistent_initial_board(self) -> None:
        board = Board()
        board.set_value(CellPosition(0, 0), 4)
        board.set_value(CellPosition(0, 1), 4)
        solver = SudokuSolver()
        solver.start(board, animate=True)
        self.assertEqual(solver.status, SolverStatus.UNSOLVABLE)

    def test_solver_advances_incrementally(self) -> None:
        board = Board(PUZZLE, fixed=True)
        solver = SudokuSolver()
        solver.start(board, animate=True)
        initial = board.to_tuple()
        self.assertTrue(solver.solve_step(board))
        self.assertNotEqual(board.to_tuple(), initial)
        self.assertEqual(solver.status, SolverStatus.RUNNING)


class GameTests(unittest.TestCase):
    def test_selection_and_entry_publish_board_event(self) -> None:
        game = SudokuGame()
        observer = RecordingObserver()
        game.attach(observer)
        game.start_solver_mode()
        game.select_cell(CellPosition(0, 0))
        self.assertTrue(game.set_cell_value(7))
        self.assertEqual(game.get_current_snapshot().board_data[0][0], 7)
        self.assertEqual(observer.events[-1].event_type, ModelEventType.BOARD_CHANGED)

    def test_elapsed_time_only_advances_during_puzzle_play(self) -> None:
        game = SudokuGame()
        game.update_elapsed_time(10)
        self.assertEqual(game.get_current_snapshot().elapsed_seconds, 0)
        game.start_game(Difficulty.EASY)
        game.update_elapsed_time(2.5)
        self.assertEqual(game.get_current_snapshot().elapsed_seconds, 2.5)

    def test_cell_values_cannot_change_while_solver_is_running(self) -> None:
        game = SudokuGame()
        game.start_solver_mode()
        game.select_cell(CellPosition(0, 0))
        game.start_solving(animate=True)
        self.assertFalse(game.set_cell_value(7))
        self.assertEqual(game.get_current_snapshot().board_data[0][0], 0)

    def test_snapshot_is_immutable(self) -> None:
        snapshot = SudokuGame().get_current_snapshot()
        with self.assertRaises((AttributeError, TypeError)):
            snapshot.version = 99  # type: ignore[misc]


class ControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = SudokuGame()
        self.renderer = FakeRenderer()
        self.view = SudokuView(self.renderer)  # type: ignore[arg-type]
        self.audio = FakeAudio()
        self.controller = GameController(self.model, self.view, FakeEvents(), self.audio)

    def test_intro_keyboard_and_menu_navigation(self) -> None:
        self.controller.handle_event(InputEvent(InputEventType.KEY_UP, key="return"))
        self.assertEqual(self.view.active_screen_type, ScreenType.MAIN_MENU)
        self.controller.dispatch_action(UIAction(UIActionType.PLAY))
        self.assertEqual(self.view.active_screen_type, ScreenType.DIFFICULTY_MENU)

    def test_difficulty_starts_puzzle_and_controls_music(self) -> None:
        self.controller.dispatch_action(UIAction(UIActionType.CHOOSE_DIFFICULTY,
                                                difficulty=Difficulty.MEDIUM))
        self.assertEqual(self.model.get_current_snapshot().difficulty, Difficulty.MEDIUM)
        self.assertEqual(self.view.active_screen_type, ScreenType.GAME)
        self.assertTrue(self.audio.paused)
        self.assertIn(SoundEffect.GAME_START, self.audio.played)

    def test_back_from_game_requires_confirmation(self) -> None:
        self.model.start_game(Difficulty.EASY)
        self.controller.dispatch_action(UIAction(UIActionType.REQUEST_RETURN_TO_MENU))
        self.assertEqual(self.view.active_dialog.type, DialogType.CONFIRM_RETURN_TO_MENU)
        self.controller.dispatch_action(UIAction(UIActionType.CANCEL))
        self.assertEqual(self.view.active_dialog.type, DialogType.NONE)

    def test_game_hit_testing_maps_cells_and_clicking_outside_deselects(self) -> None:
        self.view.show_screen(ScreenType.GAME)
        select = self.view.get_action_at((35, 135))
        self.assertEqual(select, UIAction(UIActionType.SELECT_CELL, CellPosition(0, 0)))
        self.controller.dispatch_action(select)  # type: ignore[arg-type]
        self.assertEqual(self.model.get_current_snapshot().selected_cell, CellPosition(0, 0))
        deselect = self.view.get_action_at((580, 750))
        self.controller.dispatch_action(deselect)  # type: ignore[arg-type]
        self.assertIsNone(self.model.get_current_snapshot().selected_cell)

    def test_auto_solve_dialog_starts_direct_solution(self) -> None:
        self.model.start_solver_mode()
        self.controller.dispatch_action(UIAction(UIActionType.REQUEST_AUTO_SOLVE))
        self.assertEqual(self.view.active_dialog.type, DialogType.AUTO_SOLVE)
        self.controller.dispatch_action(UIAction(UIActionType.DIRECT_SOLUTION))
        self.assertEqual(self.model.get_current_snapshot().status, GameStatus.SOLVED)

    def test_leaving_solved_puzzle_does_not_play_game_over_sound(self) -> None:
        self.model.start_game(Difficulty.EASY)
        self.model.start_solving(animate=False)
        self.assertEqual(self.model.get_current_snapshot().status, GameStatus.SOLVED)
        self.controller.dispatch_action(UIAction(UIActionType.CONFIRM))
        self.assertNotIn(SoundEffect.GAME_OVER, self.audio.played)

    def test_leaving_unsolvable_puzzle_plays_game_over_sound(self) -> None:
        self.model.start_game(Difficulty.EASY)
        snapshot = self.model.get_current_snapshot()
        row = next(index for index in range(9)
                   if 0 in snapshot.board_data[index])
        col = snapshot.board_data[row].index(0)
        conflict = next(value for value in snapshot.board_data[row] if value)
        self.model.select_cell(CellPosition(row, col))
        self.model.set_cell_value(conflict)
        self.model.start_solving(animate=False)
        self.assertEqual(self.model.get_current_snapshot().status, GameStatus.UNSOLVABLE)
        self.controller.dispatch_action(UIAction(UIActionType.CONFIRM))
        self.assertIn(SoundEffect.GAME_OVER, self.audio.played)

    def test_animated_solver_ignores_cell_edits_until_it_finishes(self) -> None:
        self.model.start_solver_mode()
        self.controller.dispatch_action(UIAction(UIActionType.ANIMATED_SOLUTION))
        self.controller.dispatch_action(
            UIAction(UIActionType.SELECT_CELL, CellPosition(0, 0))
        )
        self.controller.dispatch_action(UIAction(UIActionType.ENTER_DIGIT, digit=5))
        self.assertEqual(self.model.get_current_snapshot().board_data[0][0], 0)


if __name__ == "__main__":
    unittest.main()
