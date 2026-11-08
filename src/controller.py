"""Input handling and navigation controller."""

from dataclasses import dataclass
from enum import Enum, auto
import time
from typing import Protocol

from .audio import IAudioService, SoundEffect
from .model import Board, Difficulty, GameMode, GameStatus, SudokuGame
from .view import (DialogType, ScreenType, SudokuView, UIAction, UIActionType)


class InputEventType(Enum):
    QUIT = auto()
    
    KEY_DOWN = auto()
    KEY_UP = auto()

    MOUSE_BUTTON_DOWN = auto()
    MOUSE_BUTTON_UP = auto()
    MOUSE_MOTION = auto()


@dataclass(frozen=True)
class InputEvent:
    event_type: InputEventType
    key: str = ""
    mouse_position: tuple[int, int] = (0, 0)
    mouse_button: int = 0


class IEventSource(Protocol):
    def poll_events(self) -> list[InputEvent]: ...


class PyGameEventSource(IEventSource):
    def poll_events(self) -> list[InputEvent]:
        import pygame as pg

        event_types = {pg.QUIT: InputEventType.QUIT, pg.KEYDOWN: InputEventType.KEY_DOWN,
                       pg.KEYUP: InputEventType.KEY_UP,
                       pg.MOUSEBUTTONDOWN: InputEventType.MOUSE_BUTTON_DOWN,
                       pg.MOUSEBUTTONUP: InputEventType.MOUSE_BUTTON_UP,
                       pg.MOUSEMOTION: InputEventType.MOUSE_MOTION}

        events: list[InputEvent] = []

        for event in pg.event.get():
            kind = event_types.get(event.type)

            if kind is not None:
                events.append(InputEvent(kind, pg.key.name(event.key) if hasattr(event, "key") else "",
                                         getattr(event, "pos", (0, 0)),
                                         getattr(event, "button", 0)))

        return events


