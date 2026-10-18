"""Read model catalogs through the configured CLI, without starting an AI turn."""
# Protocol references:
# https://developers.openai.com/codex/app-server
# https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/query.py
import json
import queue
import subprocess
import tempfile
import threading
import time

from ai_help.core import resolve_program


def fetch_models(backend, program, cancel=None, timeout=20):
    if not program.strip():
        return []
    cancel = cancel or threading.Event()
    command = resolve_program(program)
    if backend == 'codex':
        command += ['app-server']
    elif backend == 'claude':
        command += ['-p', '--input-format', 'stream-json', '--output-format',
                    'stream-json', '--verbose', '--no-session-persistence',
                    '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}']
    else:
        raise ValueError('未知 AI 类型')
    with tempfile.TemporaryDirectory(prefix='companion-models-') as directory:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                                   errors='replace', cwd=directory,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        messages = queue.Queue()

        def read_output():
            try:
                for line in process.stdout:
                    try:
                        messages.put(json.loads(line))
                    except ValueError:
                        pass
            finally:
                messages.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout

        def send(message):
            process.stdin.write(json.dumps(message) + '\n')
            process.stdin.flush()

        def receive(request_id):
            while not cancel.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('获取模型超时，请检查程序和登录状态。')
                try:
                    message = messages.get(timeout=min(remaining, 0.1))
                except queue.Empty:
                    continue
                if message is None:
                    raise RuntimeError('程序未返回模型列表，请检查版本和登录状态。')
                if not isinstance(message, dict):
                    continue
                if backend == 'codex' and message.get('id') == request_id:
                    if 'error' in message:
                        raise RuntimeError('模型接口调用失败。')
                    return message['result']
                if backend == 'claude' and message.get('type') == 'control_response':
                    response = message.get('response', {})
                    if response.get('request_id') == request_id:
                        if response.get('subtype') == 'error':
                            raise RuntimeError('此 Claude 版本不支持模型查询，请更新 CLI。')
                        return response.get('response', {})
            raise RuntimeError('模型查询已取消。')

        try:
            if backend == 'codex':
                send({'id': 1, 'method': 'initialize', 'params': {
                    'clientInfo': {'name': 'cat_assistant', 'version': '1.0.0'}}})
                receive(1)
                send({'method': 'initialized', 'params': {}})
                models, cursor, request_id = [], None, 2
                while True:
                    send({'id': request_id, 'method': 'model/list',
                          'params': {'limit': 100, 'cursor': cursor}})
                    result = receive(request_id)
                    models.extend(item['model'] for item in result.get('data', [])
                                  if item.get('model') and not item.get('hidden'))
                    cursor = result.get('nextCursor')
                    if not cursor:
                        break
                    request_id += 1
            else:
                send({'type': 'control_request', 'request_id': 'init',
                      'request': {'subtype': 'initialize'}})
                result = receive('init')
                models = [item['value'] for item in result.get('models', []) if item.get('value')]
            if not models:
                raise RuntimeError('程序未提供可用模型，请检查版本和登录状态。')
            return list(dict.fromkeys(models))
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            reader.join(timeout=2)
            process.stdin.close()
            process.stdout.close()
