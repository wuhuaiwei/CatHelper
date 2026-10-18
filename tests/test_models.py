import sys
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_help.models import fetch_models, model_directory


FAKE_CLI = '''import json, sys, time
if 'child' in sys.argv:
    import subprocess
    from pathlib import Path
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    Path(sys.argv[2]).write_text(str(child.pid))
if 'error' in sys.argv:
    print('not authenticated: please log in', file=sys.stderr, flush=True)
    sys.exit(2)
for line in sys.stdin:
    request = json.loads(line)
    if "timeout" in sys.argv:
        time.sleep(10)
    if request.get("type") == "control_request":
        result = {"type": "control_response", "response": {
            "subtype": "success", "request_id": request["request_id"],
            "response": {"models": [{"value": "sonnet"}, {"value": "opus"}]}}}
    elif request.get("method") == "initialize":
        result = {"id": request["id"], "result": {}}
    elif request.get("method") == "model/list":
        cursor = request["params"].get("cursor")
        result = {"id": request["id"], "result": {
            "data": [{"model": "second" if cursor else "first"},
                     {"model": "hidden", "hidden": True}],
            "nextCursor": None if cursor else "page2"}}
    else:
        continue
    print(json.dumps(result), flush=True)
'''


class ModelTests(unittest.TestCase):
    def test_temporary_directory_lock_does_not_override_result(self):
        with patch('ai_help.models.shutil.rmtree', side_effect=PermissionError('locked')) as remove, \
             patch('ai_help.models.time.sleep'):
            with model_directory() as directory:
                self.assertTrue(Path(directory).is_dir())
            self.assertEqual(remove.call_count, 3)
        shutil.rmtree(directory)

    @unittest.skipUnless(os.name == 'nt', 'Windows process tree cleanup')
    def test_model_query_terminates_cli_child_process(self):
        import ctypes
        from ctypes import wintypes
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'cli.py'
            pidfile = Path(directory) / 'child.pid'
            script.write_text(FAKE_CLI, encoding='utf-8')
            with patch('ai_help.models.resolve_program', return_value=[sys.executable, str(script), 'child', str(pidfile)]):
                self.assertEqual(fetch_models('claude', 'fake'), ['sonnet', 'opus'])
            kernel = ctypes.windll.kernel32
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            process = kernel.OpenProcess(0x100000, False, int(pidfile.read_text()))
            if process:
                try:
                    self.assertEqual(kernel.WaitForSingleObject(process, 3000), 0)
                finally:
                    kernel.CloseHandle(process)

    def test_cli_error_details_are_available_for_program_test(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'cli.py'
            script.write_text(FAKE_CLI, encoding='utf-8')
            with patch('ai_help.models.resolve_program', return_value=[sys.executable, str(script), 'error']):
                with self.assertRaisesRegex(RuntimeError, 'not authenticated'):
                    fetch_models('claude', 'fake')

    def test_empty_path_does_not_launch_cli(self):
        with patch('ai_help.models.resolve_program') as resolve:
            self.assertEqual(fetch_models('claude', ' '), [])
            resolve.assert_not_called()

    def test_model_protocols_and_pagination(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'cli.py'
            script.write_text(FAKE_CLI, encoding='utf-8')
            with patch('ai_help.models.resolve_program', return_value=[sys.executable, str(script)]):
                self.assertEqual(fetch_models('claude', 'fake'), ['sonnet', 'opus'])
                self.assertEqual(fetch_models('codex', 'fake'), ['first', 'second'])

    def test_timeout_and_cancel_stop_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'cli.py'
            script.write_text(FAKE_CLI, encoding='utf-8')
            with patch('ai_help.models.resolve_program', return_value=[sys.executable, str(script), 'timeout']):
                with self.assertRaises(TimeoutError):
                    fetch_models('claude', 'fake', timeout=0.15)
                cancel = threading.Event()
                cancel.set()
                with self.assertRaisesRegex(RuntimeError, '取消'):
                    fetch_models('claude', 'fake', cancel)
