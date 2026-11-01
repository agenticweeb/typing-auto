#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TypingAuto run_app.py
printf 'built: dist/TypingAuto*\n'
