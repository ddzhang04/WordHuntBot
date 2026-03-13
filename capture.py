"""Screen capture and game board detection via iPhone Mirroring."""

from dataclasses import dataclass

import cv2
import numpy as np
import Quartz


@dataclass
class Screenshot:
    """Captured screenshot with metadata."""
    image: np.ndarray
    window_origin: tuple[int, int]  # (x, y) of the window on screen


def capture_screen() -> Screenshot:
    """Capture the iPhone Mirroring window directly using Quartz.

    Falls back to full-screen capture if the window isn't found.
    """
    # Find iPhone Mirroring window
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )

    target_window = None
    for window in window_list:
        owner = window.get("kCGWindowOwnerName", "")
        name = window.get("kCGWindowName", "")
        if "iPhone Mirroring" in owner or "iPhone Mirroring" in name:
            target_window = window
            break

    if target_window:
        window_id = target_window["kCGWindowNumber"]
        cg_image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionIncludingWindow,
            window_id,
            Quartz.kCGWindowImageBoundsIgnoreFraming,
        )
    else:
        cg_image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectInfinite,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault,
        )

    if cg_image is None:
        raise RuntimeError("Failed to capture screen")

    # Convert CGImage to numpy array
    width = Quartz.CGImageGetWidth(cg_image)
    height = Quartz.CGImageGetHeight(cg_image)
    bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image)
    data_provider = Quartz.CGImageGetDataProvider(cg_image)
    data = Quartz.CGDataProviderCopyData(data_provider)

    img = np.frombuffer(data, dtype=np.uint8).reshape(height, bytes_per_row // 4, 4)
    img = img[:, :width, :]  # trim padding
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    if target_window:
        b = target_window["kCGWindowBounds"]
        origin = (int(b["X"]), int(b["Y"]))
    else:
        origin = (0, 0)

    return Screenshot(image=img, window_origin=origin)


def find_board(shot: Screenshot) -> tuple[int, int, int, int] | None:
    """Detect the green Word Hunt board in a screenshot.

    Returns (x, y, w, h) bounding rect in image coordinates, or None if not found.
    """
    hsv = cv2.cvtColor(shot.image, cv2.COLOR_BGR2HSV)

    # Tan/beige wood tile color range
    lower_tan = np.array([15, 30, 150])
    upper_tan = np.array([35, 180, 255])
    mask = cv2.inRange(hsv, lower_tan, upper_tan)

    # Clean up noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # Find roughly-square contours that look like individual cells
    img_area = shot.image.shape[0] * shot.image.shape[1]
    cells = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect = w / h if h > 0 else 0
        if 0.6 < aspect < 1.7 and 500 < area < img_area * 0.05:
            cells.append((x, y, w, h))

    # We expect ~16 cells in a grid pattern
    if len(cells) < 8:
        return None

    # Bounding box around all detected cells = the board
    xs = [x for x, y, w, h in cells]
    ys = [y for x, y, w, h in cells]
    x2s = [x + w for x, y, w, h in cells]
    y2s = [y + h for x, y, w, h in cells]

    bx, by = min(xs), min(ys)
    bw, bh = max(x2s) - bx, max(y2s) - by

    return (bx, by, bw, bh)


def extract_cells(
    shot: Screenshot, board_rect: tuple[int, int, int, int]
) -> list[np.ndarray]:
    """Extract 16 cell images from the detected board region.

    board_rect should be in image coordinates (from find_board).
    Returns 16 cell images in row-major order.
    """
    x, y, w, h = board_rect
    board_img = shot.image[y : y + h, x : x + w]

    cell_w = w / 4
    cell_h = h / 4

    # Inset each cell to avoid grid borders
    margin_x = cell_w * 0.1
    margin_y = cell_h * 0.1

    cells = []
    for row in range(4):
        for col in range(4):
            cx = int(col * cell_w + margin_x)
            cy = int(row * cell_h + margin_y)
            cw = int(cell_w - 2 * margin_x)
            ch = int(cell_h - 2 * margin_y)
            cell = board_img[cy : cy + ch, cx : cx + cw]
            cells.append(cell)

    return cells


def cell_centers(
    board_rect: tuple[int, int, int, int], shot: Screenshot
) -> list[tuple[int, int]]:
    """Compute screen pixel coordinates for the center of each cell.

    Converts from image-local board_rect to absolute screen coordinates.
    Returns 16 (x, y) tuples in row-major order.
    """
    ox, oy = shot.window_origin
    x, y, w, h = board_rect

    # The captured image may be at 2x (Retina) resolution while window_origin
    # is in logical screen coordinates. Compute the scale factor.
    img_h, img_w = shot.image.shape[:2]
    win_w = img_w  # default: assume 1x
    # Try to find the actual window size from the window list
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    for win in window_list:
        owner = win.get("kCGWindowOwnerName", "")
        name = win.get("kCGWindowName", "")
        if "iPhone Mirroring" in owner or "iPhone Mirroring" in name:
            win_w = int(win["kCGWindowBounds"]["Width"])
            break
    scale = img_w / win_w if win_w > 0 else 1.0

    sx, sy = x / scale + ox, y / scale + oy
    cell_w = w / scale / 4
    cell_h = h / scale / 4

    centers = []
    for row in range(4):
        for col in range(4):
            cx = int(sx + col * cell_w + cell_w / 2)
            cy = int(sy + row * cell_h + cell_h / 2)
            centers.append((cx, cy))
    return centers


def _get_retina_scale(shot: Screenshot) -> float:
    """Get the Retina scale factor for the iPhone Mirroring window."""
    img_h, img_w = shot.image.shape[:2]
    win_w = img_w
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    for win in window_list:
        owner = win.get("kCGWindowOwnerName", "")
        name = win.get("kCGWindowName", "")
        if "iPhone Mirroring" in owner or "iPhone Mirroring" in name:
            win_w = int(win["kCGWindowBounds"]["Width"])
            break
    return img_w / win_w if win_w > 0 else 1.0


def find_anagram_tiles(shot: Screenshot) -> list[tuple[int, int, int, int]] | None:
    """Detect the 6 anagram letter tiles (tan tiles in a horizontal row).

    Returns list of 6 (x, y, w, h) rects in image coordinates sorted left-to-right,
    or None if not found.
    """
    hsv = cv2.cvtColor(shot.image, cv2.COLOR_BGR2HSV)

    # Tan/beige wood tile color range (same as Word Hunt)
    lower_tan = np.array([15, 30, 150])
    upper_tan = np.array([35, 180, 255])
    mask = cv2.inRange(hsv, lower_tan, upper_tan)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    img_area = shot.image.shape[0] * shot.image.shape[1]
    tiles = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect = w / h if h > 0 else 0
        if 0.6 < aspect < 1.7 and 500 < area < img_area * 0.05:
            tiles.append((x, y, w, h))

    # Anagrams has 6 tiles in a row — filter to tiles at roughly the same y
    if len(tiles) < 6:
        return None

    # Sort by y to find the row of tiles (they should all be near the bottom)
    tiles.sort(key=lambda t: t[1])

    # Group tiles by similar y coordinate (within one tile height)
    if tiles:
        avg_h = sum(h for _, _, _, h in tiles) / len(tiles)
        rows: dict[int, list] = {}
        for t in tiles:
            placed = False
            for key in rows:
                if abs(t[1] - key) < avg_h * 0.5:
                    rows[key].append(t)
                    placed = True
                    break
            if not placed:
                rows[t[1]] = [t]

        # Find a row with exactly 6 tiles
        for key in sorted(rows.keys(), reverse=True):  # prefer bottom row
            if len(rows[key]) == 6:
                row_tiles = sorted(rows[key], key=lambda t: t[0])  # left to right
                return row_tiles

    return None


def extract_anagram_cells(
    shot: Screenshot, tiles: list[tuple[int, int, int, int]]
) -> list[np.ndarray]:
    """Extract cell images from detected anagram tiles."""
    cells = []
    for x, y, w, h in tiles:
        margin_x = int(w * 0.1)
        margin_y = int(h * 0.1)
        cell = shot.image[y + margin_y : y + h - margin_y, x + margin_x : x + w - margin_x]
        cells.append(cell)
    return cells


def anagram_tile_centers(
    tiles: list[tuple[int, int, int, int]], shot: Screenshot
) -> list[tuple[int, int]]:
    """Compute screen coordinates for the center of each anagram tile."""
    ox, oy = shot.window_origin
    scale = _get_retina_scale(shot)

    centers = []
    for x, y, w, h in tiles:
        cx = int(x / scale + w / scale / 2 + ox)
        cy = int(y / scale + h / scale / 2 + oy)
        centers.append((cx, cy))
    return centers


def find_enter_button(
    tiles: list[tuple[int, int, int, int]], shot: Screenshot
) -> tuple[int, int]:
    """Compute the ENTER button position relative to detected anagram tiles.

    The ENTER button sits directly above the row of letter tiles.
    Returns (x, y) screen coordinates of the button center.
    """
    ox, oy = shot.window_origin
    scale = _get_retina_scale(shot)

    # ENTER button is centered horizontally, one tile-height above the tiles
    tile_ys = [t[1] for t in tiles]
    tile_xs = [t[0] for t in tiles]
    tile_ws = [t[2] for t in tiles]
    tile_hs = [t[3] for t in tiles]

    avg_h = sum(tile_hs) / len(tile_hs)
    row_top = min(tile_ys)
    row_left = min(tile_xs)
    row_right = max(x + w for x, w in zip(tile_xs, tile_ws))

    # Center x of the tile row, roughly 2 tile heights above the top of tiles
    img_cx = (row_left + row_right) / 2
    img_cy = row_top - avg_h * 2.0

    cx = int(img_cx / scale + ox)
    cy = int(img_cy / scale + oy)
    return (cx, cy)
