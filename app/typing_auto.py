from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .core import Snippet, SnippetStore, TypingEngine

try:
    from pynput import keyboard, mouse
except ImportError:
    keyboard = None
    mouse = None


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Typing Auto")
        self.root.geometry("980x720")
        self.root.minsize(820, 620)
        self.store = SnippetStore()
        self.snippets = self.store.load()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.hotkey_listener = None
        self.pick_listener = None
        self.reveal_after_typing = False
        self.dark_mode = True
        self.status_var = tk.StringVar(value="Ready")
        self.theme_button_var = tk.StringVar(value="LIGHT MODE")
        self.cpm_var = tk.IntVar(value=360)
        self.jitter_var = tk.IntVar(value=8)
        self.countdown_var = tk.IntVar(value=3)
        self.always_top_var = tk.BooleanVar(value=False)
        self._build_ui()
        self._refresh_list()
        self._apply_theme()
        self._register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.stop())

    def _build_ui(self):
        self.outer = ttk.Frame(self.root, padding=22)
        self.outer.pack(fill="both", expand=True)

        header = ttk.Frame(self.outer)
        header.pack(fill="x", pady=(0, 18))
        brand = ttk.Frame(header)
        brand.pack(side="left")
        ttk.Label(brand, text="TA", style="Brand.TLabel").pack(side="left", padx=(0, 12))
        ttk.Label(brand, text="Typing Auto", style="Title.TLabel").pack(anchor="w")
        ttk.Label(brand, text="LOCAL TEXT / OS-LEVEL INPUT", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Button(header, textvariable=self.theme_button_var, command=self.toggle_theme, style="Quiet.TButton").pack(side="right", padx=(10, 0))
        ttk.Checkbutton(header, text="Always on top", variable=self.always_top_var, command=self._toggle_topmost).pack(side="right")

        intro = ttk.Frame(self.outer)
        intro.pack(fill="x", pady=(0, 16))
        ttk.Label(intro, text="Your reusable words, ready when you are.", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(intro, text="Choose a snippet, tune the pace, and send it to the field you control.", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self.outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Panel.TFrame", padding=14)
        left.pack(side="left", fill="y", padx=(0, 14))
        ttk.Label(left, text="SNIPPETS", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(left, text="Saved locally", style="Muted.TLabel").pack(anchor="w", pady=(3, 10))
        self.listbox = tk.Listbox(left, width=28, height=15, exportselection=False, relief="flat", borderwidth=0, highlightthickness=0, activestyle="none")
        self.listbox.pack(fill="y", expand=True, pady=(0, 12))
        self.listbox.bind("<<ListboxSelect>>", self._select)
        buttons = ttk.Frame(left)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="＋ Add", command=self.add).pack(side="left", fill="x", expand=True)
        ttk.Button(buttons, text="Delete", command=self.delete, style="Quiet.TButton").pack(side="left", fill="x", expand=True, padx=(7, 0))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        editor = ttk.Frame(right, style="Panel.TFrame", padding=18)
        editor.pack(fill="both", expand=True)
        ttk.Label(editor, text="SNIPPET EDITOR", style="Eyebrow.TLabel").pack(anchor="w")
        self.name = ttk.Entry(editor, font=("Segoe UI", 15))
        self.name.pack(fill="x", pady=(8, 12))
        ttk.Label(editor, text="Text to type", style="Muted.TLabel").pack(anchor="w")
        self.text = tk.Text(editor, height=9, wrap="word", undo=True, relief="flat", borderwidth=0, padx=12, pady=12, font=("Segoe UI", 12))
        self.text.pack(fill="both", expand=True, pady=(5, 12))
        hotkey_row = ttk.Frame(editor)
        hotkey_row.pack(fill="x")
        ttk.Label(hotkey_row, text="Global hotkey", style="Muted.TLabel").pack(side="left")
        self.hotkey = ttk.Entry(hotkey_row, width=25)
        self.hotkey.pack(side="left", padx=(10, 0))
        ttk.Label(hotkey_row, text="e.g. <ctrl>+<alt>+t", style="Muted.TLabel").pack(side="left", padx=(10, 0))
        actions = ttk.Frame(editor)
        actions.pack(fill="x", pady=(18, 0))
        ttk.Button(actions, text="Pick target and type", command=self.pick_target, style="Accent.TButton").pack(side="left")
        ttk.Button(actions, text="Type selected", command=self.start_selected).pack(side="left", padx=8)
        ttk.Button(actions, text="Save snippet", command=self.save_current, style="Quiet.TButton").pack(side="right")

        test = ttk.Frame(self.outer, style="Panel.TFrame", padding=14)
        test.pack(fill="x", pady=(14, 0))
        test_header = ttk.Frame(test)
        test_header.pack(fill="x")
        ttk.Label(test_header, text="LOCAL TEST PAD", style="Eyebrow.TLabel").pack(side="left")
        ttk.Label(test_header, text="No other app receives input", style="Muted.TLabel").pack(side="right")
        self.test_pad = tk.Text(test, height=3, wrap="word", relief="flat", borderwidth=0, padx=10, pady=8, font=("Segoe UI", 11))
        self.test_pad.pack(fill="x", pady=(8, 7))
        ttk.Button(test, text="Type into test pad", command=self.start_test_pad).pack(anchor="e")

        controls = ttk.Frame(self.outer, style="Panel.TFrame", padding=14)
        controls.pack(fill="x", pady=(14, 0))
        controls_header = ttk.Frame(controls)
        controls_header.pack(fill="x")
        ttk.Label(controls_header, text="TYPING PROFILE", style="Eyebrow.TLabel").pack(side="left")
        ttk.Label(controls_header, textvariable=self.status_var, style="Status.TLabel").pack(side="right")
        self._scale(controls, "Characters per minute", self.cpm_var, 30, 1200)
        self._scale(controls, "Timing variation", self.jitter_var, 0, 30)
        self._scale(controls, "Countdown", self.countdown_var, 0, 10)
        ttk.Button(controls, text="STOP / ESC", command=self.stop, style="Danger.TButton").pack(anchor="w", pady=(8, 0))

    def _scale(self, parent, label, variable, low, high):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(7, 0))
        ttk.Label(row, text=label, width=24, style="Muted.TLabel").pack(side="left")
        ttk.Scale(row, from_=low, to=high, variable=variable, orient="horizontal").pack(side="left", fill="x", expand=True)
        ttk.Label(row, textvariable=variable, width=6, style="Value.TLabel").pack(side="right", padx=(10, 0))

    def _apply_theme(self):
        colors = {
            "bg": "#101318" if self.dark_mode else "#f4f6f8",
            "panel": "#191e26" if self.dark_mode else "#ffffff",
            "field": "#252c37" if self.dark_mode else "#eef1f4",
            "text": "#f6f7f9" if self.dark_mode else "#17202a",
            "muted": "#98a4b3" if self.dark_mode else "#657080",
            "accent": "#c9f45b",
            "accent_text": "#101318",
            "blue": "#6ca9ff",
            "danger": "#ff7a73",
            "select": "#314152" if self.dark_mode else "#dce9f7",
        }
        self.root.configure(background=colors["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=colors["bg"])
        style.configure("Panel.TFrame", background=colors["panel"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        style.configure("Brand.TLabel", background=colors["accent"], foreground=colors["accent_text"], font=("Segoe UI", 15, "bold"), padding=(8, 5))
        style.configure("Title.TLabel", background=colors["bg"], foreground=colors["text"], font=("Segoe UI", 19, "bold"))
        style.configure("Heading.TLabel", background=colors["bg"], foreground=colors["text"], font=("Segoe UI", 25, "bold"))
        style.configure("Eyebrow.TLabel", background=colors["panel"], foreground=colors["blue"], font=("Segoe UI", 9, "bold"))
        style.configure("Muted.TLabel", background=colors["panel"], foreground=colors["muted"], font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=colors["panel"], foreground=colors["accent"], font=("Segoe UI", 10, "bold"))
        style.configure("Value.TLabel", background=colors["panel"], foreground=colors["text"], font=("Segoe UI", 10, "bold"))
        style.configure("TButton", background=colors["field"], foreground=colors["text"], borderwidth=0, padding=(12, 8), font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", colors["select"])])
        style.configure("Accent.TButton", background=colors["accent"], foreground=colors["accent_text"])
        style.map("Accent.TButton", background=[("active", "#e1ff83")])
        style.configure("Quiet.TButton", background=colors["field"], foreground=colors["muted"])
        style.configure("Danger.TButton", background=colors["danger"], foreground="#201314")
        style.configure("TCheckbutton", background=colors["bg"], foreground=colors["muted"])
        style.configure("TEntry", fieldbackground=colors["field"], foreground=colors["text"], insertcolor=colors["text"], borderwidth=0, padding=9)
        style.configure("Horizontal.TScale", background=colors["panel"], troughcolor=colors["field"], sliderlength=18)
        self.listbox.configure(background=colors["field"], foreground=colors["text"], selectbackground=colors["accent"], selectforeground=colors["accent_text"])
        for widget in (self.text, self.test_pad):
            widget.configure(background=colors["field"], foreground=colors["text"], insertbackground=colors["text"], selectbackground=colors["blue"], selectforeground="#ffffff")
        self.theme_button_var.set("DARK MODE" if not self.dark_mode else "LIGHT MODE")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _toggle_topmost(self):
        self.root.attributes("-topmost", bool(self.always_top_var.get()))

    def _refresh_list(self, select=0):
        self.listbox.delete(0, tk.END)
        for snippet in self.snippets:
            self.listbox.insert(tk.END, snippet.name)
        if self.snippets:
            select = min(max(0, select), len(self.snippets) - 1)
            self.listbox.selection_set(select)
            self.listbox.event_generate("<<ListboxSelect>>")

    def _select(self, _event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        item = self.snippets[selection[0]]
        self.name.delete(0, tk.END)
        self.name.insert(0, item.name)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", item.text)
        self.hotkey.delete(0, tk.END)
        self.hotkey.insert(0, item.hotkey)

    def add(self):
        self.snippets.append(Snippet("New snippet", "", ""))
        self.store.save(self.snippets)
        self._refresh_list(len(self.snippets) - 1)

    def delete(self):
        selection = self.listbox.curselection()
        if selection and messagebox.askyesno("Delete snippet", "Delete the selected snippet?"):
            del self.snippets[selection[0]]
            self.store.save(self.snippets)
            self._refresh_list(max(0, selection[0] - 1))
            self._register_hotkeys()

    def save_current(self):
        selection = self.listbox.curselection()
        if not selection:
            self.add()
            selection = self.listbox.curselection()
        i = selection[0]
        hotkey = self.hotkey.get().strip()
        self.snippets[i] = Snippet(self.name.get().strip() or "Unnamed", self.text.get("1.0", "end-1c"), hotkey)
        self.store.save(self.snippets)
        self._refresh_list(i)
        self._register_hotkeys()
        self.status_var.set("Saved")

    def _selected_text(self) -> str | None:
        selection = self.listbox.curselection()
        return self.snippets[selection[0]].text if selection else None

    def start_selected(self):
        text = self._selected_text()
        if text is not None:
            self._start(text)

    def start_test_pad(self):
        text = self._selected_text()
        if text is None:
            return
        self.test_pad.focus_set()
        self._start(text)

    def _start(self, text: str):
        self.stop_event.set()
        self.stop_event = threading.Event()
        self.reveal_after_typing = False
        profile = (int(self.cpm_var.get()), int(self.jitter_var.get()), int(self.countdown_var.get()))
        self.worker = threading.Thread(target=self._run, args=(text, *profile, self.stop_event), daemon=True)
        self.worker.start()

    def _run(self, text, cpm, jitter, countdown, stop_event):
        try:
            TypingEngine(stop_event, lambda s: self.root.after(0, self.status_var.set, s)).type_text(text, cpm, jitter, countdown)
            if self.reveal_after_typing:
                self.root.after(0, self.root.deiconify)
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("Typing Auto", str(exc)))
            self.root.after(0, self.status_var.set, "Error")

    def pick_target(self):
        text = self._selected_text()
        if not text or mouse is None:
            self.status_var.set("Install pynput to use target picking")
            return
        self.stop()
        self.status_var.set("Click the target field — Esc cancels")
        self.reveal_after_typing = True
        self.pending_target_text = text
        self.pending_profile = (int(self.cpm_var.get()), int(self.jitter_var.get()), int(self.countdown_var.get()))
        self.root.withdraw()
        self.pick_listener = mouse.Listener(on_click=self._target_click)
        self.pick_listener.start()

    def _target_click(self, _x, _y, _button, pressed):
        if not pressed:
            return
        if self.pick_listener:
            self.pick_listener.stop()
            self.pick_listener = None
        text = self.pending_target_text
        cpm, jitter, countdown = self.pending_profile
        self.worker = threading.Thread(target=self._run_profile, args=(text, cpm, jitter, countdown, self.stop_event), daemon=True)
        self.worker.start()
        return False

    def _run_profile(self, text, cpm, jitter, countdown, stop_event):
        try:
            TypingEngine(stop_event, lambda s: self.root.after(0, self.status_var.set, s)).type_text(text, cpm, jitter, countdown)
        finally:
            if self.reveal_after_typing:
                self.root.after(0, self.root.deiconify)

    def _valid_hotkey(self, value: str) -> bool:
        if not value or keyboard is None:
            return bool(not value)
        try:
            keyboard.HotKey.parse(value)
            return True
        except (ValueError, TypeError):
            return False

    def _register_hotkeys(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        if keyboard is None:
            return
        invalid = []
        mapping = {}
        for snippet in self.snippets:
            if not snippet.hotkey:
                continue
            if not self._valid_hotkey(snippet.hotkey):
                invalid.append(snippet.name)
                continue
            mapping[snippet.hotkey] = lambda s=snippet: self.root.after(0, self._start, s.text)
        if invalid:
            self.status_var.set("Invalid hotkey skipped: " + ", ".join(invalid[:2]))
        if mapping:
            try:
                self.hotkey_listener = keyboard.GlobalHotKeys(mapping)
                self.hotkey_listener.start()
            except (ValueError, TypeError) as exc:
                self.status_var.set(f"Hotkeys unavailable: {exc}")

    def stop(self):
        self.stop_event.set()
        if self.pick_listener:
            self.pick_listener.stop()
            self.pick_listener = None
            self.root.deiconify()
        self.reveal_after_typing = False
        self.status_var.set("Stopped")

    def close(self):
        self.stop()
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
