import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_help import core, runtime, shell


class PackagingTests(unittest.TestCase):
    def test_frozen_config_is_persistent_and_outside_bundle(self):
        with patch.object(sys, 'frozen', True, create=True), patch.dict(os.environ, {'LOCALAPPDATA': r'C:\Users\test\AppData\Local'}):
            self.assertEqual(runtime.data_directory(), Path(r'C:\Users\test\AppData\Local')/'CatAssistant'/'data')
        self.assertEqual(runtime.data_directory(), runtime.ROOT/'data')

    def test_frozen_shell_command_has_no_python_or_source_script(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', r'C:\My Apps\CatAssistant\CatAssistant.exe'):
            self.assertEqual(runtime.launch_command(), '"C:\\My Apps\\CatAssistant\\CatAssistant.exe"')
            with patch.object(shell, 'ICON', Path('missing.ico')):
                self.assertEqual(shell.menu_icon(), sys.executable)
        self.assertIn('pythonw.exe', runtime.launch_command())
        self.assertIn('app.py', runtime.launch_command())

    def test_save_config_creates_nested_data_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)/'CatAssistant'/'data'
            with patch.object(core, 'DATA', data), patch.object(core, 'CONFIG', data/'config.json'):
                core.save_config(dict(core.DEFAULTS, nickname='团子'))
                self.assertEqual(core.load_config()['nickname'], '团子')
                self.assertEqual(core.load_config()['pet_size'], '中')
