#!/usr/bin/env python3
"""CLI for the Word Hunt solver."""

import sys
import time

from solver import Board, load_trie, word_points


def parse_board(raw: str) -> list[list[str]]:
    """Parse board from space-separated rows, e.g. 'abcd efgh ijkl mnop'."""
    rows = raw.strip().lower().split()
    if len(rows) != 4 or any(len(r) != 4 for r in rows):
        print("Error: provide exactly 4 rows of 4 letters each.", file=sys.stderr)
        print('Usage: python main.py "abcd efgh ijkl mnop"', file=sys.stderr)
        sys.exit(1)
    return [list(row) for row in rows]


def display_results(results: list[tuple[str, int, list[tuple[int, int]]]]) -> None:
    total_points = sum(pts for _, pts, _ in results)
    print(f"\nFound {len(results)} words ({total_points} total points)\n")

    current_length = None
    for word, pts, path in results:
        if len(word) != current_length:
            current_length = len(word)
            print(f"--- {current_length} letters ({word_points(current_length)} pts each) ---")
        coords = " → ".join(f"({r},{c})" for r, c in path)
        print(f"  {word:<20s} {coords}")
    print()


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python main.py "abcd efgh ijkl mnop"', file=sys.stderr)
        sys.exit(1)

    grid = parse_board(sys.argv[1])

    print("Board:")
    for row in grid:
        print("  " + " ".join(row))

    print("\nLoading dictionary...")
    t0 = time.time()
    trie = load_trie()
    print(f"Dictionary loaded in {time.time() - t0:.2f}s")

    print("Solving...")
    t0 = time.time()
    board = Board(grid, trie)
    results = board.solve()
    print(f"Solved in {time.time() - t0:.2f}s")

    display_results(results)


if __name__ == "__main__":
    main()
