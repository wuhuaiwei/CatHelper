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
    def test_long_message_scroll_is_bounded_and_reading_position_is_preserved(self):
        import time
        with tempfile.TemporaryDirectory() as directory, patch('app.load_config', return_value=dict(DEFAULTS)):
            root = tk.Tk()
            try:
                app = App(root, Path(directory))

                def settle():
                    deadline = time.monotonic() + 0.15
                    while time.monotonic() < deadline:
                        root.update()
                        time.sleep(0.01)

                app.append('\n'.join(f'第 {line} 行：这是一条很长的消息。' for line in range(200)))
                settle()
                body = app.message_bodies[-1]
                frame = app.message_frames[-1]
                app.output.yview_moveto(0.4)
                root.update()
                before = frame.winfo_y()
                body.event_generate('<MouseWheel>', delta=120)
                root.update()
                distance = frame.winfo_y() - before
                self.assertGreater(distance, 0)
                self.assertLessEqual(distance, app.output.winfo_height() * 0.4 + 1)
                self.assertFalse(app.follow_tail)
                body.event_generate('<MouseWheel>', delta=-120)
                root.update()
                self.assertLessEqual(abs(frame.winfo_y()-before), 1)

                body.event_generate('<MouseWheel>', delta=1200)
                root.update()
                self.assertLessEqual(frame.winfo_y()-before, app.output.winfo_height() * 0.4 + 1)
                before_small = frame.winfo_y()
                for _ in range(12):
                    body.event_generate('<MouseWheel>', delta=1)
                root.update()
                self.assertGreater(frame.winfo_y(), before_small)
                self.assertLess(frame.winfo_y()-before_small, app.scroll_line_height)

                reading_position = frame.winfo_y()
                app.fit_message(body)
                app.append('新消息不应该把正在阅读的位置拉到底部。')
                settle()
                self.assertEqual(frame.winfo_y(), reading_position)
                self.assertFalse(app.follow_tail)
                app.output.yview_moveto(1)
                body.event_generate('<MouseWheel>', delta=-120)
                root.update()
                self.assertTrue(app.follow_tail)
                app.append('在底部时继续跟随新消息。')
                settle()
                self.assertAlmostEqual(app.output.yview()[1], 1.0)
            finally:
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
                root.destroy()

    def test_enter_sends_and_modified_enter_inserts_newlines(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.DATA', Path(directory)), \
             patch('app.load_config', return_value=dict(DEFAULTS)), \
             patch('app.Runner', FakeRunner), \
             patch('ai_help.companion.ime_composing', return_value=False) as composing:
            root = tk.Tk()
            try:
                app = App(root, Path(directory))
                app.open_input()
                root.update()
                app.prompt.focus_force()
                app.prompt.insert('insert', '第一行')
                app.prompt.event_generate('<Control-Return>')
                app.prompt.insert('insert', '第二行')
                app.prompt.event_generate('<Shift-Return>')
                app.prompt.insert('insert', '第三行')
                self.assertEqual(app.prompt.get('1.0', 'end-1c'), '第一行\n第二行\n第三行')
                self.assertEqual(app.runner.calls, [])
                composing.return_value = True
                app.prompt.event_generate('<Return>')
                self.assertEqual(app.runner.calls, [])
                self.assertEqual(app.prompt.get('1.0', 'end-1c'), '第一行\n第二行\n第三行')
                composing.return_value = False
                app.prompt.event_generate('<Return>')
                self.assertEqual(app.runner.calls, [('第一行\n第二行\n第三行', None)])
                self.assertEqual(app.prompt.get('1.0', 'end-1c'), '')
                self.assertFalse(app.editing)
            finally:
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
                root.destroy()

    def test_bubble_drag_moves_cat_and_bubble_without_opening_editor(self):
        with tempfile.TemporaryDirectory() as directory, patch('app.load_config', return_value=dict(DEFAULTS)):
            root = tk.Tk()
            try:
                app = App(root, Path(directory))
                root.geometry('+650+500')
                root.update()
                for surface in (app.name_label, app.bubble_canvas, app.output,
                                app.message_frames[0], app.message_frames[0].winfo_children()[0]):
                    with self.subTest(surface=surface.winfo_class()):
                        cat = (root.winfo_x(), root.winfo_y())
                        bubble = (app.bubble.winfo_x(), app.bubble.winfo_y())
                        surface.event_generate('<ButtonPress-1>', x=2, y=2, rootx=500, rooty=400)
                        surface.event_generate('<B1-Motion>', x=2, y=2, rootx=520, rooty=415)
                        root.update()
                        surface.event_generate('<ButtonRelease-1>', x=2, y=2, rootx=520, rooty=415)
                        root.update()
                        self.assertEqual((root.winfo_x(), root.winfo_y()), (cat[0]+20, cat[1]+15))
                        self.assertEqual((app.bubble.winfo_x(), app.bubble.winfo_y()),
                                         (bubble[0]+20, bubble[1]+15))
                        self.assertFalse(app.editing)
                # A drag that returns to its starting point must not become a click.
                app.name_label.event_generate('<ButtonPress-1>', rootx=500, rooty=400)
                app.name_label.event_generate('<B1-Motion>', rootx=520, rooty=415)
                app.name_label.event_generate('<B1-Motion>', rootx=500, rooty=400)
                app.name_label.event_generate('<ButtonRelease-1>', rootx=500, rooty=400)
                self.assertFalse(app.editing)
                app.name_label.event_generate('<ButtonPress-1>', rootx=500, rooty=400)
                app.name_label.event_generate('<ButtonRelease-1>', rootx=501, rooty=401)
                self.assertTrue(app.editing)
                self.assertFalse(app.message_bodies[0].bind('<B1-Motion>'))
                self.assertFalse(app.prompt.bind('<B1-Motion>'))
            finally:
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
                root.destroy()

    def test_settings_temporarily_hide_bubble_and_preserve_draft(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.load_config', return_value=dict(DEFAULTS)), \
             patch('app.Settings') as settings:
            root = tk.Tk()
            try:
                app = App(root, Path(directory))
                root.update()
                for mode in ('conversation', 'editing', 'hidden'):
                    with self.subTest(mode=mode):
                        app.bubble.deiconify()
                        app.hide_input()
                        if mode == 'editing':
                            app.open_input()
                            app.prompt.insert('1.0', '还没发送的草稿')
                        elif mode == 'hidden':
                            app.collapse_bubble()
                        root.update()
                        editing = app.editing
                        draft = app.prompt.get('1.0', 'end-1c')
                        app.settings()
                        root.update()
                        window = app.settings_window
                        self.assertEqual(app.bubble.state(), 'withdrawn')
                        calls = settings.call_count
                        app.settings()
                        self.assertEqual(settings.call_count, calls)
                        app.open_input()
                        root.update()
                        self.assertEqual(app.bubble.state(), 'withdrawn')
                        self.assertEqual(app.editing, editing)
                        child = tk.Frame(window)
                        child.destroy()
                        self.assertIs(app.settings_window, window)
                        self.assertEqual(app.bubble.state(), 'withdrawn')
                        window.destroy()
                        root.update()
                        self.assertIsNone(app.settings_window)
                        self.assertEqual(app.bubble.state(), 'withdrawn' if mode == 'hidden' else 'normal')
                        self.assertEqual(app.editing, editing)
                        self.assertEqual(app.prompt.get('1.0', 'end-1c'), draft)
            finally:
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
                root.destroy()

    def test_shaped_cat_opens_editable_bubble_and_hides_editor(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.load_config', return_value=dict(DEFAULTS)):
            root = tk.Tk()
            try:
                app = App(root, Path(directory))
                root.update()
                self.assertTrue(root.overrideredirect())
                self.assertEqual(str(root.attributes('-transparentcolor')), '#FF00FF')
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
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
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
                self.assertNotIn('第 2 轮', ''.join(body.get('1.0', 'end') for body in app.message_bodies))
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
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
                root.destroy()

    def test_message_layout_selection_scrolling_and_collapse(self):
        import time
        with tempfile.TemporaryDirectory() as directory, patch('app.load_config', return_value=dict(DEFAULTS)):
            root = tk.Tk()
            try:
                app = App(root, Path(directory))
                def settle():
                    until = time.monotonic() + .25
                    while time.monotonic() < until:
                        root.update()
                        time.sleep(.01)
                settle()
                self.assertEqual(app.name_label.cget('text'), '与小爱对话')
                self.assertEqual(app.bubble.title(), '与小爱对话')
                self.assertFalse(app.status_label.winfo_ismapped())
                self.assertIn(Path(directory).name, app.message_bodies[0].get('1.0', 'end'))
                app.append('你好', 'user')
                settle()
                short = app.message_bodies[-1]
                self.assertEqual(int(short.cget('height')), 1)
                self.assertEqual(short.cget('state'), 'disabled')
                short.event_generate('<Button-1>', x=12, y=10)
                root.update()
                self.assertFalse(app.editing)
                short.tag_add('sel', '1.0', '1.2')
                short.event_generate('<<Copy>>')
                root.update()
                self.assertEqual(root.clipboard_get(), '你好')
                app.append('这是一段需要换行的长消息。' * 12)
                settle()
                long = app.message_bodies[-1]
                self.assertGreaterEqual(int(long.cget('height')), 2)
                for i in range(8):
                    app.append('消息 ' + str(i))
                settle()
                before = app.output.yview()[0]
                app.message_bodies[-1].event_generate('<MouseWheel>', delta=120)
                root.update()
                self.assertLess(app.output.yview()[0], before)
                app.output.yview_moveto(1)
                before = app.output.yview()[0]
                for _ in range(12):
                    app.bubble_canvas.event_generate('<MouseWheel>', delta=1)
                root.update()
                self.assertLess(app.output.yview()[0], before)
                app.close_button.event_generate('<Button-1>')
                root.update()
                self.assertEqual(app.bubble.state(), 'withdrawn')
                self.assertTrue(root.winfo_ismapped())
                app.menu.invoke(0)
                root.update()
                self.assertTrue(app.bubble.winfo_ismapped())
                self.assertTrue(app.editing)
                app.busy = True
                app.collapse_bubble()
                app.open_input()
                root.update()
                self.assertTrue(app.bubble.winfo_ismapped())
                self.assertFalse(app.editing)
                app.status.set('正在处理')
                root.update()
                self.assertTrue(app.status_label.winfo_ismapped())
                self.assertIsNone(app.status_job)
                app.busy = False
                app.status.set('已完成')
                self.assertIsNotNone(app.status_job)
                app.clear_status()
                root.update()
                self.assertFalse(app.status_label.winfo_ismapped())
            finally:
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
                root.destroy()

    def test_pointer_position_and_live_size(self):
        with tempfile.TemporaryDirectory() as directory, patch('app.load_config', return_value=dict(DEFAULTS)):
            root = tk.Tk()
            try:
                with patch.object(root, 'winfo_pointerx', return_value=500), patch.object(root, 'winfo_pointery', return_value=400):
                    app = App(root, Path(directory))
                root.update()
                self.assertEqual((root.winfo_x(), root.winfo_y()), (516, 416))
                self.assertEqual(root.winfo_width(), int(94*1.9*2/3))
                with patch('app.Settings') as settings:
                    app.settings()
                    saved = settings.call_args.args[1]
                    saved(dict(DEFAULTS, nickname='团子', pet_size='小'))
                self.assertEqual(app.name_label.cget('text'), '与团子对话')
                self.assertEqual(app.bubble.title(), '与团子对话')
                app.settings_window.destroy()
                root.update()
                self.assertEqual(root.winfo_width(), int(94*1.9/3))
                self.assertAlmostEqual(app.pet.drawing_scale, 1.9/3)
                app.root.geometry('+9999+9999')
                root.update()
                app.config['pet_size'] = '大'
                app.apply_size()
                root.update()
                self.assertLessEqual(root.winfo_x()+root.winfo_width(), root.winfo_screenwidth())
                self.assertLessEqual(root.winfo_y()+root.winfo_height(), root.winfo_screenheight())
                app.show_tooltip()
                self.assertTrue(app.tooltip.winfo_exists())
                app.hide_tooltip()
                self.assertIsNone(app.tooltip)
            finally:
                root.update_idletasks()
                for job in root.tk.call('after', 'info'):
                    root.tk.call('after', 'cancel', job)
                root.destroy()


if __name__ == '__main__':
    unittest.main()
