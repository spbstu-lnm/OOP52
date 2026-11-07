"""Screen state, hit testing, and pygame rendering adapters."""

from dataclasses import dataclass
from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import Protocol

from model import (CellPosition, Difficulty, GameSnapshot, IObserver, ModelEvent,
                   ModelEventType)


class UIActionType(Enum):
    CONTINUE_FROM_INTRO = auto()
    PLAY = auto()
    OPEN_SOLVER = auto()
    OPEN_SCORE_BOARD = auto()
    EXIT = auto()
    BACK_TO_MAIN_MENU = auto()
    CHOOSE_DIFFICULTY = auto()

    SELECT_CELL = auto()
    ENTER_DIGIT = auto()
    CLEAR_CELL = auto()

    REQUEST_RETURN_TO_MENU = auto()
    REQUEST_AUTO_SOLVE = auto()

    CONFIRM = auto()
    CANCEL = auto()

    DIRECT_SOLUTION = auto()
    ANIMATED_SOLUTION = auto()


class ScreenType(Enum):
    INTRO = auto()

    MAIN_MENU = auto()
    DIFFICULTY_MENU = auto()
    SCORE_BOARD = auto()

    GAME = auto()
    SOLVER = auto()


class DialogType(Enum):
    NONE = auto()

    CONFIRM_RETURN_TO_MENU = auto()
    AUTO_SOLVE = auto()


@dataclass(frozen=True)
class UIAction:
    action_type: UIActionType

    cell_position: CellPosition | None = None
    digit: int | None = None
    difficulty: Difficulty | None = None
    dialog_type: DialogType | None = None


class IRenderer(Protocol):
    def render_screen(self, screen: ScreenView, snapshot: GameSnapshot | None) -> None: ...
    def render_dialog(self, dialog: DialogView) -> None: ...
    def present(self) -> None: ...
    def close(self) -> None: ...


class ScreenView(ABC):
    def __init__(self) -> None:
        self._hovered_action: UIAction | None = None

    @property
    def hovered_action(self) -> UIAction | None:
        return self._hovered_action

    def set_hovered_action(self, action: UIAction | None) -> None:
        self._hovered_action = action

    @abstractmethod
    def hit_test(self, position: tuple[int, int]) -> UIAction | None:
        raise NotImplementedError


class IntroScreen(ScreenView):
    def hit_test(self, position: tuple[int, int]) -> UIAction | None:
        return None


class MainMenuScreen(ScreenView):
    _menu_items = (("play", (180, 300, 240, 70)), ("solver", (150, 400, 300, 70)),
                   ("score", (80, 500, 440, 70)), ("exit", (185, 600, 230, 70)))

    def hit_test(self, position: tuple[int, int]) -> UIAction | None:
        x, y = position

        if 300 <= y <= 370 and 150 <= x <= 450: return UIAction(UIActionType.PLAY)
        if 400 <= y <= 470 and 120 <= x <= 480: return UIAction(UIActionType.OPEN_SOLVER)
        if 500 <= y <= 570 and 50 <= x <= 550: return UIAction(UIActionType.OPEN_SCORE_BOARD)
        if 600 <= y <= 680 and 150 <= x <= 450: return UIAction(UIActionType.EXIT)

        return None


class DifficultyMenuScreen(ScreenView):
    _difficulties = ((Difficulty.EASY, (180, 300, 240, 70)),
                     (Difficulty.MEDIUM, (145, 400, 310, 70)),
                     (Difficulty.HARD, (180, 500, 240, 70)),
                     (Difficulty.VERY_HARD, (110, 600, 380, 70)))

    def hit_test(self, position: tuple[int, int]) -> UIAction | None:
        x, y = position

        for difficulty, (left, top, width, height) in self._difficulties:
            if left <= x <= left + width and top <= y <= top + height:
                return UIAction(UIActionType.CHOOSE_DIFFICULTY, difficulty=difficulty)

        if x < 240 and y < 100: return UIAction(UIActionType.BACK_TO_MAIN_MENU)

        return None


