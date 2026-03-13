"""Flask API backend for the Word Hunt Bot React UI."""

import threading
import time

from flask import Flask, jsonify, request
from flask_cors import CORS

from capture import capture_screen, find_board, extract_cells, cell_centers
from model import load_model, predict_board, MODEL_PATH
from solver import Board, load_trie
from automation import play_words

app = Flask(__name__)
CORS(app)

# Global state
state = {
    "trie": None,
    "model": None,
    "board_rect": None,
    "centers": None,
    "results": None,
    "grid": None,
    "status": "loading",
    "playing": False,
    "play_progress": None,
}


def init():
    state["status"] = "loading dictionary..."
    state["trie"] = load_trie()
    if MODEL_PATH.exists():
        state["status"] = "loading model..."
        state["model"] = load_model()
        state["status"] = "ready"
    else:
        state["status"] = "no model — run: python model.py"


threading.Thread(target=init, daemon=True).start()


@app.get("/api/status")
def get_status():
    return jsonify({
        "status": state["status"],
        "grid": state["grid"],
        "results": [
            {"word": w, "points": p, "path": path}
            for w, p, path in (state["results"] or [])
        ],
        "playing": state["playing"],
        "play_progress": state["play_progress"],
    })


@app.post("/api/capture")
def capture():
    if state["model"] is None:
        return jsonify({"error": "Model not loaded"}), 400

    state["status"] = "capturing..."
    shot = capture_screen()
    state["board_rect"] = find_board(shot)

    if state["board_rect"] is None:
        state["status"] = "board not found!"
        return jsonify({"error": "Board not found"}), 404

    cells = extract_cells(shot, state["board_rect"])
    state["centers"] = cell_centers(state["board_rect"], shot)

    grid = predict_board(state["model"], cells)
    state["grid"] = [row[:] for row in grid]

    state["status"] = "solving..."
    board = Board(grid, state["trie"])
    state["results"] = board.solve()

    total_pts = sum(p for _, p, _ in state["results"])
    state["status"] = f"found {len(state['results'])} words ({total_pts} pts)"

    return jsonify({
        "grid": state["grid"],
        "results": [
            {"word": w, "points": p, "path": path}
            for w, p, path in state["results"]
        ],
        "total_points": total_pts,
    })


@app.post("/api/play")
def play():
    if not state["results"] or not state["centers"]:
        return jsonify({"error": "No results to play"}), 400
    if state["playing"]:
        return jsonify({"error": "Already playing"}), 400

    delay = request.json.get("delay", 0.3) if request.json else 0.3
    max_words = request.json.get("max_words", 100) if request.json else 100

    def run():
        state["playing"] = True
        for progress in play_words(state["results"], state["centers"], delay, max_words):
            if not state["playing"]:
                break
            i, total, word, pts = progress
            state["play_progress"] = {"current": i, "total": total, "word": word, "points": pts}
            state["status"] = f"playing {i}/{total}: {word} ({pts}pts)"
        state["playing"] = False
        state["play_progress"] = None
        state["status"] = "done!"

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})


@app.post("/api/stop")
def stop():
    state["playing"] = False
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(port=5050, debug=False)
