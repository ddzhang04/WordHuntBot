# WordHuntBot

![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)
![PyTorch 2.0+](https://img.shields.io/badge/PyTorch-2.0%2B-orange)
![macOS Sonoma 15.0+](https://img.shields.io/badge/macOS-Sonoma%2015.0%2B-lightgrey)
![License MIT](https://img.shields.io/badge/License-MIT-green)

A GamePigeon automation bot for **Word Hunt** and **Anagrams**. Captures the game board from iPhone Mirroring, recognizes letters with a CNN, solves for all valid words, and automatically plays them via mouse simulation.

## How It Works

1. **Screen Capture** -- Uses the macOS Quartz API to capture the iPhone Mirroring window directly, handling Retina 2x scaling automatically.
2. **Board Detection** -- OpenCV color detection finds the tan/beige wooden tiles on screen. For Word Hunt it detects the 4x4 grid; for Anagrams it finds the 6-tile row and the ENTER button.
3. **Letter Recognition** -- A PyTorch CNN trained on labeled screenshots predicts each letter. The model uses CLAHE contrast enhancement and Otsu thresholding for preprocessing, with data augmentation and oversampling to handle class imbalance.
4. **Word Solving** -- A trie-based dictionary enables fast prefix pruning during DFS. Word Hunt uses 8-directional adjacency search on the grid. Anagrams uses permutation search with a used-letter array.
5. **Automation** -- Quartz CGEvent API simulates mouse input. Word Hunt words are played by swiping through cell centers. Anagram words are played by tapping tiles in sequence then tapping the ENTER button. The bot focuses the iPhone Mirroring window before playing.

## Features

- Two game modes: Word Hunt (4x4 grid, swipe) and Anagrams (6 tiles, tap + enter)
- One-click "Go" button that captures, solves, and plays automatically
- Manual letter editing with a "Solve" button to correct CNN mistakes and re-solve
- Global Escape hotkey to stop playback at any time
- Dark dashboard UI built with React, embedded in a native window via pywebview
- No external server required -- everything runs in a single process

## Requirements

- macOS (requires Quartz API and iPhone Mirroring)
- Python 3.9+
- Node.js 18+ (for building the frontend)
- iPhone Mirroring app open with the GamePigeon game visible

## Installation

```bash
git clone https://github.com/ddzhang04/WordHuntBot.git
cd WordHuntBot

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pywebview pynput

# Frontend build
cd frontend
npm install
npm run build
cd ..
```

## Usage

```bash
source venv/bin/activate
python app.py
```

This opens a desktop window with the bot UI. Make sure iPhone Mirroring is open with the game visible.

### Controls

- **Go** -- Captures the board, recognizes letters, solves all words, then auto-plays them.
- **Solve** -- Re-solves using the currently displayed letters (useful after manual edits) and auto-plays.
- **Stop (Esc)** -- Stops playback. Also triggered by pressing Escape anywhere.
- **Mode toggle** -- Switch between Word Hunt and Anagrams in the top bar.
- **Click any tile** -- Edit the letter manually. Press Tab or Enter to move to the next tile.

### CLI Mode

You can also run the solver directly from the command line without the GUI:

```bash
python main.py "obdr lthe cdht weac"
```

Provide the 4x4 board as four groups of four letters.

## Training the CNN

The CNN is trained on labeled screenshots of game tiles.

### Collecting Training Data

```bash
# Interactive labeling from a live capture
python dataset.py

# Auto-label with a known board
python dataset.py auto "abcdefghijklmnop"

# View dataset statistics
python dataset.py stats
```

### Training

```bash
python model.py
```

Trains for 50 epochs with data augmentation (rotation, scale, shift, noise) and oversampling to balance class distribution. The trained model is saved to `model.pth`.

## Project Structure

```
WordHuntBot/
  app.py              Desktop app (pywebview + Python API)
  solver.py           Trie dictionary, Board solver, AnagramSolver
  capture.py          Screen capture, board/tile detection, cell extraction
  model.py            CNN model definition, training, and inference
  automation.py       Mouse simulation (swipe for Word Hunt, tap for Anagrams)
  dataset.py          Interactive tool for labeling training data
  main.py             CLI solver interface
  dictionary.txt      Word list (~364K words)
  model.pth           Trained CNN weights
  requirements.txt    Python dependencies
  dataset/            Training images organized by letter (a-z/)
  frontend/
    src/App.jsx       React UI component
    src/App.css       Dashboard styles
    dist/             Built frontend (loaded by pywebview)
```

## Technical Details

### Solver

The dictionary is loaded into a trie for O(1) prefix lookups. During DFS, branches are pruned as soon as the current path is not a valid prefix, keeping the search fast even on large dictionaries.

Word Hunt scoring: 3 letters = 100 pts, 4 = 400, 5 = 800, 6 = 1400, 7 = 1800, 8 = 2200, 9+ = 2200 + 400 per additional letter.

### CNN Architecture

- Input: 32x32 grayscale image (preprocessed with CLAHE + Otsu threshold)
- Conv1: 32 filters, 3x3, ReLU, MaxPool 2x2
- Conv2: 64 filters, 3x3, ReLU, MaxPool 2x2
- FC1: 4096 to 128, ReLU, Dropout 0.5
- FC2: 128 to 26 (one per letter)

### Coordinate System

Screenshots from Quartz are captured at Retina resolution (2x on most Macs), but mouse events operate in logical screen coordinates. The bot detects the scale factor by comparing the captured image dimensions to the window bounds reported by the Quartz window list API.

## Limitations

- macOS only (depends on Quartz APIs and iPhone Mirroring)
- CNN accuracy depends on training data coverage; some letter pairs (G/S, B/O) can be confused with limited samples -- use manual editing to correct
- Board detection relies on the tan tile color; different game themes or lighting conditions may require adjusting HSV ranges in capture.py
