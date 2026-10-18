import tkinter as tk
import unittest
from unittest.mock import patch
from ai_help.core import DEFAULTS
from ai_help.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_permission_dropdown_loads_existing_config_and_saves_write_access(self):
        root = tk.Tk()
        root.withdraw()
        try:
            for forbidden in (False, True):
                with self.subTest(forbidden=forbidden), \
                     patch('ai_help.settings.load_config', return_value=dict(DEFAULTS, forbid_modification=forbidden)), \
                     patch('ai_help.settings.save_config') as save, \
                     patch('ai_help.settings.refresh_menu'):
                    settings = Settings(tk.Toplevel(root))
                    self.assertEqual(str(settings.permission_widget['state']), 'readonly')
                    self.assertEqual(tuple(settings.permission_widget['values']),
                                     ('默认允许修改文件', '默认禁止修改文件'))
                    self.assertEqual(settings.permission.get(), '默认禁止修改文件' if forbidden
                                     else '默认允许修改文件')
                    settings.permission.set('默认允许修改文件')
                    settings.save()
                    self.assertFalse(save.call_args.args[0]['forbid_modification'])
                    self.assertEqual(save.call_args.args[0]['mode'], 'workspace-write')
        finally:
            root.destroy()

    def test_manual_program_test_refreshes_cache_and_reports_success_or_failure(self):
        root = tk.Tk()
        root.withdraw()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS)), \
             patch('ai_help.settings.fetch_models', return_value=['new-model']) as fetch, \
             patch('ai_help.settings.threading.Thread') as thread, \
             patch('ai_help.settings.messagebox.showinfo') as success, \
             patch.object(Settings, 'show_program_error') as failure:
            try:
                settings = Settings(tk.Toplevel(root))
                settings.model_cache['codex', 'codex'] = ['cached-model']
                settings.test_buttons['codex'].invoke()
                self.assertEqual(str(settings.test_buttons['codex']['state']), 'disabled')
                count = thread.call_count
                settings.test_program('codex')
                self.assertEqual(thread.call_count, count)
                thread.call_args.kwargs['target']()
                settings.window.after_cancel(settings.poll_job)
                settings.poll_models()
                fetch.assert_called_once()
                success.assert_called_once()
                failure.assert_not_called()
                self.assertEqual(settings.model_cache['codex', 'codex'], ['new-model'])
                self.assertEqual(str(settings.test_buttons['codex']['state']), 'normal')
                fetch.side_effect = RuntimeError('login required')
                settings.test_program('codex')
                thread.call_args.kwargs['target']()
                settings.window.after_cancel(settings.poll_job)
                settings.poll_models()
                failure.assert_called_once_with('codex', 'login required')
                self.assertEqual(str(settings.model_widgets['codex']['state']), 'disabled')
                self.assertEqual(str(settings.test_buttons['codex']['state']), 'normal')
            finally:
                root.destroy()

    def test_program_test_empty_path_and_stale_results(self):
        root = tk.Tk()
        root.withdraw()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS, claude_path='')), \
             patch('ai_help.settings.threading.Thread') as thread, \
             patch('ai_help.settings.messagebox.showinfo') as success, \
             patch.object(Settings, 'show_program_error') as failure:
            try:
                settings = Settings(tk.Toplevel(root))
                settings.values['backend'].set('claude')
                settings.test_program('claude')
                failure.assert_called_once()
                thread.assert_not_called()
                failure.reset_mock()
                settings.values['claude_path'].set('claude')
                settings.test_program('claude')
                generation = settings.query_generation
                settings.values['backend'].set('codex')
                settings.model_results.put((generation, 'claude', [], 'late failure'))
                settings.window.after_cancel(settings.poll_job)
                settings.poll_models()
                success.assert_not_called()
                failure.assert_not_called()
                self.assertEqual(str(settings.test_buttons['claude']['state']), 'normal')
            finally:
                root.destroy()

    def test_failure_dialog_opens_correct_official_guide_and_restores_grab(self):
        from ai_help.program_check import ProgramErrorDialog, OFFICIAL_GUIDES
        root = tk.Tk()
        with patch('ai_help.settings.load_config', return_value=dict(DEFAULTS)), \
             patch('ai_help.program_check.webbrowser.open') as browser:
            try:
                settings = Settings(tk.Toplevel(root))
                settings.window.grab_set()
                for backend in ('codex', 'claude'):
                    dialog = ProgramErrorDialog(settings.window, backend, '找不到程序')
                    browser.assert_not_called()
                    self.assertIs(settings.window.grab_current(), dialog.window)
                    dialog.guide_button.invoke()
                    browser.assert_called_once_with(OFFICIAL_GUIDES[backend])
                    browser.reset_mock()
                    dialog.window.destroy()
                    self.assertIs(settings.window.grab_current(), settings.window)
            finally:
                root.destroy()

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
                for action in holder.winfo_children():
                    self.assertEqual(action.winfo_height(), entry.winfo_height())
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
                settings.permission.set('默认禁止修改文件')
                settings.save()
                config = save.call_args.args[0]
                self.assertEqual(config['pet_size'], '小')
                self.assertEqual(config['nickname'], '团子')
                self.assertEqual(config['backend'], 'claude')
                self.assertEqual(config['mode'], 'read-only')
                self.assertTrue(config['forbid_modification'])
                menu.assert_called_once_with('团子')
            finally:
                root.destroy()
