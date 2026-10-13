"""Shaped desktop companion and its attached speech bubble."""
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ai_help.core import Conversation
from ai_help.pet import Pet

TRANSPARENT = '#FF00FF'


class CompanionUI:
    def initialize(self, root, target, config, runner):
        self.root, self.target, self.config, self.runner = root, Path(target).resolve(), config, runner
        self.busy = self.failed = False
        self.conversation = Conversation()
        self.history, self.logs = [], []
        self.settings_window = None
        self.nickname = config['nickname']
        self.editing = False
        self.drag_origin = None
        root.title('召唤' + self.nickname)
        root.overrideredirect(True)
        root.configure(bg=TRANSPARENT)
        root.attributes('-topmost', True)
        root.attributes('-transparentcolor', TRANSPARENT)
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f'184x200+{max(10, screen_w-230)}+{max(10, screen_h-280)}')
        self.pet = Pet(root, scale=1.9, background=TRANSPARENT)
        self.pet.pack()
        self.pet.configure(cursor='hand2')
        self.pet.bind('<ButtonPress-1>', self.drag_start)
        self.pet.bind('<B1-Motion>', self.drag_move)
        self.pet.bind('<ButtonRelease-1>', self.drag_end)
        self.pet.bind('<Button-3>', self.popup_menu)

        self.bubble = tk.Toplevel(root)
        self.bubble.title(self.nickname + '的对话')
        self.bubble.overrideredirect(True)
        self.bubble.configure(bg=TRANSPARENT)
        self.bubble.attributes('-topmost', True)
        self.bubble.attributes('-transparentcolor', TRANSPARENT)
        self.bubble.geometry('380x300')
        self.bubble_canvas = tk.Canvas(self.bubble, bg=TRANSPARENT, highlightthickness=0)
        self.bubble_canvas.pack(fill='both', expand=True)
        content = tk.Frame(self.bubble_canvas, bg='white')
        self.content_window = self.bubble_canvas.create_window(18, 16, anchor='nw', window=content)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)
        self.name_label = tk.Label(content, text=self.nickname, bg='white', fg='#8062CB', anchor='w', font=('Microsoft YaHei UI', 12, 'bold'))
        self.name_label.grid(row=0, column=0, sticky='ew')
        self.status = tk.StringVar(value='点击气泡告诉我，右键小猫打开菜单')
        tk.Label(content, textvariable=self.status, bg='white', fg='#837A96', anchor='w', wraplength=326,
                 font=('Microsoft YaHei UI', 9)).grid(row=1, column=0, sticky='ew', pady=(4, 8))
        self.output = tk.Text(content, state='disabled', wrap='word', bg='white', fg='#332B48', relief='flat',
                              height=5, width=1, font=('Microsoft YaHei UI', 11), cursor='hand2')
        self.output.grid(row=2, column=0, sticky='nsew')
        for tag, color in [('user', '#8062CB'), ('pet', '#332B48'), ('note', '#837A96'), ('error', '#B45667')]:
            self.output.tag_configure(tag, foreground=color, spacing3=8)
        self.editor = tk.Frame(content, bg='white')
        self.editor.columnconfigure(0, weight=1)
        self.prompt = tk.Text(self.editor, height=3, width=1, wrap='word', bg='#F7F5FF', fg='#332B48', relief='flat',
                              font=('Microsoft YaHei UI', 11), padx=8, pady=8, insertbackground='#8062CB')
        self.prompt.grid(row=0, column=0, sticky='ew', pady=(8, 6))
        self.start_button = ttk.Button(self.editor, text='告诉' + self.nickname + ' ↗', style='Send.TButton', command=self.start)
        self.start_button.grid(row=1, column=0, sticky='e')
        self.forbid = tk.BooleanVar(value=config['forbid_modification'])
        self.allow = tk.BooleanVar(value=not self.forbid.get())
        # Controller handles are intentionally hidden; actions live in the cat menu.
        self.cancel_button = ttk.Button(content, command=self.cancel)
        self.new_button = ttk.Button(content, command=self.new_conversation)
        self.settings_button = ttk.Button(content, command=self.settings)
        self.forbid_box = ttk.Checkbutton(content, variable=self.forbid)
        self.menu = tk.Menu(root, tearoff=False, font=('Microsoft YaHei UI', 10))
        self.menu.add_command(label='继续对话', command=self.open_input)
        self.menu.add_command(label='设置…', command=self.settings)
        self.menu.add_checkbutton(label='允许修改', variable=self.allow, command=lambda: self.forbid.set(not self.allow.get()))
        self.menu.add_separator()
        self.menu.add_command(label='清空对话', command=self.new_conversation)
        self.menu.add_command(label='查看工作过程', command=self.show_logs)
        self.menu.add_command(label='停止任务', command=self.cancel)
        self.menu.add_separator()
        self.menu.add_command(label='收起小猫', command=self.close)
        self.output.bind('<Button-1>', lambda event: self.open_input())
        self.bubble_canvas.bind('<Button-1>', lambda event: self.open_input())
        self.bubble.bind('<Button-3>', self.popup_menu)
        root.bind('<Control-Return>', self.send_shortcut)
        self.bubble.bind('<Control-Return>', self.send_shortcut)
        self.prompt.bind('<Control-Return>', self.send_shortcut)
        self.bubble_canvas.bind('<Configure>', self.draw_bubble)
        root.bind('<Configure>', lambda event: self.position_bubble() if event.widget == root else None)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.bubble.protocol('WM_DELETE_WINDOW', self.close)
        self.append(f'对于这个{"文件夹" if self.target.is_dir() else "文件"}，有什么可以帮你？\n\n{self.target.name or self.target}')
        root.after_idle(self.position_bubble)
        root.after(100, self.poll)

    def draw_bubble(self, event):
        w, h = event.width, event.height
        self.bubble_canvas.delete('shape')
        r = 20
        self.bubble_canvas.create_polygon(0,r, 0,0, r,0, w-r,0, w,0, w,r,
            w,h-32-r, w,h-32, w-r,h-32, w-30,h-32, w-14,h-6,
            w-65,h-32, r,h-32, 0,h-32, 0,h-32-r,
            smooth=True, splinesteps=24, fill='white', outline='#D7CBEC', width=2, tags='shape')
        self.bubble_canvas.tag_lower('shape')
        self.bubble_canvas.itemconfigure(self.content_window, width=max(100,w-38), height=max(100,h-64))

    def position_bubble(self):
        if not self.root.winfo_exists():
            return
        self.root.update_idletasks()
        w, h = 380, 430 if self.editing else 300
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = min(max(8, self.root.winfo_x()-w+25), max(8,sw-w-8))
        y = min(max(8, self.root.winfo_y()-h+100), max(8,sh-h-55))
        self.bubble.geometry(f'{w}x{h}+{x}+{y}')

    def open_input(self):
        if self.busy:
            return
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        self.editing = True
        self.editor.grid(row=3, column=0, sticky='ew')
        self.position_bubble()
        self.bubble.lift()
        self.prompt.focus_force()

    def hide_input(self):
        self.editing = False
        self.editor.grid_remove()
        self.position_bubble()

    def send_shortcut(self, event=None):
        self.start()
        return 'break'

    def drag_start(self, event):
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def drag_move(self, event):
        if self.drag_origin:
            x, y, wx, wy = self.drag_origin
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            nx = min(max(0,wx+event.x_root-x),max(0,sw-184))
            ny = min(max(0,wy+event.y_root-y),max(0,sh-240))
            self.root.geometry(f'+{nx}+{ny}')
            self.position_bubble()

    def drag_end(self, event):
        if self.drag_origin:
            x, y, _, _ = self.drag_origin
            if abs(event.x_root-x)+abs(event.y_root-y) < 6:
                self.open_input()
        self.drag_origin = None

    def popup_menu(self, event):
        for index in (0, 1, 2, 4):
            self.menu.entryconfigure(index, state='disabled' if self.busy else 'normal')
        self.allow.set(not self.forbid.get())
        self.menu.entryconfigure(6, state='normal' if self.busy else 'disabled')
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
