"""UI 色板、按钮样式与滚动条样式常量。"""

from PyQt6.QtGui import QColor


# 状态色。
CS = QColor(5, 150, 105)
CD = QColor(220, 38, 38)
CW = QColor(202, 138, 4)
CB = QColor(232, 232, 235)
CCARD = QColor(255, 255, 255, 248)


SB_QSS = (
    'QScrollBar:vertical{'
    'background:transparent;width:7px;margin:3px 1px;'
    '}'
    'QScrollBar::handle:vertical{'
    'background:rgba(24,24,27,0.13);border-radius:3px;min-height:34px;'
    '}'
    'QScrollBar::handle:vertical:hover{'
    'background:rgba(16,163,127,0.38);'
    '}'
    'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}'
    'QScrollBar:horizontal{height:0;}'
)


def _button_style(
    background: str,
    foreground: str,
    border: str = 'transparent',
    hover_background: str = '',
    pressed_background: str = '',
) -> str:
    """生成统一的主按钮 QSS。"""

    hover = hover_background or background
    pressed = pressed_background or hover
    return (
        'QPushButton{'
        f'background:{background};color:{foreground};border:1px solid {border};'
        'border-radius:9px;padding:5px 13px;font-size:11px;font-weight:650;'
        "font-family:'Microsoft YaHei UI','Segoe UI Variable','Segoe UI';"
        '}'
        f'QPushButton:hover{{background:{hover};}}'
        f'QPushButton:pressed{{background:{pressed};padding-top:6px;padding-bottom:4px;}}'
        'QPushButton:disabled{'
        'background:#F4F4F5;color:#B4B4BC;border-color:#ECECEF;'
        '}'
    )


BP = _button_style('#18181B', '#FFFFFF', '#18181B', '#27272A', '#09090B')
BD = _button_style('#FFF7F7', '#C93636', '#F1C9C9', '#FFF0F0', '#FCE7E7')
BS = _button_style('#F0FBF7', '#087D63', '#BDE8DA', '#E6F8F1', '#DDF4EB')
BG = _button_style('#FFFFFF', '#52525B', '#E4E4E7', '#F7F7F8', '#F1F1F3')
BCR = _button_style('#DC2626', '#FFFFFF', '#DC2626', '#C81E1E', '#B91C1C')

BCL = (
    'QPushButton{'
    'background:transparent;color:#71717A;border:none;font-size:14px;'
    'border-radius:8px;padding:0;'
    '}'
    'QPushButton:hover{background:#FEE2E2;color:#DC2626;}'
)
BWC = (
    'QPushButton{'
    'background:transparent;color:#71717A;border:none;font-size:12px;'
    'border-radius:8px;padding:0;'
    '}'
    'QPushButton:hover{background:#F4F4F5;color:#18181B;}'
)


# 状态文本到 Badge 模式的默认映射。
SM = {
    '已全部关闭': 'on',
    '已还原Win10': 'on',
    '未感染': 'on',
    '已清理': 'on',
    '已关闭': 'on',
    '已禁用': 'on',
    '已卸载': 'on',
    '高性能': 'on',
    '卓越性能': 'on',
    '已设置': 'on',
    '已暂停': 'on',
    '已全部开放': 'on',
    '已左对齐': 'on',
    '此电脑': 'on',
    '已启用': 'on',
    '已隐藏': 'on',
    '运行中': 'w',
    '已开启': 'w',
    '已停止': 'w',
    '未设置': 'w',
    '未暂停': 'w',
    '全部开启': 'w',
    '部分': 'w',
    '隐藏': 'w',
    '平衡': 'w',
    '节能': 'w',
    '居中': 'w',
    '主页': 'w',
    '默认': 'w',
    '未启用': 'w',
    '待重启': 'w',
    '未验证': 'w',
    '未加密': 'on',
    '自定义': 'w',
    '未找到': 'w',
    '未安装': 'on',
    '系统保留': 'w',
    '检测受限': 'w',
    '已显示': 'w',
    '压缩中': 'w',
    '检测失败': 'off',
    '已感染': 'off',
    '发现': 'off',
}

# Backwards-compatible private alias for any internal code that still imports it.
_bs = _button_style
