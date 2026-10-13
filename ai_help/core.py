import json
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = DATA / "config.json"
DEFAULTS = {"backend": "codex", "codex_path": "codex", "claude_path": "claude",
            "codex_model": "", "claude_model": "", "mode": "workspace-write",
            "nickname": "小爱", "forbid_modification": False}


class Conversation:
    """Keep the native session and a text fallback for every turn in a window."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.session = None
        self.identity = None
        self.messages = []

    def prepare(self, config, prompt):
        backend = config["backend"]
        identity = (backend, config["mode"], config.get(backend + "_model"),
                    config.get(backend + "_path"))
        if self.identity and self.identity[0] != backend:
            self.reset()
        resume = self.session if identity == self.identity else None
        instruction = prompt
        if not resume and self.messages:
            # Preserve dialogue when the backend does not supply a session ID,
            # or when model/permissions change and a fresh native session is needed.
            instruction = ("这是同一个窗口内的连续对话。下面 JSON 数组是之前的对话，"
                "仅作为上下文。请结合它回答本轮需求。\n历史对话：\n" +
                json.dumps(self.messages, ensure_ascii=False) + "\n本轮需求：\n" + prompt)
        if not resume:
            self.session = None
        self.identity = identity
        self.messages.append({"role": "user", "content": prompt})
        return resume, instruction

    def answer(self, text):
        if text:
            self.messages.append({"role": "assistant", "content": text})


def load_config():
    result = dict(DEFAULTS)
    if CONFIG.exists():
        result.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    return result


def save_config(config):
    DATA.mkdir(exist_ok=True)
    temporary = CONFIG.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CONFIG)


def discover_windows_program(program):
    """Explorer's PATH may omit CLI locations injected by a terminal profile."""
    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData/Local")
    roaming = Path(os.environ.get("APPDATA") or home / "AppData/Roaming")
    candidates = []
    if program.lower() in ("codex", "codex.exe"):
        bundle = local / "OpenAI/Codex/bin"
        candidates.append(bundle / "codex.exe")
        try:
            versions = list(bundle.glob("*/codex.exe"))
            versions.sort(key=lambda path: path.stat().st_mtime, reverse=True)
            candidates.extend(versions)
        except OSError:
            pass
        candidates.extend([home / ".local/bin/codex.exe", roaming / "npm/codex.ps1"])
    elif program.lower() in ("claude", "claude.exe"):
        candidates.extend([home / ".local/bin/claude.exe",
            roaming / "npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe",
            roaming / "npm/claude.ps1"])
    return next((str(path) for path in candidates if path.is_file()), None)


def resolve_program(program):
    program = os.path.expandvars(os.path.expanduser(program.strip().strip('"')))
    path = shutil.which(program) or (program if Path(program).is_file() else None)
    if not path and os.name == "nt":
        path = shutil.which(program + ".ps1")
        if not path:
            path = discover_windows_program(program)
    if not path:
        raise FileNotFoundError("找不到程序：" + program + "。请在设置中填写完整路径。")
    if str(path).lower().endswith((".ps1", ".cmd", ".bat")):
        native = Path(path).parent / "node_modules/@anthropic-ai/claude-code/bin/claude.exe"
        if native.exists() and Path(path).stem.lower() == "claude":
            return [str(native)]
    if str(path).lower().endswith(".ps1"):
        return ["powershell.exe", "-NoProfile", "-File", str(path)]
    if str(path).lower().endswith((".cmd", ".bat")):
        # npm shims accept no user text on the command line: the prompt goes via stdin.
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if "claude" in text.lower():
            script = Path(path).parent / "node_modules/@anthropic-ai/claude-code/cli.js"
            node = shutil.which("node")
            if script.exists() and node:
                return [node, str(script)]
        raise ValueError("请配置 .exe、.ps1 或 Claude npm 安装路径，不能直接使用此批处理文件。")
    return [str(path)]


