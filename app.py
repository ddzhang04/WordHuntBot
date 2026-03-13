"""Word Hunt / Anagram Bot — pywebview desktop app."""

import json
import os
import threading

import webview

from capture import (
    capture_screen, find_board, extract_cells, cell_centers,
    find_anagram_tiles, extract_anagram_cells, anagram_tile_centers, find_enter_button,
)
from model import load_model, predict_board, predict_letter, MODEL_PATH
from solver import Board, AnagramSolver, load_trie
from automation import play_words, play_anagram_words


class Api:
    def __init__(self):
        self.trie = None
        self.model = None
        self.status = "loading"
        self.playing = False
        # Word Hunt state
        self._centers = None
        self._results = None
        # Anagram state
        self._anagram_centers = None
        self._anagram_enter = None

        threading.Thread(target=self._init, daemon=True).start()

    def _init(self):
        self.status = "loading dictionary..."
        self.trie = load_trie()
        if MODEL_PATH.exists():
            self.status = "loading model..."
            self.model = load_model()
            self.status = "ready"
        else:
            self.status = "no model — run: python model.py"

    def get_status(self):
        return self.status

    def capture_wordhunt(self):
        if self.model is None:
            return json.dumps({"error": "Model not loaded"})

        self.status = "capturing..."
        shot = capture_screen()
        board_rect = find_board(shot)

        if board_rect is None:
            self.status = "board not found!"
            return json.dumps({"error": "Board not found"})

        cells = extract_cells(shot, board_rect)
        self._centers = cell_centers(board_rect, shot)

        grid = predict_board(self.model, cells)

        self.status = "solving..."
        board = Board(grid, self.trie)
        self._results = board.solve()

        total_pts = sum(p for _, p, _ in self._results)
        self.status = f"found {len(self._results)} words ({total_pts} pts)"

        return json.dumps({
            "grid": grid,
            "results": [
                {"word": w, "points": p, "path": path}
                for w, p, path in self._results
            ],
            "total_points": total_pts,
        })

    def capture_anagram(self):
        if self.model is None:
            return json.dumps({"error": "Model not loaded"})

        self.status = "capturing anagram..."
        shot = capture_screen()
        tiles = find_anagram_tiles(shot)

        if tiles is None:
            self.status = "tiles not found!"
            return json.dumps({"error": "Anagram tiles not found"})

        self._anagram_centers = anagram_tile_centers(tiles, shot)
        self._anagram_enter = find_enter_button(tiles, shot)

        cells = extract_anagram_cells(shot, tiles)
        letters = [predict_letter(self.model, cell) for cell in cells]

        self.status = "solving anagram..."
        solver = AnagramSolver(letters, self.trie)
        self._results = solver.solve()

        total_pts = sum(p for _, p, _ in self._results)
        self.status = f"found {len(self._results)} words ({total_pts} pts)"

        return json.dumps({
            "letters": letters,
            "results": [
                {"word": w, "points": p, "indices": indices}
                for w, p, indices in self._results
            ],
            "total_points": total_pts,
        })

    def play_wordhunt(self, delay, max_words):
        if not self._results or not self._centers:
            return json.dumps({"error": "No results"})
        self.playing = True

        def run():
            for progress in play_words(self._results, self._centers, delay, max_words):
                if not self.playing:
                    break
                i, total, word, pts = progress
                self.status = f"playing {i}/{total}: {word} ({pts}pts)"
            self.playing = False
            self.status = "done!"

        threading.Thread(target=run, daemon=True).start()
        return json.dumps({"ok": True})

    def play_anagram(self, delay, max_words):
        if not self._results or not self._anagram_centers:
            return json.dumps({"error": "No results"})
        self.playing = True

        def run():
            for progress in play_anagram_words(
                self._results, self._anagram_centers,
                self._anagram_enter, delay, max_words,
            ):
                if not self.playing:
                    break
                i, total, word, pts = progress
                self.status = f"playing {i}/{total}: {word} ({pts}pts)"
            self.playing = False
            self.status = "done!"

        threading.Thread(target=run, daemon=True).start()
        return json.dumps({"ok": True})

    def stop(self):
        self.playing = False
        return json.dumps({"ok": True})


def main():
    api = Api()

    # Use built React app if available, otherwise dev server
    build_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
    if os.path.isdir(build_dir):
        url = f"file://{os.path.join(build_dir, 'index.html')}"
    else:
        url = "http://localhost:5173"

    window = webview.create_window(
        "Word Hunt Bot",
        url=url,
        js_api=api,
        width=920,
        height=640,
        min_size=(700, 500),
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
