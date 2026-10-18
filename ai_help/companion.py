"""Shaped desktop companion and its attached speech bubble."""
import tkinter as tk
from pathlib import Path
from tkinter import ttk, font
from ai_help.shell import apply_icon, ime_composing

from ai_help.core import Conversation
from ai_help.pet import Pet

TRANSPARENT = '#FF00FF'
CAT_SCALES = {'大': 1, '中': 2/3, '小': 1/3}
MESSAGE_WRAP_PIXELS = 326


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
        self.dragged = False
        self.follow_tail = True
        self.scroll_remainder = 0.0
        root.title('召唤' + self.nickname)
        root.overrideredirect(True)
        root.configure(bg=TRANSPARENT)
        root.attributes('-topmost', True)
        root.attributes('-transparentcolor', TRANSPARENT)
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        self.cat_scale = 1.9 * CAT_SCALES.get(config.get('pet_size', '中'), 2/3)
        self.cat_width, self.cat_height = int(94*self.cat_scale), int(100*self.cat_scale)
        x = min(max(0, root.winfo_pointerx()+16), screen_w-self.cat_width)
        y = min(max(0, root.winfo_pointery()+16), screen_h-self.cat_height)
        root.geometry(f'{self.cat_width}x{self.cat_height}+{x}+{y}')
        self.pet = Pet(root, scale=self.cat_scale, background=TRANSPARENT)
        self.pet.pack()
        self.pet.configure(cursor='hand2')
        self.pet.bind('<ButtonPress-1>', self.drag_start)
        self.pet.bind('<B1-Motion>', self.drag_move)
        self.pet.bind('<ButtonRelease-1>', self.drag_end)
        self.pet.bind('<Button-3>', self.popup_menu)
        self.tooltip = None
        self.tooltip_job = None
        self.pet.bind('<Enter>', self.schedule_tooltip)
        self.pet.bind('<Leave>', self.hide_tooltip)

        self.bubble = tk.Toplevel(root)
        self.bubble.title('与' + self.nickname + '对话')
        apply_icon(root)
        apply_icon(self.bubble)
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
        self.name_label = tk.Label(content, text='与' + self.nickname + '对话', bg='white', fg='#8062CB', anchor='w', font=('Microsoft YaHei UI', 12, 'bold'))
        self.name_label.grid(row=0, column=0, sticky='ew')
        self.close_button = tk.Label(content, text='✕', bg='white', fg='#837A96', cursor='hand2', font=('Segoe UI', 12))
        self.close_button.grid(row=0, column=0, sticky='e')
        self.close_button.bind('<Enter>', lambda e: self.close_button.configure(fg='#D44254'))
        self.close_button.bind('<Leave>', lambda e: self.close_button.configure(fg='#837A96'))
        self.close_button.bind('<Button-1>', lambda e: self.collapse_bubble())
        self.status = tk.StringVar(value='')
        self.status_job = None
        self.status_label = tk.Label(content, textvariable=self.status, bg='white', fg='#837A96', anchor='w', wraplength=326,
                 font=('Microsoft YaHei UI', 9))
        self.status.trace_add('write', self.status_changed)
        self.output = tk.Text(content, state='disabled', wrap='word', bg='white', fg='#332B48', relief='flat',
                              height=5, width=1, font=('Microsoft YaHei UI', 11), cursor='arrow', borderwidth=0)
        self.output.grid(row=2, column=0, sticky='nsew', pady=(8, 0))
        self.scroll_line_height = font.Font(root, font=self.output.cget('font')).metrics('linespace')
        self.message_frames, self.message_bodies = [], []
        self.bubble_canvas.bind('<MouseWheel>', self.scroll_output)
        self.output.bind('<MouseWheel>', self.scroll_output)
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
        for surface in (self.bubble_canvas, content, self.name_label,
                        self.status_label, self.output, self.editor):
            self.bind_bubble_drag(surface)
        self.bubble.bind('<Button-3>', self.popup_menu)
        for key in ('Return', 'KP_Enter'):
            self.prompt.bind(f'<{key}>', self.send_shortcut)
            self.prompt.bind(f'<Control-{key}>', self.newline_shortcut)
            self.prompt.bind(f'<Shift-{key}>', self.newline_shortcut)
        self.bubble_canvas.bind('<Configure>', self.draw_bubble)
        root.bind('<Configure>', lambda event: self.position_bubble() if event.widget == root else None)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.bubble.protocol('WM_DELETE_WINDOW', self.close)
        self.append(f'对于这个{"文件夹" if self.target.is_dir() else "文件"}：{self.target.name or self.target}，有什么可以帮你？')
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
        w, h = 380, 430 if self.editing else 300
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = min(max(8, self.root.winfo_x()-w+int(25*self.cat_scale/1.9)), max(8,sw-w-8))
        y = min(max(8, self.root.winfo_y()-h+int(100*self.cat_scale/1.9)), max(8,sh-h-55))
        self.bubble.geometry(f'{w}x{h}+{x}+{y}')

    def open_input(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        self.bubble.deiconify()
        self.bubble.lift()
        self.position_bubble()
        if self.busy:
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
        if not ime_composing(self.prompt):
            self.start()
        return 'break'

    def newline_shortcut(self, event=None):
        if not ime_composing(self.prompt):
            if self.prompt.tag_ranges('sel'):
                self.prompt.delete('sel.first', 'sel.last')
            self.prompt.insert('insert', '\n')
            self.prompt.see('insert')
        return 'break'

    def drag_start(self, event):
        self.hide_tooltip()
        self.dragged = False
        self.drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())
        return 'break'

    def bind_bubble_drag(self, widget):
        widget.configure(cursor='fleur')
        widget.bind('<ButtonPress-1>', self.drag_start)
        widget.bind('<B1-Motion>', self.drag_move)
        widget.bind('<ButtonRelease-1>', self.drag_end)

    def drag_move(self, event):
        if self.drag_origin:
            x, y, wx, wy = self.drag_origin
            if not self.dragged and abs(event.x_root-x)+abs(event.y_root-y) < 6:
                return 'break'
            self.dragged = True
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            nx = min(max(0,wx+event.x_root-x),max(0,sw-self.cat_width))
            ny = min(max(0,wy+event.y_root-y),max(0,sh-self.cat_height))
            self.root.geometry(f'+{nx}+{ny}')
            self.position_bubble()
        return 'break'

    def drag_end(self, event):
        if self.drag_origin:
            x, y, _, _ = self.drag_origin
            if not self.dragged and abs(event.x_root-x)+abs(event.y_root-y) < 6:
                self.open_input()
        self.drag_origin = None
        self.dragged = False
        return 'break'

    def popup_menu(self, event):
        self.hide_tooltip()
        for index in (1, 2, 4):
            self.menu.entryconfigure(index, state='disabled' if self.busy else 'normal')
        self.allow.set(not self.forbid.get())
        self.menu.entryconfigure(6, state='normal' if self.busy else 'disabled')
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def append(self, text, tag='pet'):
        colors = {'user': ('#8062CB', '#F5F0FF', '#DDD1F2'),
                  'pet': ('#298793', '#EFFAFC', '#C9E5E9'),
                  'error': ('#B45667', '#FFF1F3', '#ECCBD1')}
        foreground, background, border = colors.get(tag, colors['pet'])
        frame = tk.Frame(self.output, bg='white')
        name = tk.Label(frame, text='你' if tag == 'user' else self.nickname,
                        bg='white', fg=foreground, font=('Microsoft YaHei UI', 9, 'bold'), anchor='w')
        name.pack(fill='x', pady=(0, 3))
        box = tk.Frame(frame, bg=background, highlightbackground=border, highlightthickness=1)
        box.pack(anchor='w')
        body_font = font.Font(self.root, family='Microsoft YaHei UI', size=11)
        width = max(1, MESSAGE_WRAP_PIXELS // max(1, body_font.measure('0')))
        body = tk.Text(box, width=width, height=1, wrap='word', font=body_font,
                       bg=background, fg='#332B48', relief='flat', borderwidth=0,
                       padx=5, pady=5, cursor='xterm', exportselection=False)
        body.body_font = body_font
        body.insert('1.0', text)
        body.configure(state='disabled')
        body.pack()
        # Drag the surrounding surfaces; body text keeps its selection bindings.
        for widget in (frame, name, box):
            self.bind_bubble_drag(widget)
        for widget in (frame, name, box, body):
            widget.bind('<MouseWheel>', self.scroll_output)
        self.output.configure(state='normal')
        self.output.window_create('end', window=frame)
        self.output.insert('end', '\n\n')
        self.output.configure(state='disabled')
        self.message_frames.append(frame)
        self.message_bodies.append(body)
        self.root.after_idle(lambda: self.fit_message(body))
        self.follow_output()

    def fit_message(self, body):
        if not body.winfo_exists():
            return
        if body.winfo_width() <= 1:
            body.after(50, lambda: self.fit_message(body))
            return
        count = body.count('1.0', 'end-1c', 'displaylines')
        body.configure(height=max(1, (count[0] if count else 0) + 1))
        self.output.after_idle(self.follow_output)

    def follow_output(self):
        if self.follow_tail and self.output.winfo_exists():
            self.output.see('end')

    def scroll_output(self, event):
        delta = event.delta
        if delta:
            if delta > 0:
                self.follow_tail = False
            # Embedded message frames can be thousands of pixels tall. A Text
            # "unit" can skip that entire frame; pixels keep every line reachable.
            distance = -delta / 120 * self.scroll_line_height * 2
            limit = max(1, int(self.output.winfo_height() * 0.4))
            distance = max(-limit, min(limit, distance))
            if self.scroll_remainder * distance < 0:
                self.scroll_remainder = 0.0
            self.scroll_remainder += distance
            pixels = int(self.scroll_remainder)
            if pixels:
                self.scroll_remainder -= pixels
                self.output.yview_scroll(pixels, 'pixels')
                self.follow_tail = self.output.yview()[1] >= 1 - 1e-6
        return 'break'

    def collapse_bubble(self):
        self.hide_input()
        self.bubble.withdraw()

    def status_changed(self, *args):
        if self.status_job:
            self.root.after_cancel(self.status_job)
            self.status_job = None
        if self.status.get():
            self.status_label.grid(row=1, column=0, sticky='ew', pady=(4, 8))
            if not self.busy:
                self.status_job = self.root.after(6000, self.clear_status)
        else:
            self.status_label.grid_remove()

    def clear_status(self):
        self.status_job = None
        if not self.busy:
            self.status.set('')

    def schedule_tooltip(self, event=None):
        self.hide_tooltip()
        self.tooltip_job = self.root.after(400, self.show_tooltip)

    def show_tooltip(self):
        self.tooltip_job = None
        if self.drag_origin:
            return
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes('-topmost', True)
        tk.Label(self.tooltip, text='点击我继续对话，右键我打开菜单', bg='#FFF9E7', fg='#635477',
                 font=('Microsoft YaHei UI', 9), padx=8, pady=4).pack()
        self.tooltip.update_idletasks()
        x = min(max(0, self.root.winfo_x()), max(0, self.root.winfo_screenwidth()-self.tooltip.winfo_width()))
        y = max(0, self.root.winfo_y()-self.tooltip.winfo_height()-4)
        self.tooltip.geometry(f'+{x}+{y}')

    def hide_tooltip(self, event=None):
        if self.tooltip_job:
            self.root.after_cancel(self.tooltip_job)
            self.tooltip_job = None
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def apply_size(self):
        self.cat_scale = 1.9 * CAT_SCALES.get(self.config.get('pet_size', '中'), 2/3)
        self.cat_width, self.cat_height = int(94*self.cat_scale), int(100*self.cat_scale)
        self.pet.drawing_scale = self.cat_scale
        self.pet.configure(width=self.cat_width, height=self.cat_height)
        x = min(max(0, self.root.winfo_x()), self.root.winfo_screenwidth()-self.cat_width)
        y = min(max(0, self.root.winfo_y()), self.root.winfo_screenheight()-self.cat_height)
        self.root.geometry(f'{self.cat_width}x{self.cat_height}+{x}+{y}')
        self.pet.draw()
        self.position_bubble()
