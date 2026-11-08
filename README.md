# Sudoku

A pygame Sudoku game and interactive Sudoku solver, refactored to fit OOP paradigm.

## Run

Install the dependency listed in `requirements.txt`, then launch the application from the project root:

```bash
python -m src.sudoku
```

The game retains four difficulty levels, the manual solver, invalid-entry highlighting, the timer, confirmation dialogs, direct solving, animated solving, and the existing sound effects and background music.

## Architecture

- `src/model.py`: board and cell domain objects, snapshots, model events, the puzzle repository, and `SudokuGame`.
- `src/solver.py`: incremental `SudokuSolver` and backtracking helpers.
- `src/controller.py`: pygame input adapter and `GameController` navigation and action handling.
- `src/view.py`: screen and dialog hit testing, observer view, and pygame renderer.
- `src/audio.py`: audio interface and pygame implementation.
- `src/boards.py`: built-in puzzle data and compatibility helpers.
- `assets/audio/`: sound effects and background music.
- `assets/fonts/`: fonts used by the renderer.

## Unit tests

Run the suite with:

```bash
python -m unittest discover -s tests -v
```
