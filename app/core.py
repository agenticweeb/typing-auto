from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from pynput import keyboard
except ImportError:  # pragma: no cover - handled at runtime by the UI
    keyboard = None

APP_DIR = Path.home() / ".typing-auto"
SNIPPETS_FILE = APP_DIR / "snippets.json"


@dataclass
class Snippet:
    name: str
    text: str
    hotkey: str = ""


class SnippetStore:
    def __init__(self, path: Path = SNIPPETS_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[Snippet]:
        if not self.path.exists():
            return [Snippet("Example", "Replace this with your own text.", "<ctrl>+<alt>+t")]
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [Snippet(str(x["name"]), str(x["text"]), str(x.get("hotkey", ""))) for x in raw]
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def save(self, snippets: list[Snippet]) -> None:
        self.path.write_text(json.dumps([asdict(x) for x in snippets], ensure_ascii=False, indent=2), encoding="utf-8")


class TypingEngine:
    def __init__(self, stop_event: threading.Event, status):
        self.stop_event = stop_event
        self.status = status

    def type_text(self, text: str, cpm: int, jitter: int, countdown: int) -> None:
        if keyboard is None:
            raise RuntimeError("pynput is not installed. Run: python -m pip install -r requirements.txt")
        controller = keyboard.Controller()
        for remaining in range(countdown, 0, -1):
            if self.stop_event.wait(1):
                self.status("Stopped")
                return
            self.status(f"Starting in {remaining}…")
        delay = 60.0 / max(1, cpm)
        self.status("Typing — press Stop or Esc to interrupt")
        for char in text:
            if self.stop_event.is_set():
                self.status("Stopped")
                return
            if char == "\n":
                controller.press(keyboard.Key.enter)
            elif char == "\t":
                controller.press(keyboard.Key.tab)
            else:
                controller.type(char)
            variation = random.uniform(-jitter, jitter) / 100.0 if jitter else 0
            time.sleep(max(0.001, delay * (1 + variation)))
        self.status("Ready")
