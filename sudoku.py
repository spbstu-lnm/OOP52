#!/usr/bin/env python3
"""Application entry point for the Sudoku pygame game."""

from audio import PyGameAudioService
from controller import GameController, PyGameEventSource
from model import SudokuGame
from view import PyGameRenderer, SudokuView


def main() -> None:
    renderer = PyGameRenderer()
    model = SudokuGame()
    view = SudokuView(renderer)
    controller = GameController(model, view, PyGameEventSource(), PyGameAudioService())
    controller.run()


if __name__ == "__main__":
    main()
