import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_help.models import fetch_models


FAKE_CLI = '''import json, sys, time
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
