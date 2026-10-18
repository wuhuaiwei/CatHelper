"""Rounded window outlines and lightweight custom window controls."""
import ctypes
import os
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk

from ai_help.settings_style import BG, MUTED


class SettingsChrome(tk.Canvas):
    def __init__(self, window):
        super().__init__(window, bg=BG, highlightthickness=0)
        self.window = window
        self.drag_origin = self.resize_origin = None
        window.overrideredirect(True)
        self.pack(fill='both', expand=True)
        self.body = tk.Frame(self, bg=BG, padx=14, pady=10)
        self.body_id = self.create_window(10, 10, anchor='nw', window=self.body)
        self.bind('<Configure>', self.layout)
        self.titlebar = tk.Frame(self.body, bg=BG)
        self.titlebar.pack(fill='x', pady=(0, 8))
        caption = tk.Label(self.titlebar, text='伙伴设置', bg=BG, fg=MUTED,
                           font=('Microsoft YaHei UI', 9))
        caption.pack(side='left')
        self.close_button = ttk.Button(self.titlebar, text='×', width=2, padding=0,
                                       style='Companion.Soft.TButton', cursor='hand2',
                                       command=window.destroy)
        self.close_button.pack(side='right')
        self.make_draggable(self.titlebar)
        self.make_draggable(caption)
        window.bind('<Alt-F4>', lambda event: window.destroy(), add='+')
        self.grip = tk.Canvas(self, width=16, height=16, bg=BG,
                              highlightthickness=0, cursor='size_nw_se')
        for offset in (0, 5):
            self.grip.create_line(5+offset, 12, 12, 5+offset, fill='#C4B0DC', width=2)
        self.grip.bind('<ButtonPress-1>', self.begin_resize)
        self.grip.bind('<B1-Motion>', self.resize)
        self.grip.bind('<ButtonRelease-1>', lambda event: setattr(self, 'resize_origin', None))
        self.grip_id = self.create_window(0, 0, anchor='se', window=self.grip)

    def layout(self, event):
        w, h, r = event.width, event.height, 24
        self.delete('outline')
        points = [r, 1, w-r, 1, w-1, 1, w-1, r, w-1, h-r,
                  w-1, h-1, w-r, h-1, r, h-1, 1, h-1, 1, h-r, 1, r, 1, 1]
        self.create_polygon(points, smooth=True, splinesteps=32, fill=BG,
                            outline='#DED0ED', tags='outline')
        self.tag_lower('outline')
        self.itemconfigure(self.body_id, width=max(1, w-20), height=max(1, h-20))
        self.coords(self.grip_id, w-10, h-10)
        self.tag_raise(self.grip_id)

    def make_draggable(self, widget):
        widget.bind('<ButtonPress-1>', self.begin_drag, add='+')
        widget.bind('<B1-Motion>', self.drag, add='+')
        widget.bind('<ButtonRelease-1>', lambda event: setattr(self, 'drag_origin', None), add='+')

    def begin_drag(self, event):
        self.drag_origin = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())

    def drag(self, event):
        if self.drag_origin:
            x, y, left, top = self.drag_origin
            self.window.geometry(f'{left + event.x_root - x:+d}{top + event.y_root - y:+d}')

    def begin_resize(self, event):
        self.resize_origin = (event.x_root, event.y_root,
                              self.window.winfo_width(), self.window.winfo_height())

    def resize(self, event):
        if self.resize_origin:
            x, y, width, height = self.resize_origin
            minimum = self.window.minsize()
            self.window.geometry(f'{max(minimum[0], width + event.x_root - x)}x'
                                 f'{max(minimum[1], height + event.y_root - y)}')


class RoundedWindow:
    def __init__(self, window):
        self.window = window
        self.job = None
        self.last_region = None
        if os.name != 'nt':
            return
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.gdi = ctypes.WinDLL('gdi32', use_last_error=True)
        self.dwm = ctypes.WinDLL('dwmapi', use_last_error=True)
        self.user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user.GetAncestor.restype = wintypes.HWND
        self.user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.GetWindowRect.restype = wintypes.BOOL
        self.user.IsZoomed.argtypes = [wintypes.HWND]
        self.user.IsZoomed.restype = wintypes.BOOL
        self.user.GetDpiForWindow.argtypes = [wintypes.HWND]
        self.user.GetDpiForWindow.restype = wintypes.UINT
        self.user.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
        self.user.SetWindowRgn.restype = ctypes.c_int
        self.gdi.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
        self.gdi.CreateRoundRectRgn.restype = wintypes.HANDLE
        self.gdi.DeleteObject.argtypes = [wintypes.HANDLE]
        self.gdi.DeleteObject.restype = wintypes.BOOL
        self.dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                  ctypes.c_void_p, wintypes.DWORD]
        self.dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        window.bind('<Map>', self.schedule, add='+')
        window.bind('<Configure>', self.schedule, add='+')
        window.bind('<Destroy>', self.destroy, add='+')
        self.schedule()

    def schedule(self, event=None):
        if event is not None and event.widget != self.window:
            return
        if self.job is None:
            self.job = self.window.after_idle(self.apply)

    def apply(self):
        self.job = None
        # Tk's winfo_id is the client HWND; GA_ROOT resolves its decorated wrapper.
        hwnd = self.user.GetAncestor(self.window.winfo_id(), 2)
        if not hwnd:
            return
        # Windows 11's compositor rounds the complete frame, including its shadow.
        # https://learn.microsoft.com/windows/apps/desktop/modernize/ui/apply-rounded-corners
        preference = ctypes.c_int(2)  # DWMWCP_ROUND
        native_rounding = self.dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(preference),
                                                        ctypes.sizeof(preference)) == 0
        if native_rounding and not self.window.overrideredirect():
            return
        # Windows 10 fallback: clip the outer frame, updating on resize/restore.
        rect = wintypes.RECT()
        if not self.user.GetWindowRect(hwnd, ctypes.byref(rect)):
            return
        width, height = rect.right - rect.left, rect.bottom - rect.top
        maximized = bool(self.user.IsZoomed(hwnd))
        # Custom chrome uses the same 24-pixel curve as its drawn border.
        diameter = 48 if self.window.overrideredirect() else round(
            32 * (self.user.GetDpiForWindow(hwnd) or 96) / 96)
        signature = (hwnd, width, height, maximized, diameter)
        if self.last_region == signature:
            return
        if maximized:
            result = self.user.SetWindowRgn(hwnd, None, True)
        else:
            region = self.gdi.CreateRoundRectRgn(0, 0, width + 1, height + 1,
                                                diameter, diameter)
            if not region:
                return
            result = self.user.SetWindowRgn(hwnd, region, True)
            # On success Windows owns the region; on failure we still own it.
            if not result:
                self.gdi.DeleteObject(region)
        if result:
            self.last_region = signature

    def destroy(self, event):
        if event.widget == self.window and self.job is not None:
            self.window.after_cancel(self.job)
            self.job = None
