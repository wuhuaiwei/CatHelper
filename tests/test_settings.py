import tkinter as tk
import unittest
from unittest.mock import patch
from ai_help.core import DEFAULTS
from ai_help.settings import Settings


class SettingsTests(unittest.TestCase):
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
                settings.forbid.set(True)
                settings.save()
                config = save.call_args.args[0]
                self.assertEqual(config['nickname'], '团子')
                self.assertEqual(config['backend'], 'claude')
                self.assertEqual(config['mode'], 'read-only')
                menu.assert_called_once_with('团子')
            finally:
                root.destroy()
