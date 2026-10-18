import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path
from ai_help.runtime import launch_command

MENU_KEYS = [r'Software\Classes\*\shell\AIHelp',
             r'Software\Classes\Directory\shell\AIHelp',
             r'Software\Classes\Directory\Background\shell\AIHelp']
SETTINGS_KEY = r'Software\Classes\Directory\Background\shell\AIHelpSettings'


ICON = Path(__file__).resolve().parent.parent / 'assets' / 'cat.ico'


def ime_composing(widget):
    """Do not treat Enter used to confirm an IME composition as Send."""
    if os.name != 'nt':
        return False
    imm = ctypes.WinDLL('imm32')
    imm.ImmGetContext.argtypes = [wintypes.HWND]
    imm.ImmGetContext.restype = wintypes.HANDLE
    imm.ImmGetCompositionStringW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                            ctypes.c_void_p, wintypes.DWORD]
    imm.ImmGetCompositionStringW.restype = ctypes.c_long
    imm.ImmReleaseContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
    imm.ImmReleaseContext.restype = wintypes.BOOL
    hwnd = widget.winfo_id()
    context = imm.ImmGetContext(hwnd)
    if not context:
        return False
    try:
        return imm.ImmGetCompositionStringW(context, 8, None, 0) > 0  # GCS_COMPSTR
    finally:
        imm.ImmReleaseContext(hwnd, context)


def apply_icon(window):
    if ICON.is_file():
        window.iconbitmap(str(ICON))


def menu_icon():
    return str(ICON if ICON.is_file() else Path(sys.executable) if getattr(sys, 'frozen', False) else Path(sys.executable).with_name('pythonw.exe'))


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
                winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, menu_icon())
                installed = True
        except FileNotFoundError:
            pass
    if installed:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY) as key:
            for name in ('', 'MUIVerb'):
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, nickname + '的设置…')
            winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, menu_icon())
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY + r'\command') as key:
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, launch_command() + ' --settings')
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
