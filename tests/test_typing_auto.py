import json
from pathlib import Path

from app.core import Snippet, SnippetStore


def test_store_round_trip(tmp_path: Path):
    path = tmp_path / "snippets.json"
    store = SnippetStore(path)
    expected = [Snippet("Greeting", "Hello\nworld", "<ctrl>+g")]
    store.save(expected)
    assert json.loads(path.read_text()) == [{"name": "Greeting", "text": "Hello\nworld", "hotkey": "<ctrl>+g"}]
    loaded = store.load()
    assert loaded == expected


def test_missing_store_is_safe(tmp_path: Path):
    loaded = SnippetStore(tmp_path / "missing.json").load()
    assert loaded and loaded[0].name == "Example"
