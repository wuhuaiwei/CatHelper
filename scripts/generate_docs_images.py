"""Generate clearly labelled SVG interface diagrams (not screenshots)."""
from html import escape
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / 'docs' / 'images'


def text(x, y, value, size=18, color='#514263', weight='normal'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(value)}</text>'


def rect(x, y, w, h, fill='white', stroke='none', radius=16):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def save(name, width, height, title, parts):
    DEST.mkdir(parents=True, exist_ok=True)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">'
           f'<title id="title">{escape(title)}</title>'
           '<g font-family="Microsoft YaHei UI, Microsoft YaHei, Noto Sans CJK SC, sans-serif">'
           + ''.join(parts) + '</g></svg>')
    (DEST / name).write_text(svg, encoding='utf-8')


def main():
    parts = [rect(0, 0, 1000, 330, '#FAF7FD', radius=24),
             text(32, 48, '从右键召唤，到继续追问', 26, weight='bold'),
             text(32, 78, 'CatHelper 操作流程示意', 14, '#93849F')]
    steps = [('01', '右键召唤', '文件 / 文件夹 / 空白处', '让小猫来到当前任务旁'),
             ('02', '写下需求', '点击小猫展开输入框', 'Enter 发送 · 组合键换行'),
             ('03', '查看答复', '消息可以选字与复制', '长文本按像素小步滚动'),
             ('04', '继续追问', '同一窗口保留对话上下文', '需要时切换允许修改')]
    for index, (number, title, first, second) in enumerate(steps):
        x = 28 + 244 * index
        parts += [rect(x, 108, 220, 184, 'white', '#E8DFF2'),
                  rect(x+16, 124, 38, 32, '#EEE5FA', radius=10),
                  text(x+23, 147, number, 17, '#9270CE', 'bold'),
                  text(x+16, 191, title, 22, weight='bold'),
                  text(x+16, 229, first, 14), text(x+16, 258, second, 13, '#93849F')]
    save('workflow.svg', 1000, 330, 'CatHelper：右键召唤、写下需求、查看答复、继续追问', parts)

    parts = [rect(0, 0, 1000, 720, '#F4EFF9', radius=24),
             text(34, 42, '伙伴设置 · 界面示意', 25, weight='bold'),
             text(34, 70, '示例内容，非实机截图；实际模型列表以 CLI 返回为准。', 15, '#93849F'),
             rect(28, 94, 614, 602, '#FAF7FD', '#DED0ED', 24),
             text(52, 124, '伙伴设置', 13, '#93849F'),
             rect(588, 106, 30, 28, '#EEE5FA', radius=9), text(597, 127, '×', 22, '#9270CE'),
             text(58, 178, '伙伴的小偏好', 28, weight='bold'),
             text(58, 206, '把每一点小习惯，调成喜欢的样子。', 15, '#93849F'),
             rect(50, 228, 570, 144, stroke='#EEE6F5', radius=22),
             text(70, 255, '01   认识你的伙伴', 15, '#A28AB6', 'bold'),
             rect(50, 388, 570, 222, stroke='#EEE6F5', radius=22),
             text(70, 417, '02   伙伴的 AI 魔法', 15, '#A28AB6', 'bold')]
    rows = [(292, '伙伴昵称', '小爱', False), (339, '伙伴图标大小', '中', True),
            (455, '默认 AI', 'codex', True), (502, 'Codex 程序', 'codex', False),
            (549, 'Codex 模型', '默认（跟随 CLI）', True)]
    for y, label, value, combo in rows:
        path = label.endswith('程序')
        parts += [text(70, y, label, 16), rect(222, y-26, 200 if path else 376, 38,
                                                  '#FCFAFF', '#E8E0F0', 10),
                  text(236, y, value, 16)]
        if combo:
            parts.append(text(574, y, '⌄', 19, '#9D82BE'))
        if path:
            parts += [rect(432, y-26, 78, 38, '#F1EAFB', radius=10),
                      text(454, y, '浏览', 16, '#7959A6'),
                      rect(520, y-26, 78, 38, '#F1EAFB', radius=10),
                      text(542, y, '测试', 16, '#7959A6')]
    parts += [text(70, 590, '权限设置', 16),
              rect(222, 564, 376, 38, '#FCFAFF', '#E8E0F0', 10),
              text(236, 590, '默认允许修改文件', 16), text(574, 590, '⌄', 19, '#9D82BE'),
              text(53, 657, '每次召唤，都更懂你一点。', 13, '#93849F'),
              rect(448, 630, 172, 43, '#9270CE', radius=15),
              text(487, 658, '保存小偏好', 17, 'white')]
    notes = [(151, '圆角窗口', '拖动标题移动，右下角缩放'),
             (287, '昵称与大小', '让伙伴拥有你喜欢的名字和尺寸'),
             (441, '只显示选中的 AI', '切换后保留各自路径与模型设置'),
             (539, '模型自动获取', '成功后启用下拉框，失败可悬浮查看'),
             (646, '打开设置时', '气泡暂时收起，草稿与显示状态保留')]
    for y, title, detail in notes:
        parts += [rect(672, y-27, 300, 78, 'white', radius=15),
                  text(690, y, title, 18, '#8062CB', 'bold'),
                  text(690, y+28, detail, 13, '#93849F')]
    save('settings.svg', 1000, 720, '伙伴设置选项与窗口操作示意图（非实机截图）', parts)


if __name__ == '__main__':
    main()
