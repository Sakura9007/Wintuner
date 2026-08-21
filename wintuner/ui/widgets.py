"""WinTuner UI 组件公共门面。

具体实现已经拆分到 :mod:`wintuner.ui.components`。保留本模块是为了让页面
导入保持稳定，也方便以后逐步迁移外部调用。
"""

from .components.actions import (
    ACard,
    MESSAGE_QSS,
    SvcCard,
    _ask,
    _detect_cards_batch,
    _info_card,
    _make_toggle,
    _tip,
    _warn_card,
)
from .components.layout import (
    DashboardColumns,
    MascotHeader,
    SectionHeader,
    SectionPanel,
    SectionSeparator,
    _gl,
    _page_header,
    _scroll,
    _sep,
    _toolbar,
)
from .components.navigation import NavIcon, NavItem, SidePanel, TitleBar
from .components.primitives import Badge, Card, ModernButton, _btn, _lbl

__all__ = [
    'ACard',
    'Badge',
    'Card',
    'DashboardColumns',
    'MESSAGE_QSS',
    'MascotHeader',
    'ModernButton',
    'NavIcon',
    'NavItem',
    'SectionHeader',
    'SectionPanel',
    'SectionSeparator',
    'SidePanel',
    'SvcCard',
    'TitleBar',
    '_ask',
    '_btn',
    '_detect_cards_batch',
    '_gl',
    '_info_card',
    '_lbl',
    '_make_toggle',
    '_page_header',
    '_scroll',
    '_sep',
    '_tip',
    '_toolbar',
    '_warn_card',
]
