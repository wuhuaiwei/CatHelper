import tkinter as tk
import unittest
from unittest.mock import patch
from ai_help.core import DEFAULTS
from ai_help.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_custom_window_drag_resize_and_close(self):
        root = tk.Tk()
        root.withdraw()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS)), \
             patch('ai_help.settings.threading.Thread'):
            try:
                window = tk.Toplevel(root)
                settings = Settings(window)
                window.geometry('+100+100')
                window.update()
                self.assertTrue(window.overrideredirect())
                chrome = settings.chrome
                left, top = window.winfo_x(), window.winfo_y()
                chrome.titlebar.event_generate('<ButtonPress-1>', x=4, y=4, rootx=110, rooty=110)
                chrome.titlebar.event_generate('<B1-Motion>', x=4, y=4, rootx=150, rooty=140)
                window.update()
                self.assertEqual((window.winfo_x(), window.winfo_y()), (left+40, top+30))
                chrome.titlebar.event_generate('<ButtonRelease-1>')
                self.assertIsNone(chrome.drag_origin)

                chrome.grip.event_generate('<ButtonPress-1>', x=5, y=5, rootx=700, rooty=700)
                chrome.grip.event_generate('<B1-Motion>', x=5, y=5, rootx=0, rooty=0)
                window.update()
                self.assertEqual((window.winfo_width(), window.winfo_height()), window.minsize())
                chrome.grip.event_generate('<ButtonRelease-1>')
                chrome.grip.event_generate('<ButtonPress-1>', x=5, y=5, rootx=500, rooty=500)
                width, height = window.winfo_width(), window.winfo_height()
                chrome.grip.event_generate('<B1-Motion>', x=5, y=5, rootx=560, rooty=540)
                window.update()
                self.assertEqual((window.winfo_width(), window.winfo_height()), (width+60, height+40))
                self.assertGreaterEqual(chrome.body.winfo_height(), chrome.body.winfo_reqheight())
                chrome.close_button.invoke()
                self.assertFalse(window.winfo_exists())
                self.assertTrue(settings.closed)
            finally:
                root.destroy()

    def test_model_loading_empty_path_failure_and_stale_results(self):
        root = tk.Tk()
        root.withdraw()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS, claude_path='', claude_model='saved')), \
             patch('ai_help.settings.fetch_models', return_value=['sonnet', 'opus']) as fetch, \
             patch('ai_help.settings.threading.Thread') as thread:
            try:
                settings = Settings(tk.Toplevel(root))
                settings.values['backend'].set('claude')
                self.assertIsNone(settings.model_job)
                self.assertEqual(str(settings.model_widgets['claude']['state']), 'disabled')
                fetch.assert_not_called()
                settings.values['claude_path'].set('claude')
                settings.window.after_cancel(settings.model_job)
                settings.start_model_query()
                thread.call_args.kwargs['target']()
                settings.window.after_cancel(settings.poll_job)
                settings.poll_models()
                fetch.assert_called_once()
                combo = settings.model_widgets['claude']
                self.assertEqual(str(combo['state']), 'readonly')
                self.assertEqual(tuple(combo['values']), ('默认（跟随 CLI）', 'sonnet', 'opus'))
                self.assertEqual(settings.values['claude_model'].get(), 'saved')
                settings.model_display['claude'].set('sonnet')
                combo.event_generate('<<ComboboxSelected>>')
                self.assertEqual(settings.values['claude_model'].get(), 'sonnet')
                settings.model_display['claude'].set('默认（跟随 CLI）')
                combo.event_generate('<<ComboboxSelected>>')
                self.assertEqual(settings.values['claude_model'].get(), '')

                old_generation = settings.query_generation
                settings.values['claude_path'].set('other-claude')
                settings.model_results.put((old_generation, 'claude', ['stale'], None))
                settings.model_results.put((settings.query_generation, 'claude', [], 'offline'))
                settings.window.after_cancel(settings.poll_job)
                settings.poll_models()
                self.assertEqual(str(combo['state']), 'disabled')
                self.assertNotIn('stale', combo['values'])
                self.assertIn('offline', settings.model_tips['claude'].text)
            finally:
                root.destroy()

    def test_browse_button_matches_entry_height_and_hints_are_hidden(self):
        root = tk.Tk()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS)):
            try:
                window = tk.Toplevel(root)
                settings = Settings(window)
                window.update()
                _, entry, holder, _, _ = settings.backend_widgets['codex']
                button = holder.winfo_children()[0]
                self.assertEqual(button.winfo_height(), entry.winfo_height())
                self.assertGreater(button.winfo_width(), 30)
                labels = [child.cget('text') for child in entry.master.winfo_children()
                          if child.winfo_class() == 'TLabel']
                self.assertFalse(any('模型留空' in text or '修改范围' in text for text in labels))
                self.assertTrue(all(tip.popup is None for tip in settings.tips))
            finally:
                root.destroy()

    def test_backend_switch_shows_only_selected_fields_and_keeps_edits(self):
        root = tk.Tk()
        root.withdraw()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS, backend='claude')), \
             patch('ai_help.settings.save_config') as save, \
             patch('ai_help.settings.refresh_menu'):
            try:
                settings = Settings(tk.Toplevel(root))

                def assert_visible_backend(selected):
                    for backend, widgets in settings.backend_widgets.items():
                        self.assertEqual(len(widgets), 5)
                        for widget in widgets:
                            self.assertEqual(widget.winfo_manager(), 'grid' if backend == selected else '')

                assert_visible_backend('claude')
                settings.values['claude_model'].set('my-claude-model')
                settings.values['backend'].set('codex')
                assert_visible_backend('codex')
                settings.values['codex_model'].set('my-codex-model')
                settings.values['backend'].set('claude')
                assert_visible_backend('claude')
                self.assertEqual(settings.values['claude_model'].get(), 'my-claude-model')
                settings.save()
                config = save.call_args.args[0]
                self.assertEqual(config['claude_model'], 'my-claude-model')
                self.assertEqual(config['codex_model'], 'my-codex-model')
            finally:
                root.destroy()

    def test_empty_hidden_program_does_not_block_save(self):
        root = tk.Tk()
        root.withdraw()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS, claude_path='')), \
             patch('ai_help.settings.save_config') as save, \
             patch('ai_help.settings.refresh_menu'), \
             patch('ai_help.settings.messagebox.showerror') as error:
            try:
                settings = Settings(tk.Toplevel(root))
                settings.values['backend'].set('claude')
                settings.save()
                error.assert_called_once()
                save.assert_not_called()
                settings.values['backend'].set('codex')
                settings.save()
                save.assert_called_once()
            finally:
                root.destroy()

    def test_save_nickname_default_backend_and_read_only(self):
        root = tk.Tk()
        root.withdraw()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS)), \
             patch('ai_help.settings.save_config') as save, \
             patch('ai_help.settings.refresh_menu') as menu:
            try:
                window = tk.Toplevel(root)
                settings = Settings(window)
                settings.values['nickname'].set('团子')
                settings.values['backend'].set('claude')
                settings.values['pet_size'].set('小')
                settings.forbid.set(True)
                settings.save()
                config = save.call_args.args[0]
                self.assertEqual(config['pet_size'], '小')
                self.assertEqual(config['nickname'], '团子')
                self.assertEqual(config['backend'], 'claude')
                self.assertEqual(config['mode'], 'read-only')
                menu.assert_called_once_with('团子')
            finally:
                root.destroy()
