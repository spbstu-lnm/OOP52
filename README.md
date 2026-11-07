# Sudoku

A pygame Sudoku game and interactive Sudoku solver, refactored to fit OOP paradigm.

## Run

Install the dependency listed in `requirements.txt`, then launch the application from this directory:

```bash
python sudoku.py
```

The game retains four difficulty levels, the manual solver, invalid-entry highlighting, the timer, confirmation dialogs, direct solving, animated solving, and the existing sound effects and background music.

## Architecture

- `model.py`: board and cell domain objects, snapshots, model events, the puzzle repository, and `SudokuGame`.
- `solver.py`: incremental `SudokuSolver` and backtracking helpers.
- `controller.py`: pygame input adapter and `GameController` navigation and action handling.
- `view.py`: screen and dialog hit testing, observer view, and pygame renderer.
- `audio.py`: audio interface and pygame implementation.
- `boards.py`: built-in puzzle data and compatibility helpers.

## Unit tests

Run the suite with:

```bash
python -m unittest discover -s tests -v
```
