"""Separate bundled, read-only resources from persistent user data."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_directory():
    if getattr(sys, 'frozen', False):
        local = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
        return local / 'CatAssistant' / 'data'
    return ROOT / 'data'


def launch_command():
    if getattr(sys, 'frozen', False):
        return '"' + str(Path(sys.executable).resolve()) + '"'
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    return '"' + str(pythonw) + '" "' + str(ROOT / 'app.py') + '"'
