"""Word Hunt solver — Trie + DFS on a 4x4 board."""

from pathlib import Path

DICTIONARY_PATH = Path(__file__).parent / "dictionary.txt"

POINTS = {3: 100, 4: 400, 5: 800, 6: 1400, 7: 1800, 8: 2200}


def word_points(length: int) -> int:
    if length in POINTS:
        return POINTS[length]
    if length > 8:
        return POINTS[8] + (length - 8) * 400
    return 0


class TrieNode:
    __slots__ = ("children", "is_word")

    def __init__(self):
        self.children: dict[str, "TrieNode"] = {}
        self.is_word = False


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_word = True

    def search(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        return self._walk(prefix) is not None

    def _walk(self, s: str) -> TrieNode | None:
        node = self.root
        for ch in s:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node


def load_trie(path: Path = DICTIONARY_PATH) -> Trie:
    trie = Trie()
    with open(path) as f:
        for line in f:
            word = line.strip().lower()
            if word:
                trie.insert(word)
    return trie


# 8-directional neighbor offsets
_DIRS = [(-1, -1), (-1, 0), (-1, 1),
         (0, -1),           (0, 1),
         (1, -1),  (1, 0),  (1, 1)]


class Board:
    def __init__(self, grid: list[list[str]], trie: Trie):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])
        self.trie = trie

    def solve(self) -> list[tuple[str, int, list[tuple[int, int]]]]:
        """Return list of (word, points, path) sorted by points descending."""
        results: dict[str, list[tuple[int, int]]] = {}

        for r in range(self.rows):
            for c in range(self.cols):
                self._dfs(r, c, self.trie.root, [], results)

        scored = []
        for word, path in results.items():
            pts = word_points(len(word))
            scored.append((word, pts, path))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored

    def _dfs(
        self,
        r: int,
        c: int,
        node: TrieNode,
        path: list[tuple[int, int]],
        results: dict[str, list[tuple[int, int]]],
    ) -> None:
        ch = self.grid[r][c]
        if ch not in node.children:
            return

        next_node = node.children[ch]
        path.append((r, c))

        if next_node.is_word and len(path) >= 3:
            word = "".join(self.grid[pr][pc] for pr, pc in path)
            if word not in results or len(path) > len(results[word]):
                results[word] = list(path)

        for dr, dc in _DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols and (nr, nc) not in path:
                self._dfs(nr, nc, next_node, path, results)

        path.pop()


class AnagramSolver:
    """Find all valid words from a set of letters (each used at most once)."""

    def __init__(self, letters: list[str], trie: Trie):
        self.letters = [ch.lower() for ch in letters]
        self.trie = trie

    def solve(self) -> list[tuple[str, int, list[int]]]:
        """Return list of (word, points, letter_indices) sorted by length desc."""
        results: dict[str, list[int]] = {}
        self._dfs(self.trie.root, [], [False] * len(self.letters), results)

        scored = []
        for word, indices in results.items():
            pts = word_points(len(word))
            scored.append((word, pts, indices))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return scored

    def _dfs(
        self,
        node: TrieNode,
        indices: list[int],
        used: list[bool],
        results: dict[str, list[int]],
    ) -> None:
        if node.is_word and len(indices) >= 3:
            word = "".join(self.letters[i] for i in indices)
            if word not in results or len(indices) > len(results[word]):
                results[word] = list(indices)

        for i, ch in enumerate(self.letters):
            if used[i]:
                continue
            if ch not in node.children:
                continue
            used[i] = True
            indices.append(i)
            self._dfs(node.children[ch], indices, used, results)
            indices.pop()
            used[i] = False
