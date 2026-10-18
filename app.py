import argparse
import json
import queue
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox

from ai_help.core import DATA, Conversation, Runner, load_config
from ai_help.pet import Pet
from ai_help.shell import apply_icon
from ai_help.settings import Settings
from ai_help.companion import CompanionUI


def theme(root):
    root.configure(bg='#F7F5FF')
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background='#F7F5FF')
    style.configure('TLabel', background='#F7F5FF', foreground='#332B48', font=('Microsoft YaHei UI', 10))
    style.configure('TButton', padding=8, font=('Microsoft YaHei UI', 10))
    style.configure('TCheckbutton', background='#F7F5FF', foreground='#837A96', font=('Microsoft YaHei UI', 9))
    style.configure('Send.TButton', background='#8062CB', foreground='white', borderwidth=0)
    style.map('Send.TButton', background=[('active', '#6B50B1'), ('disabled', '#BFB1DC')])


class ChatController:
    def start(self):
        if self.busy:
            return
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            return
        self.config["mode"] = 'read-only' if self.forbid.get() else 'workspace-write'
        resume, instruction = self.conversation.prepare(self.config, prompt)
        self.busy, self.failed = True, False
        self.saw_answer = False
        self.history = [("prompt", prompt)]
        self.append(prompt, 'user')
        self.prompt.delete("1.0", "end")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.forbid_box.configure(state="disabled")
        self.pet.thinking = True
        self.settings_button.configure(state="disabled")
        self.new_button.configure(state="disabled")
        self.status.set("让我想想，正在帮你处理…")
        if hasattr(self, 'hide_input'):
            self.hide_input()
        self.runner.start(self.config, self.target, instruction, resume)

    def new_conversation(self):
        if self.busy:
            return
        self.conversation.reset()
        self.follow_tail = True
        self.scroll_remainder = 0.0
        for frame in self.message_frames:
            frame.destroy()
        self.message_frames.clear()
        self.message_bodies.clear()
        self.logs.clear()
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self.status.set('')
        if hasattr(self, 'open_input'):
            self.open_input()
        else:
            self.prompt.focus_set()

    def cancel(self):
        self.status.set("正在取消…")
        self.cancel_button.configure(state="disabled")
        import threading
        threading.Thread(target=self.runner.cancel, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, text = self.runner.events.get_nowait()
                self.history.append((kind, text))
                if kind == "session":
                    self.conversation.session = text
                elif kind == "done":
                    self.busy = False
                    self.status.set('遇到一点问题，请看看下面的提示。' if self.failed else
                                    '已停下，已完成的修改会保留。' if text == '已取消' else '处理好啦，你可以继续告诉我。')
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.forbid_box.configure(state="normal")
                    self.pet.thinking = False
                    self.settings_button.configure(state="normal")
                    self.new_button.configure(state="normal")
                    DATA.mkdir(parents=True, exist_ok=True)
                    name = datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"
                    (DATA / name).write_text(json.dumps({"target": str(self.target), "backend": self.config['backend'], "session": self.conversation.session, "events": self.history}, ensure_ascii=False, indent=2), encoding="utf-8")
                elif kind == "result":
                    if not self.saw_answer:
                        self.append(text)
                        self.conversation.answer(text)
                elif kind == 'log':
                    self.logs.append(text)
                    if hasattr(self, 'bubble'):
                        progress = {'command_execution': '正在检查和运行任务…',
                                    'file_change': '正在处理文件…', 'mcp_tool_call': '正在调用工具…'}
                        self.status.set(progress.get(text, '正在处理：' + text[:65]))
                else:
                    if kind == "error":
                        self.failed = True
                    if kind == "answer":
                        self.saw_answer = True
                        self.conversation.answer(text)
                    self.append(text, 'error' if kind == 'error' else 'pet')
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def show_logs(self):
        window = tk.Toplevel(self.root)
        window.title(self.nickname + '的工作过程')
        apply_icon(window)
        window.geometry('640x400')
        output = tk.Text(window, wrap='word', font=('Consolas', 10), padx=15, pady=15)
        output.pack(fill='both', expand=True)
        def update():
            if not window.winfo_exists():
                return
            output.configure(state='normal')
            output.delete('1.0', 'end')
            output.insert('end', '\n\n'.join(self.logs) or '还没有工作记录。')
            output.configure(state='disabled')
            window.after(500, update)
        update()

    def settings(self):
        if self.busy:
            return
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        restore_bubble = self.bubble.state() != 'withdrawn'
        self.hide_tooltip()
        self.bubble.withdraw()
        self.settings_window = tk.Toplevel(self.root)
        settings_window = self.settings_window

        def restore_after_settings(event):
            if event.widget != settings_window:
                return
            if self.settings_window == settings_window:
                self.settings_window = None
            if restore_bubble and self.root.winfo_exists() and self.bubble.winfo_exists():
                self.position_bubble()
                self.bubble.deiconify()
                self.bubble.lift()
                if self.editing:
                    self.prompt.focus_force()

        settings_window.bind('<Destroy>', restore_after_settings, add='+')
        self.settings_window.attributes('-topmost', True)
        self.settings_window.transient(self.root)
        self.settings_window.grab_set()
        def saved(config):
            self.config = dict(config)
            self.nickname = config['nickname']
            self.root.title('召唤' + self.nickname)
            self.name_label.configure(text='与' + self.nickname + '对话')
            self.bubble.title('与' + self.nickname + '对话')
            self.apply_size()
            self.forbid.set(config['forbid_modification'])
            self.allow.set(not self.forbid.get())
            self.start_button.configure(text='告诉' + self.nickname + ' ↗')
        Settings(self.settings_window, saved)
        settings_window.lift()
        settings_window.focus_force()

    def close(self):
        if self.busy:
            if not messagebox.askyesno("任务运行中", "关闭窗口将取消任务，已完成的修改会保留。继续关闭？"):
                return
            self.runner.cancel()
        self.root.destroy()


class CompanionApp(CompanionUI, ChatController):
    def __init__(self, root, target):
        theme(root)
        self.initialize(root, target, load_config(), Runner())


def check_installation(report):
    """Exercise the installed Tk UI without calling a backend or saving settings."""
    from ai_help.core import CONFIG
    from ai_help.shell import ICON
    root = tk.Tk()
    try:
        app = CompanionApp(root, Path.cwd())
        dialog = tk.Toplevel(root)
        settings = Settings(dialog)
        if settings.model_job:
            dialog.after_cancel(settings.model_job)
            settings.model_job = None
        dialog.withdraw()
        def finish():
            _, program, browser, _, _ = settings.backend_widgets[settings.values['backend'].get()]
            report.write_text(json.dumps({
                'ok': True, 'title': app.bubble.title(), 'icon_exists': ICON.is_file(),
                'config': str(CONFIG), 'cat_width': root.winfo_width(),
                'greeting': app.message_bodies[0].get('1.0', 'end-1c'),
                'settings_rounded': bool(dialog.overrideredirect()),
                'settings_backend': settings.values['backend'].get(),
                'model_dropdown': settings.model_widgets[settings.values['backend'].get()].winfo_class(),
                'browse_matches_input_height': browser.winfo_height() == program.winfo_height(),
            }, ensure_ascii=False, indent=2), encoding='utf-8')
            root.destroy()
        root.after(300, finish)
        root.mainloop()
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=str(Path.cwd()))
    parser.add_argument('--settings', action='store_true')
    parser.add_argument('--refresh-menu', action='store_true', help='刷新已注册的右键菜单')
    parser.add_argument('--check-installation', metavar='REPORT', help='检查打包运行环境并写入 JSON 报告')
    args = parser.parse_args()
    if args.refresh_menu:
        from ai_help.shell import refresh_menu
        refresh_menu(load_config()['nickname'])
        return
    if args.check_installation:
        check_installation(Path(args.check_installation))
        return
    target = Path(args.target)
    root = tk.Tk()
    theme(root)
    if not args.settings and not target.exists():
        root.withdraw()
        messagebox.showerror("AI 帮忙", "目标不存在：" + str(target))
        root.destroy()
        return
    try:
        if args.settings:
            Settings(root)
        else:
            CompanionApp(root, target)
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("AI 帮忙", str(exc))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
