# 召唤小爱

Windows 资源管理器右键 AI 助手。Python 3.9+ 标准库实现，无第三方 Python 依赖。

## 启动

```powershell
python app.py --target "D:\your-project"
```

也可以运行 `launch.ps1`，通过 pythonw 打开窗口而不显示终端。

默认昵称为“小爱”，右键菜单显示“召唤小爱”。伙伴有眨眼和思考动画。
召唤后显示无边框、透明背景的小猫和话语气泡。点击小猫或气泡展开输入框，
确认后输入框收起，在气泡中显示任务进度和答复；再次点击即可追问。
拖动小猫可移动它和气泡。长答复可在气泡中滚动查看。
右键小猫打开菜单：设置、允许修改（默认勾选）、清空对话、工作过程、停止任务和收起。
同一次召唤自动延续多轮对话。

独立设置界面可通过目录空白处右键的“小爱的设置…”、小猫右键的“设置…”，
或 `python app.py --settings` / `launch-settings.ps1` 打开。
可设置昵称、默认后端、程序路径、模型和默认是否禁止修改。
保存昵称后同步更新右键菜单；从独立设置窗口修改选项后重新召唤即可使用。

## 注册右键菜单

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-context-menu.ps1
```

仅修改当前用户注册表，无需管理员。支持单个文件、文件夹及目录空白处。
Windows 10 直接显示在右键菜单靠前的位置；Windows 11 中位于“显示更多选项”。
安装器会通知资源管理器刷新菜单。安装后请保持程序目录位置不变，移动后重新注册。

卸载：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-context-menu.ps1 -Uninstall
```

## 配置和任务

- 独立设置窗口配置默认 Claude Code / Codex、昵称、程序路径和模型。
- 小猫菜单的“允许修改”只影响本次召唤，不覆盖全局默认设置。
- 右键启动无需终端 PATH：自动查找 Codex 桌面应用附带的 CLI、Claude 本地及 npm 安装位置。
- 先在终端登录对应 CLI。本工具复用它的身份和配置，不存储密钥。
- 全局配置位于 `data/config.json`，任务记录为 `data/<时间戳>.json`。
- Ctrl+Enter 发送需求。同一窗口内后续输入自动使用明确 session ID 延续上下文。
- 后端未返回 session ID 时，自动携带当前窗口的文字对话历史继续。
- “新对话”清空当前窗口上下文；切换后端也开始新对话。
- 路径、模型或权限模式变化创建新的原生会话，同时携带文字对话历史。
- 用户需求经 stdin 传入，不拼接为 shell 命令。
- 任务失败不会自动切换后端。取消会停止进程树，不撤销已完成修改。

## 当前能力与限制

这是 CLI 驱动 MVP。支持进度事件、完整消息、当前窗口会话延续、取消和本地记录。
不支持托盘后台运行、跨窗口恢复、项目配置、多选、修改差异预览或自动撤销。
关闭窗口会取消任务。记录可能含文件内容与需求，请按自己的需求管理 `data`。

Codex 使用 `read-only` 或 `workspace-write` 沙箱；文件目标的工作目录为其所在目录。
写入模式允许修改整个工作目录，未提供单文件强制隔离。
Claude 只开放 Read/Glob/Grep（分析）或额外 Edit/Write（修改），不开放 Bash。
Claude 工具许可不是操作系统目录沙箱，读取可能涉及选中目录之外；仅用于可信目录。
本工具不会关闭已有项目 hooks 或重新隔离其副作用。
CLI 模式需要额外授权的操作会失败或被拒绝；本版本尚未实现交互审批。
输出是事件/消息级流式展示，并非逐 token 展示。
任意文件可作为目标，但复杂文档格式依赖后端实际能力。

## 验证

```powershell
python -m unittest discover -s tests -v
```

测试使用本地假后端，不调用付费 AI 服务。
