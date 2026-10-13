import queue
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_help.core import DEFAULTS
from app import CompanionApp as App


class FakeRunner:
    def __init__(self):
        self.events = queue.Queue()
        self.calls = []
        self.configs = []

    def start(self, config, target, prompt, session=None):
        self.configs.append(dict(config))
        self.calls.append((prompt, session))
        self.events.put(('session', 'same-session'))
        self.events.put(('answer', '已记住苹果'))
        self.events.put(('done', '已结束'))


class ConversationUITests(unittest.TestCase):
    def test_shaped_cat_opens_editable_bubble_and_hides_editor(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.load_config', return_value=dict(DEFAULTS)):
            root = tk.Tk()
            try:
                app = App(root, Path(directory))
                root.update()
                self.assertTrue(root.overrideredirect())
                self.assertEqual(root.attributes('-transparentcolor'), '#FF00FF')
                self.assertFalse(app.prompt.winfo_ismapped())
                app.open_input()
                root.update()
                for widget in (app.prompt, app.start_button):
                    self.assertTrue(widget.winfo_ismapped())
                    top = widget.winfo_rooty() - app.bubble.winfo_rooty()
                    self.assertGreaterEqual(top, 0)
                    self.assertLessEqual(top + widget.winfo_height(), app.bubble.winfo_height())
                self.assertGreater(app.prompt.winfo_height(), 50)
                app.prompt.focus_force()
                app.prompt.event_generate('<KeyPress-a>')
                root.update()
                self.assertEqual(app.prompt.get('1.0', 'end').strip(), 'a')
                app.hide_input()
                root.update()
                self.assertFalse(app.prompt.winfo_ismapped())
            finally:
                root.destroy()

    def test_send_twice_automatically_resumes_and_new_button_resets(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.DATA', Path(directory)), \
             patch('app.load_config', return_value=dict(DEFAULTS)), \
             patch('app.Runner', FakeRunner):
            root = tk.Tk()
            root.withdraw()
            try:
                app = App(root, Path(directory))
                self.assertFalse(app.forbid.get())
                self.assertFalse(hasattr(app, 'backend_box'))
                self.assertTrue(app.allow.get())
                app.open_input()
                app.prompt.insert('1.0', '请记住苹果')
                app.start()
                self.assertFalse(app.editing)
                self.assertTrue(app.pet.thinking)
                app.open_input()
                self.assertFalse(app.editing)
                app.poll()
                self.assertFalse(app.pet.thinking)
                app.open_input()
                app.prompt.insert('1.0', '刚才说了什么？')
                app.start()
                app.poll()
                self.assertEqual(app.runner.calls[0], ('请记住苹果', None))
                self.assertEqual(app.runner.calls[1], ('刚才说了什么？', 'same-session'))
                self.assertEqual(len(app.conversation.messages), 4)
                self.assertIn('第 2 轮', app.output.get('1.0', 'end'))
                app.new_conversation()
                app.menu.invoke(2)
                self.assertTrue(app.forbid.get())
                app.prompt.insert('1.0', '全新需求')
                app.start()
                app.poll()
                self.assertEqual(app.runner.calls[2], ('全新需求', None))
                self.assertEqual(app.runner.configs[0]['mode'], 'workspace-write')
                self.assertEqual(app.runner.configs[2]['mode'], 'read-only')
            finally:
                root.destroy()


if __name__ == '__main__':
    unittest.main()
