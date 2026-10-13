import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ai_help.core import load_config, save_config
from ai_help.shell import refresh_menu


class Settings:
    def __init__(self, window, on_saved=None):
        self.window, self.on_saved = window, on_saved
        self.config = load_config()
        window.title('伙伴设置')
        window.geometry('630x540')
        window.minsize(600, 520)
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='让它成为你的伙伴', font=('Microsoft YaHei UI', 18, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 8))
        ttk.Label(frame, text='这里的选项会用于下一次召唤。').grid(row=1, column=0, columnspan=3, sticky='w', pady=(0, 20))
        self.values = {}
        fields = [('nickname', '伙伴昵称'), ('backend', '默认 AI'), ('codex_path', 'Codex 程序'),
                  ('claude_path', 'Claude 程序'), ('codex_model', 'Codex 模型'), ('claude_model', 'Claude 模型')]
        for index, (key, label) in enumerate(fields, 2):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky='w', pady=9)
            value = tk.StringVar(value=self.config[key])
            self.values[key] = value
            widget = (ttk.Combobox(frame, textvariable=value, values=['codex', 'claude'], state='readonly')
                      if key == 'backend' else ttk.Entry(frame, textvariable=value))
            widget.grid(row=index, column=1, sticky='ew', padx=12)
            if key.endswith('_path'):
                def browse(variable=value):
                    path = filedialog.askopenfilename(parent=window)
                    if path:
                        variable.set(path)
                ttk.Button(frame, text='浏览', command=browse).grid(row=index, column=2)
        frame.columnconfigure(1, weight=1)
        self.forbid = tk.BooleanVar(value=self.config['forbid_modification'])
        ttk.Checkbutton(frame, text='默认禁止修改', variable=self.forbid).grid(row=8, column=0, columnspan=3, sticky='w', pady=10)
        ttk.Label(frame, text='模型留空使用默认值；程序可填名称或完整路径。\n使用现有 CLI 登录状态。修改范围为工作目录；停止不会撤销修改。', wraplength=550).grid(row=9, column=0, columnspan=3, sticky='w', pady=10)
        ttk.Button(frame, text='保存设置', command=self.save).grid(row=10, column=2, pady=8)

    def save(self):
        updates = {key: value.get().strip() for key, value in self.values.items()}
        nickname = updates['nickname']
        if not nickname or len(nickname) > 20 or any(ord(char) < 32 for char in nickname):
            messagebox.showerror('伙伴昵称', '请填写 1–20 个字符的昵称。', parent=self.window)
            return
        if any(not updates[key] for key in ('codex_path', 'claude_path')):
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
