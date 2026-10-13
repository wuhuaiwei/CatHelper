import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_help.core import Conversation, DEFAULTS, Runner, build_command, parse_event, resolve_program


DEFAULTS = dict(DEFAULTS, mode='read-only')


class CoreTests(unittest.TestCase):
    def test_second_turn_resumes_captured_native_session(self):
        for backend, event in [('codex', {'type': 'thread.started', 'thread_id': 'native-id'}),
                               ('claude', {'type': 'system', 'session_id': 'native-id'})]:
            conversation = Conversation()
            config = dict(DEFAULTS, backend=backend)
            self.assertEqual(conversation.prepare(config, '记住苹果')[0], None)
            for kind, text in parse_event(backend, json.dumps(event)):
                if kind == 'session':
                    conversation.session = text
            conversation.answer('记住了')
            self.assertEqual(conversation.prepare(config, '我刚才说了什么？'),
                             ('native-id', '我刚才说了什么？'))

    def test_missing_session_carries_both_roles(self):
        conversation = Conversation()
        conversation.prepare(dict(DEFAULTS), '记住苹果')
        conversation.answer('记住了苹果')
        session, prompt = conversation.prepare(dict(DEFAULTS), '我刚才说了什么？')
        self.assertIsNone(session)
        self.assertIn('记住苹果', prompt)
        self.assertIn('记住了苹果', prompt)
        self.assertIn('我刚才说了什么？', prompt)

    def test_reset_and_backend_switch_do_not_leak_context(self):
        conversation = Conversation()
        conversation.prepare(dict(DEFAULTS), '旧上下文')
        conversation.session = 'old-session'
        self.assertEqual(conversation.prepare(dict(DEFAULTS, backend='claude'), '新问题'), (None, '新问题'))
        self.assertEqual(len(conversation.messages), 1)
        conversation.reset()
        self.assertEqual(conversation.prepare(dict(DEFAULTS), '新问题'), (None, '新问题'))

    def test_permission_change_preserves_text_but_not_native_session(self):
        conversation = Conversation()
        conversation.prepare(dict(DEFAULTS), '已有需求')
        conversation.session = 'old-session'
        session, prompt = conversation.prepare(dict(DEFAULTS, mode='workspace-write'), '继续修改')
        self.assertIsNone(session)
        self.assertIn('已有需求', prompt)

    def test_codex_discovered_without_explorer_path(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'OpenAI/Codex/bin/version/codex.exe'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'fake')
            with patch('ai_help.core.shutil.which', return_value=None), \
                 patch('ai_help.core.os.name', 'nt'), \
                 patch.dict('os.environ', {'LOCALAPPDATA': directory}):
                self.assertEqual(resolve_program('codex'), [str(binary)])

    def test_explicit_missing_path_is_not_silently_replaced(self):
        with patch('ai_help.core.shutil.which', return_value=None):
            with self.assertRaises(FileNotFoundError):
                resolve_program('Z:/missing/codex.exe')

    @patch('ai_help.core.resolve_program', return_value=['codex.exe'])
    def test_codex_uses_stdin_and_explicit_sandbox(self, _):
        command = build_command(dict(DEFAULTS))
        self.assertEqual(command[-1], '-')
        self.assertIn('read-only', command)
        resumed = build_command(dict(DEFAULTS), 'test-session')
        self.assertEqual(resumed[2:4], ['resume', 'test-session'])
        self.assertNotIn('--sandbox', resumed)

    @patch('ai_help.core.resolve_program', return_value=['claude.exe'])
    def test_claude_read_only_has_no_write_or_shell_tools(self, _):
        config = dict(DEFAULTS, backend='claude')
        command = build_command(config)
        tools = command[command.index('--tools') + 1]
        self.assertEqual(tools, 'Read,Glob,Grep')
        config['mode'] = 'workspace-write'
        tools = build_command(config)[command.index('--tools') + 1]
        self.assertIn('Write', tools)
        self.assertNotIn('Bash', tools)

    def test_failure_and_permission_denials_are_visible(self):
        events = parse_event('claude', json.dumps({'type': 'result', 'is_error': True,
                            'errors': ['auth failed'], 'permission_denials': [{'tool': 'Write'}]}))
        self.assertEqual(sum(kind == 'error' for kind, _ in events), 2)
        events = parse_event('codex', '{"type":"turn.failed","error":{"message":"offline"}}')
        self.assertEqual(events[0][0], 'error')

    def test_runner_streams_unicode_stdin_and_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'fake.py'
            script.write_text('import sys,json\np=sys.stdin.read()\nprint(json.dumps({"type":"thread.started","thread_id":"session"}))\nprint(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":p}}))\nprint("diagnostic",file=sys.stderr)\n', encoding='utf-8')
            runner = Runner()
            with patch('ai_help.core.build_command', return_value=[sys.executable, str(script)]):
                runner.start(dict(DEFAULTS), directory, '中文 "$()" & 提示')
                events = []
                while True:
                    event = runner.events.get(timeout=10)
                    events.append(event)
                    if event[0] == 'done':
                        break
            self.assertIn(('session', 'session'), events)
            self.assertTrue(any(kind == 'answer' and '中文 "$()" & 提示' in text for kind, text in events))
            self.assertIn(('log', 'diagnostic'), events)
            self.assertFalse(any(kind == 'error' for kind, _ in events))


if __name__ == '__main__':
    unittest.main()
