"""macOS native GUI for the Word Hunt Bot using AppKit (PyObjC)."""

import threading

import objc
from AppKit import (
    NSApplication,
    NSWindow,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSBackingStoreBuffered,
    NSButton,
    NSTextField,
    NSFont,
    NSColor,
    NSScrollView,
    NSTextView,
    NSBezelStylePush,
    NSMakeRect,
    NSApp,
    NSObject,
    NSApplicationActivationPolicyRegular,
    NSProgressIndicator,
    NSProgressIndicatorStyleBar,
)

from capture import capture_screen, find_board, extract_cells, cell_centers
from model import load_model, predict_board, MODEL_PATH
from solver import Board, load_trie
from automation import play_words


class AppDelegate(NSObject):
    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        return True


class WordHuntApp:
    def __init__(self):
        self.trie = None
        self.model = None
        self.board_rect = None
        self.centers = None
        self.results = None
        self.playing = False

        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        self.delegate = AppDelegate.alloc().init()
        self.app.setDelegate_(self.delegate)

        self._build_window()
        self._load_resources()

    def _make_label(self, text, x, y, w, h, size=13, bold=False, align=None):
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        label.setFont_(font)
        if align:
            label.setAlignment_(align)
        return label

    def _make_button(self, title, x, y, w, h, action):
        btn = NSButton.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
        btn.setTitle_(title)
        btn.setBezelStyle_(NSBezelStylePush)
        btn.setTarget_(self)
        btn.setAction_(action)
        return btn

    def _build_window(self):
        win_w, win_h = 460, 560
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(200, 200, win_w, win_h),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("Word Hunt Bot")
        content = self.window.contentView()

        # --- Board grid (4x4) ---
        board_y = win_h - 200
        self.board_labels = []
        for r in range(4):
            row_labels = []
            for c in range(4):
                x = 20 + c * 55
                y = board_y - r * 45
                lbl = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, 50, 40))
                lbl.setStringValue_("·")
                lbl.setBezeled_(False)
                lbl.setEditable_(False)
                lbl.setSelectable_(False)
                lbl.setAlignment_(1)  # center
                lbl.setFont_(NSFont.boldSystemFontOfSize_(22))
                lbl.setBackgroundColor_(NSColor.colorWithRed_green_blue_alpha_(0.18, 0.35, 0.15, 1.0))
                lbl.setTextColor_(NSColor.whiteColor())
                lbl.setDrawsBackground_(True)
                content.addSubview_(lbl)
                row_labels.append(lbl)
            self.board_labels.append(row_labels)

        # --- Buttons ---
        btn_x = 260
        self.capture_btn = self._make_button("Capture Board", btn_x, win_h - 70, 170, 32, b"onCapture:")
        content.addSubview_(self.capture_btn)

        self.play_btn = self._make_button("Play Words", btn_x, win_h - 110, 170, 32, b"onPlay:")
        self.play_btn.setEnabled_(False)
        content.addSubview_(self.play_btn)

        self.dry_run_btn = self._make_button("Dry Run", btn_x, win_h - 150, 170, 32, b"onDryRun:")
        self.dry_run_btn.setEnabled_(False)
        content.addSubview_(self.dry_run_btn)

        self.stop_btn = self._make_button("Stop", btn_x, win_h - 190, 170, 32, b"onStop:")
        self.stop_btn.setEnabled_(False)
        content.addSubview_(self.stop_btn)

        # --- Settings ---
        content.addSubview_(self._make_label("Delay (s):", btn_x, win_h - 230, 80, 20, size=11))
        self.delay_field = NSTextField.alloc().initWithFrame_(NSMakeRect(btn_x + 85, win_h - 230, 60, 22))
        self.delay_field.setStringValue_("0.3")
        self.delay_field.setFont_(NSFont.systemFontOfSize_(11))
        content.addSubview_(self.delay_field)

        content.addSubview_(self._make_label("Max words:", btn_x, win_h - 258, 80, 20, size=11))
        self.max_words_field = NSTextField.alloc().initWithFrame_(NSMakeRect(btn_x + 85, win_h - 258, 60, 22))
        self.max_words_field.setStringValue_("100")
        self.max_words_field.setFont_(NSFont.systemFontOfSize_(11))
        content.addSubview_(self.max_words_field)

        # --- Status ---
        self.status_label = self._make_label("Loading...", 20, win_h - 230, 220, 20, size=11)
        content.addSubview_(self.status_label)

        # --- Progress bar ---
        self.progress = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(20, win_h - 255, 220, 16))
        self.progress.setStyle_(NSProgressIndicatorStyleBar)
        self.progress.setMinValue_(0)
        self.progress.setMaxValue_(100)
        self.progress.setDoubleValue_(0)
        self.progress.setIndeterminate_(False)
        content.addSubview_(self.progress)

        # --- Word list (scrollable text view) ---
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 10, win_w - 40, win_h - 280))
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(1)  # NSBezelBorder

        self.text_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, win_w - 60, win_h - 280))
        self.text_view.setEditable_(False)
        self.text_view.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0.0))
        scroll.setDocumentView_(self.text_view)
        content.addSubview_(scroll)

    def _load_resources(self):
        def load():
            self._set_status("Loading dictionary...")
            self.trie = load_trie()
            if MODEL_PATH.exists():
                self._set_status("Loading model...")
                self.model = load_model()
                self._set_status("Ready")
            else:
                self._set_status("No model — run: python model.py")
        threading.Thread(target=load, daemon=True).start()

    def _set_status(self, text):
        self.status_label.performSelectorOnMainThread_withObject_waitUntilDone_(
            b"setStringValue:", text, False
        )

    def _update_board_display(self, grid):
        for r in range(4):
            for c in range(4):
                self.board_labels[r][c].setStringValue_(grid[r][c].upper())

    @objc.typedSelector(b"v@:@")
    def onCapture_(self, sender):
        if self.model is None:
            self._set_status("No model! Train first.")
            return

        self._set_status("Capturing...")

        def do_capture():
            shot = capture_screen()
            self.board_rect = find_board(shot)

            if self.board_rect is None:
                self._set_status("Board not found!")
                return

            cells = extract_cells(shot, self.board_rect)
            self.centers = cell_centers(self.board_rect, shot)

            grid = predict_board(self.model, cells)
            # Update UI on main thread
            self.window.contentView().performSelectorOnMainThread_withObject_waitUntilDone_(
                b"setNeedsDisplay:", True, False
            )
            self._update_board_display(grid)

            self._set_status("Solving...")
            board = Board(grid, self.trie)
            self.results = board.solve()

            # Build word list text
            total_pts = sum(pts for _, pts, _ in self.results)
            lines = [f"Found {len(self.results)} words ({total_pts} total pts)\n"]
            lines.append(f"{'Word':<20s} {'Pts':>5s}  {'Len':>3s}")
            lines.append("-" * 32)
            for word, pts, path in self.results:
                lines.append(f"{word:<20s} {pts:>5d}  {len(word):>3d}")

            text = "\n".join(lines)
            self.text_view.performSelectorOnMainThread_withObject_waitUntilDone_(
                b"setString:", text, False
            )

            self._set_status(f"Found {len(self.results)} words ({total_pts} pts)")
            self.play_btn.setEnabled_(True)
            self.dry_run_btn.setEnabled_(True)

        threading.Thread(target=do_capture, daemon=True).start()

    @objc.typedSelector(b"v@:@")
    def onPlay_(self, sender):
        if not self.results or not self.centers:
            return
        self._run_words(dry_run=False)

    @objc.typedSelector(b"v@:@")
    def onDryRun_(self, sender):
        if not self.results:
            return
        self._run_words(dry_run=True)

    @objc.typedSelector(b"v@:@")
    def onStop_(self, sender):
        self.playing = False

    def _run_words(self, dry_run):
        self.playing = True
        self.play_btn.setEnabled_(False)
        self.dry_run_btn.setEnabled_(False)
        self.capture_btn.setEnabled_(False)
        self.stop_btn.setEnabled_(True)

        try:
            delay = float(self.delay_field.stringValue())
        except ValueError:
            delay = 0.3
        try:
            max_words = int(self.max_words_field.stringValue())
        except ValueError:
            max_words = 100

        def run():
            if dry_run:
                words = self.results[:max_words]
                for i, (word, pts, path) in enumerate(words):
                    if not self.playing:
                        break
                    self._set_status(f"Dry run {i+1}/{len(words)}: {word} ({pts}pts)")
                    self._update_progress(i + 1, len(words))
            else:
                for progress in play_words(self.results, self.centers, delay, max_words):
                    if not self.playing:
                        break
                    i, total, word, pts = progress
                    self._set_status(f"Playing {i}/{total}: {word} ({pts}pts)")
                    self._update_progress(i, total)

            self.playing = False
            self.play_btn.setEnabled_(True)
            self.dry_run_btn.setEnabled_(True)
            self.capture_btn.setEnabled_(True)
            self.stop_btn.setEnabled_(False)
            self._set_status("Done!")

        threading.Thread(target=run, daemon=True).start()

    def _update_progress(self, current, total):
        self.progress.setMaxValue_(total)
        self.progress.setDoubleValue_(current)

    def run(self):
        self.window.makeKeyAndOrderFront_(None)
        self.app.activateIgnoringOtherApps_(True)
        self.app.run()


if __name__ == "__main__":
    app = WordHuntApp()
    app.run()
