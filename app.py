import argparse
import json
import queue
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox

from ai_help.core import DATA, Conversation, Runner, load_config
from ai_help.pet import Pet
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
    def append(self, text, tag='pet'):
        self.output.configure(state="normal")
        label = '你' if tag == 'user' else self.nickname if tag == 'pet' else ''
        self.output.insert("end", (label + '\n' if label else '') + text + "\n\n", tag)
        self.output.see("end")
        self.output.configure(state="disabled")

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
        turn = sum(message["role"] == "user" for message in self.conversation.messages)
        self.append(prompt, 'user')
        self.append('第 ' + str(turn) + ' 轮', 'note')
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
        self.logs.clear()
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self.status.set("新的一页，想聊些什么？")
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
                    DATA.mkdir(exist_ok=True)
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
            return
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.attributes('-topmost', True)
        self.settings_window.transient(self.root)
        self.settings_window.grab_set()
        def saved(config):
            self.config = dict(config)
            self.nickname = config['nickname']
            self.root.title('召唤' + self.nickname)
            self.name_label.configure(text=self.nickname)
            self.forbid.set(config['forbid_modification'])
            self.allow.set(not self.forbid.get())
            self.start_button.configure(text='告诉' + self.nickname + ' ↗')
        Settings(self.settings_window, saved)

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=str(Path.cwd()))
    parser.add_argument('--settings', action='store_true')
    args = parser.parse_args()
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
