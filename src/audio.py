"""Audio service abstraction and pygame implementation."""

from enum import Enum, auto
from pathlib import Path
from typing import Protocol


class SoundEffect(Enum):
    CLICK = auto()
    MOVE = auto()
    GAME_START = auto()
    GAME_OVER = auto()
    CONGRATULATIONS = auto()


class IAudioService(Protocol):
    def play_effect(self, effect: SoundEffect) -> None: ...
    def play_background_music(self) -> None: ...
    def pause_background_music(self) -> None: ...
    def resume_background_music(self) -> None: ...


class PyGameAudioService(IAudioService):
    def __init__(self, asset_directory: Path | None = None) -> None:
        import pygame

        self._pygame = pygame

        # asset dir path can be passed via args
        self._asset_directory = asset_directory or Path(__file__).resolve().parent.parent / "assets" / "audio"

        self._effects: dict[SoundEffect, object] = {}
        self._enabled = False

        try:
            pygame.mixer.init()

            names = {SoundEffect.CLICK: "click.ogg", SoundEffect.MOVE: "move.ogg",
                     SoundEffect.GAME_START: "gameStart.ogg", SoundEffect.GAME_OVER: "gameOver.ogg",
                     SoundEffect.CONGRATULATIONS: "congratulation.ogg"}

            self._effects = {effect: pygame.mixer.Sound(str(self._asset_directory / name))
                             for effect, name in names.items()}

            pygame.mixer.music.load(str(self._asset_directory / "backgroundMusic.ogg"))

            self._enabled = True
        except pygame.error:
            self._enabled = False

    def play_effect(self, effect: SoundEffect) -> None:
        if self._enabled and effect in self._effects:
            self._effects[effect].play()

    def play_background_music(self) -> None:
        if self._enabled:
            self._pygame.mixer.music.play(-1)

    def pause_background_music(self) -> None:
        if self._enabled:
            self._pygame.mixer.music.pause()

    def resume_background_music(self) -> None:
        if self._enabled:
            self._pygame.mixer.music.unpause()
