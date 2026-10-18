"""Actionable CLI test failures with the backend's official installation guide."""
import tkinter as tk
from tkinter import ttk
import webbrowser

from ai_help.settings_style import BG, INK, MUTED, FONT
from ai_help.window_frame import RoundedWindow, SettingsChrome

OFFICIAL_GUIDES = {
    'codex': 'https://developers.openai.com/codex/cli',
    'claude': 'https://code.claude.com/docs/en/overview',
}
BACKEND_NAMES = {'codex': 'Codex', 'claude': 'Claude Code'}


class ProgramErrorDialog:
    def __init__(self, parent, backend, error):
        self.previous_grab = parent.grab_current()
        self.window = window = tk.Toplevel(parent)
        window.title('AI 程序测试')
        window.transient(parent)
        window.attributes('-topmost', True)
        window.configure(bg=BG)
        window.geometry('620x520')
        self.chrome = SettingsChrome(window, title='AI 程序测试')
        body = self.chrome.body
        name = BACKEND_NAMES[backend]
        tk.Label(body, text=f'{name} 还没有准备好', bg=BG, fg='#B45667',
                 font=('Microsoft YaHei UI', 17, 'bold')).pack(anchor='w', pady=(4, 12))
        tk.Label(body, text='测试未通过，原因如下：', bg=BG, fg=INK, font=FONT).pack(anchor='w')
        details = tk.Text(body, width=1, height=4, wrap='word', font=FONT, padx=10, pady=8,
                          bg='white', fg=INK, relief='flat', borderwidth=0)
        details.insert('1.0', str(error))
        details.configure(state='disabled')
        details.pack(fill='both', expand=True, pady=(8, 14))
        tk.Label(body, text='安装与连接指引', bg=BG, fg=INK,
                 font=('Microsoft YaHei UI', 11, 'bold')).pack(anchor='w')
        tk.Label(body, text=(f'1. 打开下方官方指引，安装 Windows 版 {name} CLI。\n'
                             f'2. 在终端运行 {backend}，按提示完成登录。\n'
                             '3. 回到设置，填写程序名称或浏览选择实际程序，再点击“测试”。\n\n'
                             '如果已经安装，请检查程序路径、登录状态和网络；必要时更新 CLI。'),
                 bg=BG, fg=MUTED, font=FONT, justify='left', wraplength=552).pack(
                     fill='x', pady=(8, 14))
        buttons = tk.Frame(body, bg=BG)
        buttons.pack(fill='x')
        self.guide_button = ttk.Button(buttons, text='打开官方安装指引 ↗',
                                       style='Companion.Primary.TButton', cursor='hand2',
                                       command=lambda: webbrowser.open(OFFICIAL_GUIDES[backend]))
        self.guide_button.pack(side='left')
        ttk.Button(buttons, text='返回设置', style='Companion.Soft.TButton',
                   command=window.destroy).pack(side='right')
        window.bind('<Destroy>', self.restore_grab, add='+')
        window.update_idletasks()
        window.minsize(max(620, body.winfo_reqwidth()+20), max(520, body.winfo_reqheight()+20))
        window.geometry(f'+{max(0, parent.winfo_rootx()+20)}+{max(0, parent.winfo_rooty()+40)}')
        self.rounded_window = RoundedWindow(window)
        window.grab_set()
        window.lift(parent)
        window.focus_force()
        self.guide_button.focus_set()

    def restore_grab(self, event):
        if event.widget == self.window and self.previous_grab and self.previous_grab.winfo_exists():
            self.previous_grab.grab_set()

