import sys
import os
import json
import threading
import time
from pathlib import Path

# Support PySide6 or PyQt6
try:
    from PySide6.QtCore import Qt, Signal, QObject
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
    from PySide6.QtGui import QColor
except ImportError:
    from PyQt6.QtCore import Qt, pyqtSignal as Signal, QObject
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
    from PyQt6.QtGui import QColor

import websockets
import asyncio


class WebSocketWorker(QObject):
    """Listens to the local daemon WebSocket and emits signals on new text."""
    text_received = Signal(str)
    status_changed = Signal(str)

    def __init__(self, uri="ws://127.0.0.1:8765"):
        super().__init__()
        self.uri = uri
        self.is_running = True

    def start(self):
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        asyncio.run(self._listen())

    async def _listen(self):
        while self.is_running:
            try:
                self.status_changed.emit("Connecting to local engine...")
                async with websockets.connect(self.uri) as ws:
                    self.status_changed.emit("Listening")
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            if data.get("type") == "transcript" and data.get("text"):
                                self.text_received.emit(data["text"])
                        except Exception:
                            self.text_received.emit(str(message))
            except Exception:
                self.status_changed.emit("Engine Offline (ws://127.0.0.1:8765)")
                await asyncio.sleep(3)


class CaptionOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_position = None
        self.init_ui()
        self.load_stylesheet()
        self.init_network()

    def init_ui(self):
        # Frameless, transparent, always-on-top window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Card container
        self.card = QWidget(self)
        self.card.setObjectName("OverlayCard")

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)

        # Labels
        self.caption_label = QLabel("Listening for audio...", self.card)
        self.caption_label.setObjectName("CaptionLabel")
        self.caption_label.setWordWrap(True)
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Initializing...", self.card)
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Layouts
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 12, 16, 8)
        card_layout.addWidget(self.caption_label)
        card_layout.addWidget(self.status_label)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self.card)

        # Geometry: centered near bottom of screen
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.55)
        height = 120
        x = int((screen.width() - width) / 2)
        y = int(screen.height() - height - 80)
        self.setGeometry(x, y, width, height)

    def load_stylesheet(self):
        qss_path = Path(__file__).parent / "style.qss"
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def init_network(self):
        self.worker = WebSocketWorker()
        self.worker.text_received.connect(self.update_caption)
        self.worker.status_changed.connect(self.update_status)
        self.worker.start()

    def update_caption(self, text: str):
        self.caption_label.setText(text)

    def update_status(self, status: str):
        self.status_label.setText(status)

    # Click-and-drag window movement
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None


def main():
    app = QApplication(sys.argv)
    overlay = CaptionOverlay()
    overlay.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()