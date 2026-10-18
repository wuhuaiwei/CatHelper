import tkinter as tk
import queue
import threading
from tkinter import ttk, filedialog, messagebox, font
from ai_help.core import load_config, save_config
from ai_help.models import fetch_models
from ai_help.shell import refresh_menu, apply_icon
from ai_help.settings_style import BG, INK, MUTED, FONT, SettingsCard, setup_styles, draw_cat
from ai_help.window_frame import RoundedWindow, SettingsChrome
from ai_help.program_check import ProgramErrorDialog, BACKEND_NAMES


class HoverTip:
    def __init__(self, widget, text):
        self.widget, self.text = widget, text
        self.job = self.popup = None
        widget.bind('<Enter>', self.schedule, add='+')
        for event in ('<Leave>', '<ButtonPress>', '<Destroy>'):
            widget.bind(event, self.hide, add='+')

    def schedule(self, event=None):
        self.hide()
        self.job = self.widget.after(450, self.show)

    def show(self):
        self.job = None
        self.popup = tk.Toplevel(self.widget)
        self.popup.overrideredirect(True)
        self.popup.attributes('-topmost', True)
        tk.Label(self.popup, text=self.text, padx=12, pady=9, wraplength=400,
                 bg='#FFF9ED', fg=INK, font=('Microsoft YaHei UI', 9),
                 relief='solid', borderwidth=1, justify='left').pack()
        self.popup.update_idletasks()
        x = min(self.widget.winfo_rootx(), max(0, self.widget.winfo_screenwidth() - self.popup.winfo_width()))
        y = min(self.widget.winfo_rooty() + self.widget.winfo_height() + 5,
                max(0, self.widget.winfo_screenheight() - self.popup.winfo_height()))
        self.popup.geometry(f'+{x}+{y}')

    def hide(self, event=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.popup:
            self.popup.destroy()
            self.popup = None


class Settings:
    def __init__(self, window, on_saved=None):
        self.window, self.on_saved = window, on_saved
        self.config = load_config()
        window.title('伙伴设置')
        apply_icon(window)
        window.geometry('660x690')
        window.minsize(620, 670)
        window.configure(bg=BG)
        setup_styles(window)
        self.chrome = SettingsChrome(window)
        content = self.chrome.body
        header = tk.Frame(content, bg=BG)
        header.pack(fill='x', pady=(0, 16))
        portrait = tk.Canvas(header, width=88, height=88, bg=BG, highlightthickness=0)
        portrait.pack(side='left', padx=(0, 14))
        draw_cat(portrait)
        headings = tk.Frame(header, bg=BG)
        headings.pack(side='left', fill='x', expand=True)
        tk.Label(headings, text='伙伴的小偏好', bg=BG, fg=INK,
                 font=('Microsoft YaHei UI', 21, 'bold')).pack(anchor='w')
        tk.Label(headings, text='把每一点小习惯，调成喜欢的样子。', bg=BG, fg=MUTED,
                 font=('Microsoft YaHei UI', 10)).pack(anchor='w', pady=(6, 0))
        for surface in (header, portrait, headings, *headings.winfo_children()):
            self.chrome.make_draggable(surface)
        identity = SettingsCard(content, '01   认识你的伙伴')
        identity.pack(fill='x', pady=(0, 14))
        intelligence = SettingsCard(content, '02   伙伴的 AI 魔法')
        intelligence.pack(fill='x')
        self.values = {}
        self.model_widgets, self.model_display, self.model_tips = {}, {}, {}
        self.model_results = queue.Queue()
        self.model_cache = {}
        self.test_buttons = {}
        self.manual_test = None
        self.model_job = self.query_cancel = None
        self.query_generation = 0
        self.closed = False
        self.tips = []
        self.backend_widgets = {'codex': [], 'claude': []}
        fields = [('nickname', '伙伴昵称'), ('pet_size', '伙伴图标大小'), ('backend', '默认 AI'),
                  ('codex_path', 'Codex 程序'), ('claude_path', 'Claude 程序'),
                  ('codex_model', 'Codex 模型'), ('claude_model', 'Claude 模型')]
        for index, (key, label) in enumerate(fields, 2):
            frame = identity.body if key in ('nickname', 'pet_size') else intelligence.body
            index = index - 1 if key in ('nickname', 'pet_size') else index - 3
            label_widget = tk.Label(frame, text=label, bg='white', fg=INK, font=FONT)
            label_widget.grid(row=index, column=0, sticky='w', pady=9)
            row_widgets = [label_widget]
            value = tk.StringVar(value=self.config[key])
            self.values[key] = value
            widget = (ttk.Combobox(frame, textvariable=value, values=['codex', 'claude'] if key == 'backend' else ['大', '中', '小'], state='readonly', style='Companion.TCombobox', font=FONT)
                      if key in ('backend', 'pet_size') else ttk.Entry(frame, textvariable=value, style='Companion.TEntry', font=FONT))
            if key.endswith('_model'):
                widget.destroy()
                backend = key.split('_')[0]
                display = tk.StringVar(value=value.get() or '默认（跟随 CLI）')
                widget = ttk.Combobox(frame, textvariable=display, state='disabled', style='Companion.TCombobox', font=FONT)
                widget.bind('<<ComboboxSelected>>', lambda event, v=value, d=display:
                            v.set('' if d.get() == '默认（跟随 CLI）' else d.get()))
                self.model_widgets[backend] = widget
                self.model_display[backend] = display
                self.model_tips[backend] = HoverTip(widget, '填写对应程序后自动获取模型。')
            widget.grid(row=index, column=1, columnspan=1 if key.endswith('_path') else 2,
                        sticky='ew', padx=(16, 0), pady=6)
            row_widgets.append(widget)
            if key.endswith('_path'):
                def browse(variable=value):
                    path = filedialog.askopenfilename(parent=window)
                    if path:
                        variable.set(path)
                # Anchor the button to the input's actual height, independent of theme/DPI.
                button_width = font.Font(window, font=FONT).measure('测试中') + 20
                holder = tk.Frame(frame, bg='white', width=button_width*2+8, height=1)
                holder.grid(row=index, column=2, sticky='ew', padx=(8, 0))
                button = ttk.Button(holder, text='浏览', command=browse, padding=(8, 0),
                                    style='Companion.Soft.TButton', cursor='hand2')
                button.place(x=0, width=button_width, relheight=1)
                backend = key.split('_')[0]
                test = ttk.Button(holder, text='测试', command=lambda b=backend: self.test_program(b),
                                  padding=(4, 0), style='Companion.Soft.TButton', cursor='hand2')
                test.place(x=button_width+8, width=button_width, relheight=1)
                self.test_buttons[backend] = test
                self.tips.append(HoverTip(test, '测试程序启动和模型接口，不发送 AI 对话请求。'))
                widget.bind('<Configure>', lambda event, h=holder: h.configure(height=event.height), add='+')
                self.tips.append(HoverTip(widget, '程序可填名称或完整路径；使用现有 CLI 登录状态。'))
                row_widgets.append(holder)
            for backend in self.backend_widgets:
                if key.startswith(backend + '_'):
                    self.backend_widgets[backend].extend(row_widgets)
        self.values['backend'].trace_add('write', self.update_backend_fields)
        for backend in self.backend_widgets:
            self.values[backend + '_path'].trace_add('write', self.schedule_models)
        self.update_backend_fields()
        self.forbid = tk.BooleanVar(value=self.config['forbid_modification'])
        forbid = ttk.Checkbutton(intelligence.body, text='默认禁止修改', variable=self.forbid,
                                 style='Companion.TCheckbutton', cursor='hand2')
        forbid.grid(row=7, column=0, columnspan=3, sticky='w', pady=(12, 0))
        self.tips.append(HoverTip(forbid, '修改范围为工作目录；停止不会撤销修改。'))
        footer = tk.Frame(content, bg=BG)
        footer.pack(side='bottom', fill='x', pady=(18, 0))
        tk.Label(footer, text='每次召唤，都更懂你一点。', bg=BG, fg=MUTED,
                 font=('Microsoft YaHei UI', 9)).pack(side='left')
        ttk.Button(footer, text='保存小偏好  ♡', command=self.save,
                   style='Companion.Primary.TButton', cursor='hand2').pack(side='right')
        window.bind('<Destroy>', self.close_queries, add='+')
        self.poll_job = window.after(100, self.poll_models)
        window.update_idletasks()
        window.minsize(max(620, content.winfo_reqwidth()+20), max(670, content.winfo_reqheight()+20))
        self.rounded_window = RoundedWindow(window)

    def update_backend_fields(self, *_):
        selected = self.values['backend'].get()
        for backend, widgets in self.backend_widgets.items():
            for widget in widgets:
                if backend == selected:
                    widget.grid()
                else:
                    widget.grid_remove()
        self.schedule_models()

    def schedule_models(self, *_):
        if self.closed:
            return
        self.manual_test = None
        for button in self.test_buttons.values():
            button.configure(text='测试', state='normal')
        if self.model_job:
            self.window.after_cancel(self.model_job)
            self.model_job = None
        if self.query_cancel:
            self.query_cancel.set()
        self.query_generation += 1
        backend = self.values['backend'].get()
        program = self.values[backend + '_path'].get().strip()
        self.model_widgets[backend].configure(state='disabled')
        self.model_tips[backend].hide()
        self.model_tips[backend].text = '填写对应程序后自动获取模型。'
        if program:
            self.model_tips[backend].text = '正在获取模型列表…'
            self.model_job = self.window.after(500, self.start_model_query)

    def test_program(self, backend):
        if self.manual_test or self.closed or backend != self.values['backend'].get():
            return
        self.schedule_models()
        program = self.values[backend + '_path'].get().strip()
        if not program:
            self.show_program_error(backend, '尚未填写程序名称或路径。')
            return
        if self.model_job:
            self.window.after_cancel(self.model_job)
            self.model_job = None
        # A manual test must really query the CLI rather than reusing cached data.
        self.model_cache.pop((backend, program), None)
        self.manual_test = (self.query_generation, backend)
        self.test_buttons[backend].configure(text='测试中', state='disabled')
        self.start_model_query()

    def show_program_error(self, backend, error):
        self.test_dialog = ProgramErrorDialog(self.window, backend, error)

    def start_model_query(self):
        self.model_job = None
        backend = self.values['backend'].get()
        program = self.values[backend + '_path'].get().strip()
        generation = self.query_generation
        if (backend, program) in self.model_cache:
            self.model_results.put((generation, backend, self.model_cache[backend, program], None))
            return
        cancel = self.query_cancel = threading.Event()

        def work():
            try:
                models = fetch_models(backend, program, cancel)
                self.model_results.put((generation, backend, models, None))
            except Exception as exc:
                self.model_results.put((generation, backend, [], str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll_models(self):
        while not self.model_results.empty():
            generation, backend, models, error = self.model_results.get_nowait()
            if generation != self.query_generation:
                continue
            manual = self.manual_test == (generation, backend)
            if manual:
                self.manual_test = None
                self.test_buttons[backend].configure(text='测试', state='normal')
            tip = self.model_tips[backend]
            if error:
                tip.text = '获取模型失败：' + error + '\n重新选择 AI 或修改程序路径可重试；原有模型设置会保留。'
            else:
                program = self.values[backend + '_path'].get().strip()
                self.model_cache[backend, program] = models
                self.model_widgets[backend].configure(values=['默认（跟随 CLI）'] + models, state='readonly')
                tip.text = '选择模型；“默认”使用 CLI 的默认模型。'
            if manual:
                if error:
                    self.show_program_error(backend, error)
                else:
                    messagebox.showinfo('测试通过',
                                        f'{BACKEND_NAMES[backend]} 已成功启动，并获取 {len(models)} 个模型。\n'
                                        '模型下拉框已更新，本次测试没有发送 AI 对话请求。', parent=self.window)
        if not self.closed:
            self.poll_job = self.window.after(100, self.poll_models)

    def close_queries(self, event):
        if event.widget != self.window:
            return
        self.closed = True
        if self.query_cancel:
            self.query_cancel.set()
        for job in (self.model_job, self.poll_job):
            if job:
                self.window.after_cancel(job)

    def save(self):
        updates = {key: value.get().strip() for key, value in self.values.items()}
        nickname = updates['nickname']
        if not nickname or len(nickname) > 20 or any(ord(char) < 32 for char in nickname):
            messagebox.showerror('伙伴昵称', '请填写 1–20 个字符的昵称。', parent=self.window)
            return
        if not updates[updates['backend'] + '_path']:
            messagebox.showerror('程序路径', '程序名称或路径不能为空。', parent=self.window)
            return
        self.config.update(updates)
        self.config['forbid_modification'] = self.forbid.get()
        self.config['mode'] = 'read-only' if self.forbid.get() else 'workspace-write'
        try:
            save_config(self.config)
            refresh_menu(nickname)
        except Exception as exc:
            messagebox.showerror('保存设置', str(exc), parent=self.window)
            return
        if self.on_saved:
            self.on_saved(self.config)
        self.window.destroy()
