"""Mouse swipe automation using macOS Quartz CGEvent API."""

import subprocess
import time

import Quartz


def focus_iphone_mirroring():
    """Bring iPhone Mirroring window to front."""
    subprocess.run([
        "osascript", "-e",
        'tell application "iPhone Mirroring" to activate',
    ], capture_output=True)
    time.sleep(0.5)


def _move_mouse(x: int, y: int, mouse_down: bool = False):
    """Move mouse to (x, y). If mouse_down, send a drag event instead."""
    if mouse_down:
        event = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventLeftMouseDragged, (x, y), Quartz.kCGMouseButtonLeft
        )
    else:
        event = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft
        )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def _mouse_down(x: int, y: int):
    """Press left mouse button at (x, y)."""
    event = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventLeftMouseDown, (x, y), Quartz.kCGMouseButtonLeft
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def _mouse_up(x: int, y: int):
    """Release left mouse button at (x, y)."""
    event = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventLeftMouseUp, (x, y), Quartz.kCGMouseButtonLeft
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def swipe_word(
    path: list[tuple[int, int]],
    cell_centers: list[tuple[int, int]],
    step_delay: float = 0.02,
):
    """Swipe through a word path on screen.

    path: list of (row, col) grid coordinates
    cell_centers: 16 (x, y) screen coordinates from capture.cell_centers()
    step_delay: seconds between each drag step
    """
    if not path:
        return

    # Convert grid coords to screen coords
    screen_points = []
    for row, col in path:
        idx = row * 4 + col
        screen_points.append(cell_centers[idx])

    # Move to start position
    sx, sy = screen_points[0]
    _move_mouse(sx, sy)
    time.sleep(0.01)

    # Press down
    _mouse_down(sx, sy)
    time.sleep(0.01)

    # Drag through each cell
    for px, py in screen_points[1:]:
        _move_mouse(px, py, mouse_down=True)
        time.sleep(step_delay)

    # Release
    last_x, last_y = screen_points[-1]
    _mouse_up(last_x, last_y)


def play_words(
    words_with_paths: list[tuple[str, int, list[tuple[int, int]]]],
    cell_centers: list[tuple[int, int]],
    delay: float = 0.3,
    max_words: int | None = None,
):
    """Play a list of solved words by swiping each one.

    words_with_paths: output from Board.solve() — list of (word, points, path)
    cell_centers: 16 (x, y) screen coordinates
    delay: seconds between words
    max_words: maximum number of words to play (None = all)
    """
    focus_iphone_mirroring()
    words = words_with_paths[:max_words] if max_words else words_with_paths

    for i, (word, points, path) in enumerate(words):
        swipe_word(path, cell_centers, step_delay=0.02)
        time.sleep(delay)

        # Yield progress info
        yield i + 1, len(words), word, points


def _click(x: int, y: int):
    """Click at (x, y)."""
    _mouse_down(x, y)
    time.sleep(0.02)
    _mouse_up(x, y)


def play_anagram_words(
    words_with_indices: list[tuple[str, int, list[int]]],
    tile_centers: list[tuple[int, int]],
    enter_pos: tuple[int, int],
    delay: float = 0.3,
    max_words: int | None = None,
):
    """Play anagram words by tapping tiles then ENTER.

    words_with_indices: output from AnagramSolver.solve() — list of (word, points, indices)
    tile_centers: 6 (x, y) screen coordinates for each tile
    enter_pos: (x, y) screen coordinates of the ENTER button
    delay: seconds between words
    max_words: maximum number of words to play (None = all)
    """
    focus_iphone_mirroring()
    words = words_with_indices[:max_words] if max_words else words_with_indices

    for i, (word, points, indices) in enumerate(words):
        # Tap each letter tile in order
        for idx in indices:
            tx, ty = tile_centers[idx]
            _click(tx, ty)
            time.sleep(0.05)

        # Tap ENTER
        time.sleep(0.05)
        _click(enter_pos[0], enter_pos[1])
        time.sleep(delay)

        yield i + 1, len(words), word, points
