import ctypes
import os
import sys
from pathlib import Path

MENU_KEYS = [r'Software\Classes\*\shell\AIHelp',
             r'Software\Classes\Directory\shell\AIHelp',
             r'Software\Classes\Directory\Background\shell\AIHelp']
SETTINGS_KEY = r'Software\Classes\Directory\Background\shell\AIHelpSettings'


def refresh_menu(nickname):
    if os.name != 'nt':
        return
    import winreg
    installed = False
    for path in MENU_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                for name in ('', 'MUIVerb'):
                    winreg.SetValueEx(key, name, 0, winreg.REG_SZ, '召唤' + nickname)
                installed = True
        except FileNotFoundError:
            pass
    if installed:
        app = Path(__file__).resolve().parent.parent / 'app.py'
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY) as key:
            for name in ('', 'MUIVerb'):
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, nickname + '的设置…')
            winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, str(pythonw))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY + r'\command') as key:
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, '"' + str(pythonw) + '" "' + str(app) + '" --settings')
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