def build_command(config, session=None):
    backend = config["backend"]
    command = list(resolve_program(config[backend + "_path"]))
    model = config.get(backend + "_model", "").strip()
    if backend == "codex":
        command += ["exec"]
        if session:
            command += ["resume", session]
        command += ["--json", "--skip-git-repo-check"]
        if not session:
            command += ["--sandbox", config["mode"]]
        if model:
            command += ["--model", model]
        command += ["-"]
    else:
        tools = "Read,Glob,Grep"
        if config["mode"] == "workspace-write":
            tools += ",Edit,Write"
        command += ["-p", "--output-format", "stream-json", "--verbose",
                    "--permission-mode", "dontAsk", "--tools", tools,
                    "--allowedTools", tools]
        if session:
            command += ["--resume", session]
        if model:
            command += ["--model", model]
    return command


def parse_event(backend, line):
    try:
        event = json.loads(line)
    except (ValueError, TypeError):
        return [("log", line)]
    result = []
    session = event.get("thread_id") if backend == "codex" else event.get("session_id")
    if session:
        result.append(("session", session))
    kind = event.get("type")
    if backend == "codex":
        item = event.get("item", {})
        if kind == "item.completed" and item.get("type") == "agent_message":
            result.append(("answer", item.get("text", "")))
        elif kind in ("item.started", "item.completed"):
            result.append(("log", item.get("command") or item.get("type", kind)))
        elif kind in ("error", "turn.failed"):
            result.append(("error", str(event.get("message") or event.get("error") or event)))
    else:
        if kind == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    result.append(("answer", block.get("text", "")))
                elif block.get("type") == "tool_use":
                    result.append(("log", "工具：" + block.get("name", "")))
        elif kind == "result":
            if event.get("is_error"):
                result.append(("error", str(event.get("errors") or event.get("result") or event)))
            else:
                result.append(("result", event.get("result", "")))
            if event.get("permission_denials"):
                result.append(("error", "部分操作需要权限，本次未执行：" + str(event["permission_denials"])))
    return result


class Runner:
    def __init__(self):
        self.events = queue.Queue()
        self.process = None
        self.cancelled = threading.Event()
        self.lock = threading.Lock()

    def start(self, config, target, prompt, session=None):
        self.cancelled.clear()
        threading.Thread(target=self._run, args=(dict(config), Path(target), prompt, session), daemon=True).start()

    def _run(self, config, target, prompt, session):
        try:
            cwd = target if target.is_dir() else target.parent
            instruction = ("选中目标：" + str(target) + "\n工作目录：" + str(cwd) +
                           "\n优先处理选中目标。不要修改工作目录之外的文件。\n用户需求：\n" + prompt)
            command = build_command(config, session)
            with self.lock:
                if self.cancelled.is_set():
                    return
                environment = dict(os.environ, PYTHONIOENCODING="utf-8")
                self.process = subprocess.Popen(command, cwd=str(cwd), stdin=subprocess.PIPE, env=environment,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                    errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                process = self.process
            def stderr_reader():
                for line in process.stderr:
                    self.events.put(("log", line.rstrip()))
            reader = threading.Thread(target=stderr_reader, daemon=True)
            reader.start()
            process.stdin.write(instruction)
            process.stdin.close()
            for line in process.stdout:
                for event in parse_event(config["backend"], line.rstrip()):
                    self.events.put(event)
            code = process.wait()
            reader.join(timeout=2)
            process.stdout.close()
            process.stderr.close()
            if code and not self.cancelled.is_set():
                self.events.put(("error", "进程退出码：" + str(code)))
        except Exception as exc:
            if not self.cancelled.is_set():
                self.events.put(("error", str(exc)))
        finally:
            with self.lock:
                self.process = None
            self.events.put(("done", "已取消" if self.cancelled.is_set() else "已结束"))

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            process = self.process
            if process and process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process.terminate()
