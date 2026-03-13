"""Mouse swipe automation using macOS Quartz CGEvent API."""

import time

import Quartz


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
    words = words_with_paths[:max_words] if max_words else words_with_paths

    for i, (word, points, path) in enumerate(words):
        swipe_word(path, cell_centers, step_delay=0.02)
        time.sleep(delay)

        # Yield progress info
        yield i + 1, len(words), word, points
