"""Open repeatable documentation demos without user configuration or AI requests."""
import argparse
from pathlib import Path
import queue
import sys
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai_help.core import DEFAULTS
from ai_help.settings import Settings
from app import CompanionApp, theme


class DemoRunner:
    def __init__(self):
        self.events = queue.Queue()

    def start(self, *args):
        pass

    def cancel(self):
        pass


@patch('app.load_config', lambda: dict(DEFAULTS))
@patch('app.Runner', DemoRunner)
@patch('ai_help.settings.load_config', lambda: dict(DEFAULTS))
@patch('ai_help.settings.save_config', lambda config: None)
@patch('ai_help.settings.refresh_menu', lambda nickname: None)
@patch('ai_help.settings.fetch_models', lambda backend, program, cancel:
       ['gpt-6.1-sol', 'gpt-6-sol'] if backend == 'codex' else ['sonnet', 'opus'])
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('view', choices=['settings', 'conversation'])
    parser.add_argument('--capture-host', action='store_true', help='Use a decorated host for screenshot tools')
    args = parser.parse_args()
    root = tk.Tk()
    theme(root)
    config = dict(DEFAULTS, nickname='小爱')
    if args.view == 'settings':
        with patch('ai_help.settings.load_config', return_value=config):
            settings = Settings(root)
        if settings.model_job:
            root.after_cancel(settings.model_job)
            settings.model_job = None
        settings.model_tips['codex'].text = '文档演示：模型列表来自示例数据。'
        settings.model_widgets['codex'].configure(
            state='readonly', values=['默认（跟随 CLI）', 'gpt-6.1-sol', 'gpt-6-sol'])
        # The demo cannot persist settings or refresh Explorer registration.
        settings.chrome.close_button.configure(command=root.destroy)
        settings.start_model_query = lambda: None
        for child in settings.chrome.body.winfo_children():
            for button in child.winfo_children():
                if isinstance(button, ttk.Button):
                    button.configure(command=root.destroy)
        root.geometry('+180+80')
        if args.capture_host:
            root.overrideredirect(False)
            root.title('CatHelper 文档预览')
    else:
        with patch('app.load_config', return_value=config), patch('app.Runner', DemoRunner):
            app = CompanionApp(root, Path('示例项目'))
        root.geometry('+750+570')
        app.new_conversation()
        app.hide_input()
        app.append('帮我梳理这个文件夹，并告诉我从哪里开始。', 'user')
        app.append('可以呀，我们先从这三步开始：\n\n1. 看 README，了解项目的用途。\n2. 找到启动入口和配置文件。\n3. 运行测试，确认当前状态。\n\n需要修改时，可以在小猫右键菜单中切换“允许修改”。')
        app.open_input()
        app.prompt.insert('1.0', '先帮我看看 README 吧')
    # A preview should never outlive its documentation session indefinitely.
    root.after(600000, root.destroy)
    root.mainloop()


if __name__ == '__main__':
    main()
