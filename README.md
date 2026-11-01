# Typing Auto

Typing Auto is a transparent, local-only snippet typer for Windows, macOS, and Linux. It sends ordinary OS-level keyboard events one character at a time instead of using the clipboard. It is intended for personal productivity, UI testing, accessibility experiments, and repetitive text-entry workflows where the target application permits automation.

It deliberately does **not** hide its activity, bypass anti-cheat or monitoring systems, inject into target processes, install a service, create persistence, or claim to be undetectable. The application has a visible window, an emergency stop, and an explicit status line while it is typing.

## Features

- Local JSON snippet storage in `~/.typing-auto/snippets.json`.
- Per-snippet global hotkeys through `pynput`.
- Character-by-character OS keyboard events.
- Adjustable characters-per-minute timing.
- Optional bounded timing variation for UI and typing tests.
- Countdown before typing and `Esc`/Stop cancellation.
- No network code, telemetry, updater, background service, or scheduled task.
- Cross-platform Python implementation with documented OS permissions.

## Install from source

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.typing_auto
```

On macOS, grant Accessibility/Input Monitoring permission to the terminal or packaged app. On Linux, desktop-session and Wayland security policies may limit global input injection; X11 generally provides broader compatibility. On Windows, a target window running elevated may reject input from a non-elevated process.

## Hotkeys

Use `pynput` global-hotkey notation, for example `<ctrl>+<alt>+t`, `<shift>+<f8>`, or `<cmd>+<alt>+t` on macOS. The exact set depends on the platform and keyboard layout.

## Safety model

The tool only calls the public keyboard abstraction provided by `pynput`. It does not read target-window contents, inspect other processes, modify the registry, create a startup entry, or make network requests. Review `app/typing_auto.py` before running it. Use only where you have permission to automate the target application.

## Project layout

- `app/typing_auto.py` — desktop app and typing engine.
- `site/` — static product and installation documentation for Vercel.
- `scripts/` — local packaging and validation helpers.
- `tests/` — non-invasive unit tests.

## License

MIT. See [LICENSE](LICENSE).

## Deploy the documentation site

The `site/` directory is a plain static site. In Vercel, connect this repository and set the project Root Directory to `site`; no build command or environment variable is required. Every push to `main` can then publish the documentation automatically.
