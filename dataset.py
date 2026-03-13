"""Dataset creation helper — capture boards and label letters for CNN training."""

import string
import time
from pathlib import Path

import cv2

from capture import capture_screen, extract_cells, find_board

DATASET_DIR = Path(__file__).parent / "dataset"


def ensure_dirs():
    """Create dataset directories for each letter."""
    for letter in string.ascii_lowercase:
        (DATASET_DIR / letter).mkdir(parents=True, exist_ok=True)


def next_index(letter_dir: Path) -> int:
    """Get next available index for a letter directory."""
    existing = list(letter_dir.glob("*.png"))
    if not existing:
        return 0
    return max(int(p.stem) for p in existing) + 1


def label_board():
    """Capture the current screen, detect board, and interactively label cells."""
    print("Capturing screen...")
    shot = capture_screen()
    board_rect = find_board(shot)

    if board_rect is None:
        print("Could not detect board. Make sure Word Hunt is visible on screen.")
        return

    x, y, w, h = board_rect
    print(f"Board detected at ({x}, {y}) size {w}x{h}")

    cells = extract_cells(shot, board_rect)
    print(f"Extracted {len(cells)} cells")

    # Show the board region for reference
    board_img = shot.image[y : y + h, x : x + w]
    cv2.imshow("Board", board_img)
    cv2.waitKey(500)

    ensure_dirs()

    print("\nLabel each cell (a-z). Press ESC to skip, 'q' to quit.\n")

    for i, cell in enumerate(cells):
        row, col = divmod(i, 4)
        display = cv2.resize(cell, (200, 200), interpolation=cv2.INTER_NEAREST)
        cv2.imshow(f"Cell ({row},{col})", display)
        print(f"Cell ({row},{col}): ", end="", flush=True)

        key = cv2.waitKey(0) & 0xFF
        cv2.destroyWindow(f"Cell ({row},{col})")

        if key == 27:  # ESC
            print("skipped")
            continue
        if key == ord("q"):
            print("quit")
            break

        ch = chr(key).lower()
        if ch in string.ascii_lowercase:
            letter_dir = DATASET_DIR / ch
            idx = next_index(letter_dir)
            save_path = letter_dir / f"{idx:04d}.png"
            cv2.imwrite(str(save_path), cell)
            print(f"{ch} -> saved to {save_path}")
        else:
            print("invalid, skipped")

    cv2.destroyAllWindows()


def label_from_string(board_str: str):
    """Capture screen and save cells using a known board string.

    board_str: 16-character string of letters (row-major), e.g. 'abcdefghijklmnop'
    """
    board_str = board_str.lower().replace(" ", "")
    if len(board_str) != 16 or not board_str.isalpha():
        print("Error: provide exactly 16 letters.")
        return

    print("Capturing screen...")
    shot = capture_screen()
    board_rect = find_board(shot)

    if board_rect is None:
        print("Could not detect board.")
        return

    cells = extract_cells(shot, board_rect)
    ensure_dirs()

    saved = 0
    for i, (cell, ch) in enumerate(zip(cells, board_str)):
        letter_dir = DATASET_DIR / ch
        idx = next_index(letter_dir)
        save_path = letter_dir / f"{idx:04d}.png"
        cv2.imwrite(str(save_path), cell)
        saved += 1

    print(f"Saved {saved} labeled cell images.")


def show_stats():
    """Print dataset statistics."""
    total = 0
    for letter in string.ascii_lowercase:
        letter_dir = DATASET_DIR / letter
        if letter_dir.is_dir():
            count = len(list(letter_dir.glob("*.png")))
            if count > 0:
                print(f"  {letter}: {count}")
                total += count
    print(f"\nTotal: {total} samples")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            show_stats()
        elif cmd == "auto" and len(sys.argv) > 2:
            label_from_string(sys.argv[2])
        else:
            print("Usage:")
            print("  python dataset.py          # interactive labeling")
            print("  python dataset.py stats     # show dataset stats")
            print('  python dataset.py auto "abcdefghijklmnop"  # auto-label with known letters')
    else:
        label_board()
