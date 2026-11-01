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
        self.root.geometry("860x650")
        self.root.minsize(740, 540)
        self.store = SnippetStore()
        self.snippets = self.store.load()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.hotkey_listener = None
        self.pick_listener = None
        self.reveal_after_typing = False
        self.status_var = tk.StringVar(value="Ready")
        self.cpm_var = tk.IntVar(value=360)
        self.jitter_var = tk.IntVar(value=8)
        self.countdown_var = tk.IntVar(value=3)
        self.always_top_var = tk.BooleanVar(value=False)
        self._build_ui()
        self._refresh_list()
        self._register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self.stop())

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="Typing Auto", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Label(header, text="LOCAL / VISIBLE / REVERSIBLE", foreground="#c75532").pack(side="right", pady=8)
        ttk.Checkbutton(header, text="Always on top", variable=self.always_top_var, command=self._toggle_topmost).pack(side="right", padx=16)
        ttk.Label(outer, text="Pick a snippet, choose a pace, then click the field where it should go.").pack(anchor="w", pady=(0, 12))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(left, text="Snippets").pack(anchor="w")
        self.listbox = tk.Listbox(left, width=28, height=14, exportselection=False)
        self.listbox.pack(fill="y", expand=True, pady=6)
        self.listbox.bind("<<ListboxSelect>>", self._select)
        buttons = ttk.Frame(left)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Add", command=self.add).pack(side="left", fill="x", expand=True)
        ttk.Button(buttons, text="Delete", command=self.delete).pack(side="left", fill="x", expand=True, padx=(6, 0))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Name").pack(anchor="w")
        self.name = ttk.Entry(right)
        self.name.pack(fill="x", pady=(2, 8))
        ttk.Label(right, text="Text").pack(anchor="w")
        self.text = tk.Text(right, height=9, wrap="word", undo=True)
        self.text.pack(fill="both", expand=True, pady=(2, 8))
        row = ttk.Frame(right)
        row.pack(fill="x")
        ttk.Label(row, text="Hotkey").pack(side="left")
        self.hotkey = ttk.Entry(row, width=24)
        self.hotkey.pack(side="left", padx=(6, 14))
        ttk.Label(row, text="Example: <ctrl>+<alt>+t").pack(side="left")
        ttk.Button(right, text="Save snippet", command=self.save_current).pack(anchor="e", pady=8)

        test = ttk.LabelFrame(outer, text="Local test pad", padding=8)
        test.pack(fill="x", pady=(12, 0))
        ttk.Label(test, text="Use this box to verify timing and line breaks without sending input to another app.").pack(anchor="w")
        self.test_pad = tk.Text(test, height=3, wrap="word")
        self.test_pad.pack(fill="x", pady=(6, 0))
        ttk.Button(test, text="Type into test pad", command=self.start_test_pad).pack(anchor="e", pady=(6, 0))

        controls = ttk.LabelFrame(outer, text="Typing profile", padding=10)
        controls.pack(fill="x", pady=(12, 0))
        self._scale(controls, "Characters per minute", self.cpm_var, 30, 1200)
        self._scale(controls, "Timing variation (%)", self.jitter_var, 0, 30)
        self._scale(controls, "Countdown (seconds)", self.countdown_var, 0, 10)
        actions = ttk.Frame(controls)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Pick target and type", command=self.pick_target).pack(side="left")
        ttk.Button(actions, text="Type selected", command=self.start_selected).pack(side="left", padx=6)
        ttk.Button(actions, text="STOP", command=self.stop).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var).pack(side="left", padx=10)
        ttk.Label(outer, text="Esc stops typing. Picking a target hides this window, waits for one click, then types visibly into that focused field.", foreground="#555").pack(anchor="w", pady=(10, 0))

    def _scale(self, parent, label, variable, low, high):
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Label(row, text=label, width=24).pack(side="left")
        ttk.Scale(row, from_=low, to=high, variable=variable, orient="horizontal").pack(side="left", fill="x", expand=True)
        ttk.Label(row, textvariable=variable, width=6).pack(side="right")

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
        self.name.delete(0, tk.END); self.name.insert(0, item.name)
        self.text.delete("1.0", tk.END); self.text.insert("1.0", item.text)
        self.hotkey.delete(0, tk.END); self.hotkey.insert(0, item.hotkey)

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
            self.add(); selection = self.listbox.curselection()
        i = selection[0]
        self.snippets[i] = Snippet(self.name.get().strip() or "Unnamed", self.text.get("1.0", "end-1c"), self.hotkey.get().strip())
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
        TypingEngine(stop_event, lambda s: self.root.after(0, self.status_var.set, s)).type_text(text, cpm, jitter, countdown)
        if self.reveal_after_typing:
            self.root.after(0, self.root.deiconify)

    def _register_hotkeys(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        if keyboard is None:
            return
        mapping = {x.hotkey: (lambda s=x: self.root.after(0, self._start, s.text)) for x in self.snippets if x.hotkey}
        if mapping:
            self.hotkey_listener = keyboard.GlobalHotKeys(mapping)
            self.hotkey_listener.start()

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