class ScoreBoardScreen(ScreenView):
    def hit_test(self, position: tuple[int, int]) -> UIAction | None:
        x, y = position

        if x < 240 and y < 100: return UIAction(UIActionType.BACK_TO_MAIN_MENU)

        return None


class GameScreen(ScreenView):
    def hit_test(self, position: tuple[int, int]) -> UIAction | None:
        x, y = position

        if x < 220 and y < 90: return UIAction(UIActionType.REQUEST_RETURN_TO_MENU)

        if 2 <= x < 596 and 100 <= y < 694:
            return UIAction(UIActionType.SELECT_CELL,
                            CellPosition((y - 100) // 66, (x - 2) // 66))

        return UIAction(UIActionType.SELECT_CELL)


class SolverScreen(GameScreen):
    pass


class DialogView:
    def __init__(self) -> None:
        self._type = DialogType.NONE
        self._message = ""
        self._actions: tuple[UIActionType, ...] = ()
        self._hovered_action: UIAction | None = None

    @property
    def type(self) -> DialogType:
        return self._type

    @property
    def message(self) -> str:
        return self._message

    @property
    def actions(self) -> tuple[UIActionType, ...]:
        return self._actions

    @property
    def hovered_action(self) -> UIAction | None:
        return self._hovered_action

    def set_hovered_action(self, action: UIAction | None) -> None:
        self._hovered_action = action

    def configure(self, dialog_type: DialogType) -> None:
        self._type = dialog_type
        self._hovered_action = None

        if dialog_type is DialogType.CONFIRM_RETURN_TO_MENU:
            self._message = "Are you sure? You will lose your progress!"
            self._actions = (UIActionType.CANCEL, UIActionType.CONFIRM)
        elif dialog_type is DialogType.AUTO_SOLVE:
            self._message = "Solve this puzzle directly or watch the animation?"
            self._actions = (UIActionType.CANCEL, UIActionType.DIRECT_SOLUTION,
                             UIActionType.ANIMATED_SOLUTION)
        else:
            self._message, self._actions = "", ()

    def hit_test(self, position: tuple[int, int]) -> UIAction | None:
        x, y = position

        if self.type is DialogType.NONE: return None

        if 100 <= x <= 280 and 400 <= y <= 490: return UIAction(UIActionType.CANCEL)

        if self.type is DialogType.CONFIRM_RETURN_TO_MENU and 370 <= x <= 500 and 400 <= y <= 490:
            return UIAction(UIActionType.CONFIRM)

        if self.type is DialogType.AUTO_SOLVE:
            if 300 <= x <= 540 and 360 <= y <= 440: return UIAction(UIActionType.DIRECT_SOLUTION)
            if 290 <= x <= 540 and 450 <= y <= 530: return UIAction(UIActionType.ANIMATED_SOLUTION)

        return None


class SudokuView(IObserver):
    def __init__(self, renderer: IRenderer) -> None:
        self._renderer = renderer
        self._last_snapshot: GameSnapshot | None = None
        self._dirty = True
        self._hovered_action: UIAction | None = None
        self._screens: dict[ScreenType, ScreenView] = {
            ScreenType.INTRO: IntroScreen(), ScreenType.MAIN_MENU: MainMenuScreen(),
            ScreenType.DIFFICULTY_MENU: DifficultyMenuScreen(),
            ScreenType.SCORE_BOARD: ScoreBoardScreen(), ScreenType.GAME: GameScreen(),
            ScreenType.SOLVER: SolverScreen()
        }
        self._active_screen_type = ScreenType.INTRO
        self._active_screen: ScreenView = self._screens[ScreenType.INTRO]
        self._active_dialog = DialogView()

    @property
    def active_screen_type(self) -> ScreenType:
        return self._active_screen_type

    @property
    def active_dialog(self) -> DialogView:
        return self._active_dialog

    def update(self, event: ModelEvent) -> None:
        self._last_snapshot, self._dirty = event.snapshot, True

    def show_screen(self, screen: ScreenType) -> None:
        self._active_screen_type = screen

        self._screens[screen].set_hovered_action(None)

        self._active_screen, self._dirty = self._screens[screen], True

    def show_dialog(self, dialog: DialogType) -> None:
        self._active_dialog.configure(dialog)
        self._dirty = True

    def dismiss_dialog(self) -> None:
        self.show_dialog(DialogType.NONE)

    def get_action_at(self, position: tuple[int, int]) -> UIAction | None:
        action = self._active_dialog.hit_test(position)

        if self._active_dialog.type is not DialogType.NONE:
            return action

        return self._active_screen.hit_test(position)

    def handle_pointer_move(self, position: tuple[int, int]) -> None:
        self._hovered_action = self.get_action_at(position)
        self._active_screen.set_hovered_action(self._hovered_action)
        self._active_dialog.set_hovered_action(
            self._active_dialog.hit_test(position)
            if self._active_dialog.type is not DialogType.NONE else None
        )
        self._dirty = True

    def render_if_dirty(self) -> None:
        if self._dirty:
            screen = self._active_screen
            self._renderer.render_screen(screen, self._last_snapshot)

            if self._active_dialog.type is not DialogType.NONE:
                self._renderer.render_dialog(self._active_dialog)

            self._renderer.present()
            self._dirty = False

    def close(self) -> None:
        self._renderer.close()


class PyGameRenderer(IRenderer):
    WIDTH = 600
    HEIGHT = 800

    def __init__(self) -> None:
        import pygame as pg
        from pathlib import Path

        self._pg = pg
        # path to assets hardcoded as parent directory
        self._assets = Path(__file__).resolve().parent

        pg.init()

        self._screen = pg.display.set_mode((self.WIDTH, self.HEIGHT))
        pg.display.set_caption("~SUDOKU~")

        self._font_path = self._assets / "RobotoSlab-Bold.ttf"
        self._number_path = self._assets / "TypeWrongSmudgedBold.ttf"
        self._logo_path = self._assets / "SEASRN__.ttf"

        self._active_screen: ScreenView = IntroScreen()
        self._last_screen_family: str | None = None

    def _text(self, text: str, size: int, color: tuple[int, int, int],
              center: tuple[int, int], font_path: object | None = None) -> None:
        font = self._pg.font.Font(font_path or self._font_path, size)
        surface = font.render(text, True, color)

        self._screen.blit(surface, surface.get_rect(center=center))

    def render_screen(self, screen: ScreenView, snapshot: GameSnapshot | None) -> None:
        self._active_screen = screen

        family = "game" if isinstance(screen, GameScreen) else type(screen).__name__
        if family != self._last_screen_family:
            if family == "IntroScreen":
                self._animate_grid(intro=True)
            elif family == "MainMenuScreen":
                self._animate_grid(intro=True)
            elif family == "game":
                self._animate_grid(intro=False)

            self._last_screen_family = family

        self._screen.fill((20, 20, 20))

        if isinstance(screen, (IntroScreen, MainMenuScreen)):
            self._draw_menu_background()

        if isinstance(screen, (GameScreen, SolverScreen)):
            self._draw_board(snapshot)
            self._menu_back(screen, center=(120, 40), rect=(20, 25, 200, 40),
                            action_types=(UIActionType.REQUEST_RETURN_TO_MENU,))

            self._text("Press [SPACE] to Autosolve", 25, (80, 80, 80), (300, 750))

            if snapshot is not None and snapshot.elapsed_seconds:
                seconds = int(snapshot.elapsed_seconds)
                self._text(f"{seconds // 60}:{seconds % 60:02d}", 28,
                           (240, 240, 240), (510, 45), self._number_path)

            if snapshot is not None and snapshot.message:
                self._text(snapshot.message, 22, (240, 240, 240), (300, 710))

            return

        self._text("SUDOKU", 88, (240, 240, 240), (300, 190), self._logo_path)

        if isinstance(screen, IntroScreen):
            self._text("Press ENTER to continue", 26, (150, 150, 150), (300, 500))
        elif isinstance(screen, MainMenuScreen):
            entries = (("PLAY", 335, UIActionType.PLAY),
                       ("SOLVER", 435, UIActionType.OPEN_SOLVER),
                       ("SCORE BOARD", 535, UIActionType.OPEN_SCORE_BOARD),
                       ("EXIT", 635, UIActionType.EXIT))

            for label, y, action_type in entries:
                hovered = screen.hovered_action is not None and screen.hovered_action.action_type is action_type

                self._text(f"-: {label} :-", 56 if hovered else 45,
                           (240, 240, 240), (300, y))
        elif isinstance(screen, DifficultyMenuScreen):
            self._menu_back(screen)

            entries = (("EASY", 335, Difficulty.EASY), ("MEDIUM", 435, Difficulty.MEDIUM),
                       ("HARD", 535, Difficulty.HARD), ("VERY HARD", 635, Difficulty.VERY_HARD))

            for label, y, difficulty in entries:
                hovered = (screen.hovered_action is not None and
                           screen.hovered_action.difficulty is difficulty)

                self._text(f"-: {label} :-", 54 if hovered else 43,
                           (240, 240, 240), (300, y))
        elif isinstance(screen, ScoreBoardScreen):
            self._text("-: SCORE BOARD :-", 40, (240, 240, 240), (300, 500))
            self._menu_back(screen)

    def _menu_back(
        self,
        screen: ScreenView,
        center: tuple[int, int] = (140, 60),
        rect: tuple[int, int, int, int] = (50, 45, 180, 40),
        action_types: tuple[UIActionType, ...] = (UIActionType.BACK_TO_MAIN_MENU,),
    ) -> None:
        hovered = (screen.hovered_action is not None and
                   screen.hovered_action.action_type in action_types)

        if hovered:
            self._pg.draw.rect(self._screen, (240, 240, 240), rect)

        self._text("[main menu]", 25,
                   (20, 20, 20) if hovered else (240, 240, 240), center)

    def _animate_grid(self, intro: bool) -> None:
        """Keep the original progressive grid reveal when entering board screens."""
        pg = self._pg

        self._screen.fill((20, 20, 20))

        if intro:
            x_start, x_end, vertical_count = 4, 532, 9
            vertical_y_start, vertical_y_end = 0, 800
            horizontal_x_start, horizontal_x_end = 0, 600
            horizontal_y_start, horizontal_y_end = 100, 694
        else:
            x_start, x_end, vertical_count = 2, 596, 10
            vertical_y_start, vertical_y_end = 100, 694
            horizontal_x_start, horizontal_x_end = 2, 596
            horizontal_y_start, horizontal_y_end = 100, 694

        horizontal_count = (horizontal_y_end - horizontal_y_start) // 66 + 1

        steps = 15
        for step in range(1, steps + 1):
            visible_x = max(1, step * vertical_count // steps)
            visible_y = max(1, step * horizontal_count // steps)

            for index in range(visible_x):
                x = x_start + index * 66
                if x <= x_end:
                    width = 6 if index % 3 == 0 else 3
                    color = (80, 80, 80) if width == 6 else (40, 40, 40)
                    vertical_end = (vertical_y_end if intro else
                                    vertical_y_start +
                                    (vertical_y_end - vertical_y_start) * step // steps)

                    pg.draw.line(self._screen, color, (x, vertical_y_start),
                                 (x, vertical_end), width)

            for index in range(visible_y):
                y = horizontal_y_start + index * 66
                if y <= horizontal_y_end:
                    width = 6 if index % 3 == 0 else 3
                    color = (80, 80, 80) if width == 6 else (40, 40, 40)
                    horizontal_end = (horizontal_x_end if intro else
                                      horizontal_x_start +
                                      (horizontal_x_end - horizontal_x_start) * step // steps)

                    pg.draw.line(self._screen, color, (horizontal_x_start, y),
                                 (horizontal_end, y), width)

            pg.display.update()
            pg.time.delay(20)

    def _draw_menu_background(self) -> None:
        for x_index in range(9):
            x = 4 + x_index * 66
            color = (40, 40, 40) if x_index % 3 == 0 else (30, 30, 30)
            width = 6 if x_index % 3 == 0 else 3
            self._pg.draw.line(self._screen, color, (x, 0), (x, 800), width)

        for y_index in range(10):
            y = 100 + y_index * 66
            color = (40, 40, 40) if y_index % 3 == 0 else (30, 30, 30)
            width = 6 if y_index % 3 == 0 else 3
            self._pg.draw.line(self._screen, color, (0, y), (600, y), width)

    def _draw_board(self, snapshot: GameSnapshot | None) -> None:
        pg = self._pg

        completed = snapshot is not None and all(
            value != 0 for row in snapshot.board_data for value in row
        ) and not snapshot.invalid_cells

        line_color = (40, 160, 30) if completed else (80, 80, 80)

        for index in range(10):
            width = 6 if index % 3 == 0 else 3

            pg.draw.line(self._screen, line_color, (2, 100 + index * 66),
                         (596, 100 + index * 66), width)
            pg.draw.line(self._screen, line_color, (2 + index * 66, 100),
                         (2 + index * 66, 694), width)

        if snapshot is None: return

        invalid = set(snapshot.invalid_cells)

        for row in range(9):
            for col in range(9):
                position = CellPosition(row, col)
                value = snapshot.board_data[row][col]

                if snapshot.selected_cell == position:
                    pg.draw.rect(self._screen, (80, 80, 80),
                                 (col * 66 + 8, row * 66 + 106, 54, 60))
                elif (self._current_screen_hover(position)):
                    pg.draw.rect(self._screen, (40, 40, 40),
                                 (col * 66 + 8, row * 66 + 106, 54, 60))
                if value:
                    color = (170, 10, 10) if position in invalid else (
                        (150, 150, 150) if snapshot.fixed_cells[row][col] else (240, 240, 240))

                    self._text(str(value), 36, color,
                               (col * 66 + 29, row * 66 + 130), self._number_path)

    def _current_screen_hover(self, position: CellPosition) -> bool:
        return (isinstance(self._active_screen, GameScreen) and
                self._active_screen.hovered_action is not None and
                self._active_screen.hovered_action.cell_position == position)

    def render_dialog(self, dialog: DialogView) -> None:
        pg = self._pg
        self._dialog_hovered_action = dialog.hovered_action

        height = 250 if dialog.type is DialogType.AUTO_SOLVE else 200

        pg.draw.rect(self._screen, (0, 0, 0), (0, 300, 600, height))

        self._text(dialog.message, 21, (240, 240, 240), (300, 350))

        self._dialog_action("[CANCEL]", UIActionType.CANCEL, (190, 445))

        if dialog.type is DialogType.CONFIRM_RETURN_TO_MENU:
            self._dialog_action("[OK]", UIActionType.CONFIRM, (430, 445))
        elif dialog.type is DialogType.AUTO_SOLVE:
            self._dialog_action("[SOLUTION]", UIActionType.DIRECT_SOLUTION, (410, 405))

            self._dialog_action("[ANIMATION]", UIActionType.ANIMATED_SOLUTION, (410, 495))

    def _dialog_action(self, label: str, action: UIActionType,
                       center: tuple[int, int]) -> None:
        hovered = self._active_dialog_hovered(action)

        color = (20, 20, 20) if hovered else (240, 240, 240)

        if hovered:
            width = 190 if action in (UIActionType.DIRECT_SOLUTION,
                                      UIActionType.ANIMATED_SOLUTION) else 150

            self._pg.draw.rect(self._screen, (240, 240, 240),
                              (center[0] - width // 2, center[1] - 20, width, 40))

        self._text(label, 26, color, center)

    def _active_dialog_hovered(self, action_type: UIActionType) -> bool:
        return (getattr(self, "_dialog_hovered_action", None) is not None and
                self._dialog_hovered_action.action_type is action_type)

    def present(self) -> None:
        self._pg.display.update()

    def close(self) -> None:
        self._pg.quit()