class GameController:
    def __init__(self, model: SudokuGame, view: SudokuView, event_source: IEventSource,
                 audio_service: IAudioService) -> None:
        self._model, self._view = model, view
        self._event_source, self._audio_service = event_source, audio_service

        self._running = True
        self._animated_solving = False

        self._last_tick = time.monotonic()

        self._completion_sound_played = False

        model.attach(view)

    def run(self) -> None:
        import pygame as pg

        self._audio_service.play_background_music()

        clock = pg.time.Clock()

        while self._running:
            for event in self._event_source.poll_events():
                self.handle_event(event)

            self.update()

            self._view.render_if_dirty()

            clock.tick(60)

        self._view.close()

    def update(self) -> None:
        now = time.monotonic()
        delta = max(0.0, now - self._last_tick)

        self._last_tick = now

        snapshot = self._model.get_current_snapshot()

        if snapshot.mode is GameMode.PUZZLE and snapshot.status is GameStatus.PLAYING:
            self._model.update_elapsed_time(delta)

        if self._animated_solving:
            self.handle_solver_step()

    def handle_event(self, event: InputEvent) -> None:
        if event.event_type is InputEventType.QUIT:
            self.exit_application()
        elif event.event_type in (InputEventType.KEY_DOWN, InputEventType.KEY_UP):
            action = self.handle_keyboard_input(event)

            if action is not None:
                self.dispatch_action(action)
        elif event.event_type is InputEventType.MOUSE_MOTION:
            self._view.handle_pointer_move(event.mouse_position)
        elif event.event_type in (InputEventType.MOUSE_BUTTON_DOWN, InputEventType.MOUSE_BUTTON_UP):
            action = self.handle_mouse_input(event)

            if action is not None:
                self.dispatch_action(action)

    def handle_keyboard_input(self, event: InputEvent) -> UIAction | None:
        if event.event_type is InputEventType.KEY_UP and event.key in ("return", "enter"):
            if self._view.active_screen_type is ScreenType.INTRO:
                return UIAction(UIActionType.CONTINUE_FROM_INTRO)
        if event.event_type is InputEventType.KEY_UP and event.key == "space":
            if self._view.active_screen_type in (ScreenType.GAME, ScreenType.SOLVER):
                return UIAction(UIActionType.REQUEST_AUTO_SOLVE)
        if event.event_type is InputEventType.KEY_DOWN:
            if event.key == "0" and self._view.active_screen_type in (ScreenType.GAME, ScreenType.SOLVER):
                return UIAction(UIActionType.CLEAR_CELL)

            if len(event.key) == 1 and event.key in "123456789" and self._view.active_screen_type in (
                    ScreenType.GAME, ScreenType.SOLVER):
                return UIAction(UIActionType.ENTER_DIGIT, digit=int(event.key))

        return None

    def handle_mouse_input(self, event: InputEvent) -> UIAction | None:
        if event.event_type is not InputEventType.MOUSE_BUTTON_UP:
            return None

        return self._view.get_action_at(event.mouse_position)

    def dispatch_action(self, action: UIAction) -> None:
        kind = action.action_type

        if self._animated_solving and kind in (
            UIActionType.SELECT_CELL,
            UIActionType.ENTER_DIGIT,
            UIActionType.CLEAR_CELL
        ):
            return

        if kind not in (UIActionType.SELECT_CELL, UIActionType.ENTER_DIGIT,
                        UIActionType.CLEAR_CELL):
            self._audio_service.play_effect(SoundEffect.CLICK)

        if kind is UIActionType.CONTINUE_FROM_INTRO:
            self._view.show_screen(ScreenType.MAIN_MENU)
        elif kind is UIActionType.PLAY:
            self._view.show_screen(ScreenType.DIFFICULTY_MENU)
        elif kind is UIActionType.OPEN_SOLVER:
            self._model.start_solver_mode()

            self._view.show_screen(ScreenType.SOLVER)
        elif kind is UIActionType.OPEN_SCORE_BOARD:
            self._view.show_screen(ScreenType.SCORE_BOARD)
        elif kind is UIActionType.EXIT:
            self.exit_application()
        elif kind is UIActionType.BACK_TO_MAIN_MENU:
            self.return_to_main_menu()
        elif kind is UIActionType.CHOOSE_DIFFICULTY and action.difficulty is not None:
            self._model.start_game(action.difficulty)

            self._completion_sound_played = False

            self._audio_service.pause_background_music()
            self._audio_service.play_effect(SoundEffect.GAME_START)

            self._view.show_screen(ScreenType.GAME)
        elif kind is UIActionType.SELECT_CELL:
            self._model.select_cell(action.cell_position)
        elif kind is UIActionType.ENTER_DIGIT and action.digit is not None:
            self._audio_service.play_effect(SoundEffect.MOVE)

            self._model.set_cell_value(action.digit)

            self._play_completion_sound()
        elif kind is UIActionType.CLEAR_CELL:
            self._model.clear_selected_cell()
        elif kind is UIActionType.REQUEST_RETURN_TO_MENU:
            if self._model.get_current_snapshot().mode is GameMode.PUZZLE:
                self._view.show_dialog(DialogType.CONFIRM_RETURN_TO_MENU)
            else:
                self.return_to_main_menu()
        elif kind is UIActionType.REQUEST_AUTO_SOLVE:
            snapshot = self._model.get_current_snapshot()

            if (snapshot.mode is GameMode.PUZZLE or
                    Board(snapshot.board_data).is_consistent()):
                self._view.show_dialog(DialogType.AUTO_SOLVE)
        elif kind is UIActionType.CANCEL:
            self._view.dismiss_dialog()
        elif kind is UIActionType.CONFIRM:
            self._view.dismiss_dialog()

            if self._model.get_current_snapshot().status is GameStatus.UNSOLVABLE:
                self._audio_service.play_effect(SoundEffect.GAME_OVER)

            self.return_to_main_menu()
        elif kind in (UIActionType.DIRECT_SOLUTION, UIActionType.ANIMATED_SOLUTION):
            self._view.dismiss_dialog()

            self._animated_solving = kind is UIActionType.ANIMATED_SOLUTION
            self._model.start_solving(self._animated_solving)

            if not self._animated_solving:
                self._play_completion_sound()

    def handle_solver_step(self) -> None:
        still_running = self._model.advance_solver_step()
        if not still_running:
            self._animated_solving = False
            self._play_completion_sound()

    def _play_completion_sound(self) -> None:
        if (self._model.get_current_snapshot().status is GameStatus.SOLVED and
                not self._completion_sound_played):
            self._audio_service.play_effect(SoundEffect.CONGRATULATIONS)
            self._completion_sound_played = True

    def return_to_main_menu(self) -> None:
        self._animated_solving = False

        self._view.dismiss_dialog()

        self._view.show_screen(ScreenType.MAIN_MENU)

        self._audio_service.resume_background_music()

    def exit_application(self) -> None:
        self._running = False
