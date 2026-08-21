"""装机软件页面。"""

import re
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from wintuner.software_installation import SOFTWARE_ITEMS
from wintuner.ui.widgets import Card, DashboardColumns, _gl, _lbl, _page_header, _scroll, _sep, _tip, _btn
from wintuner.ui.styles import BP


class SoftwareLinkCard(Card):

    def __init__(self, name, desc, url, logger, parent=None):
        super().__init__(parent)
        self.name = name
        self.url = url
        self.logger = logger
        self.setMinimumHeight(78)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 11, 13, 11)
        lay.setSpacing(10)
        icon = QLabel()
        first = re.search('[A-Za-z0-9]', name)
        icon.setText(first.group(0).upper() if first else name[:1])
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "QLabel{background:#F4EEFF;color:#7557C8;border:1px solid #E6DBFF;border-radius:10px;font-family:'Segoe UI','Microsoft YaHei UI';font-size:11px;font-weight:700;}",
        )
        lay.addWidget(icon)
        info = QVBoxLayout()
        info.setSpacing(3)
        info.addWidget(_lbl(name, '#27272A', 12, True))
        dl = _lbl(desc, '#71717A', 10)
        dl.setWordWrap(True)
        info.addWidget(dl)
        ul = _lbl(url, '#9466B7', 9)
        ul.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.addWidget(ul)
        lay.addLayout(info, 1)
        btn = _btn('打开官网', BP, self._open)
        btn.setMinimumWidth(78)
        lay.addWidget(btn)

    def _open(self):
        target = QUrl.fromUserInput(self.url)
        ok = QDesktopServices.openUrl(target)
        self.logger(('▶ 已打开: ' if ok else '✗ 无法打开: ') + self.name + ('' if ok else f'  {self.url}'))


class InstallSoftwarePage(QWidget):
    """常用装机软件官方入口页面。"""
    ITEMS = tuple(((x.name, x.description, x.url) for x in SOFTWARE_ITEMS))

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.setAutoFillBackground(False)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_page_header('装机软件', '常用装机软件官方下载入口，点击按钮直接使用默认浏览器访问官方网站。', 'SOFTWARE / INSTALL'))
        ct = QWidget()
        ct.setAutoFillBackground(False)
        ct.setStyleSheet('background:transparent;')
        cl = DashboardColumns(ct)
        cl.addWidget(_gl('ESSENTIAL SOFTWARE'))
        cl.addWidget(_sep())
        for name, desc, url in self.ITEMS:
            cl.addWidget(SoftwareLinkCard(name, desc, url, logger))
            cl.addSpacing(3)
        cl.addWidget(_tip('下载软件时请核对浏览器地址栏域名，优先使用上方列出的官方页面。'))
        cl.addStretch()
        root.addWidget(_scroll(ct))

    def detect_all(self):
        self.logger('✓ 装机软件官方下载入口已就绪')
