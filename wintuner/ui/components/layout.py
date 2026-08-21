"""页面分组、双栏布局、页头、滚动区与工具栏。"""

from __future__ import annotations

import os

import re

from PyQt6.QtCore import Qt

from PyQt6.QtGui import QPixmap

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from wintuner.core.paths import candidate_base_dirs

from wintuner.ui.styles import SB_QSS

from .primitives import _btn, _lbl


class SectionHeader:
    __slots__ = ('title', 'icon')

    def __init__(self, title):
        self.title = title
        self.icon = self._icon_for(title)

    @staticmethod
    def _icon_for(t):
        m = re.search('[A-Za-z0-9]', str(t or ''))
        return m.group(0).upper() if m else '·'


class SectionSeparator:
    __slots__ = ()


class SectionPanel(QFrame):

    def __init__(self, title, icon, parent=None):
        super().__init__(parent)
        self.weight = 1
        self.setObjectName('SectionPanel')
        self.setStyleSheet(
            'QFrame#SectionPanel{background:#FAFAFB;border:1px solid #ECECEF;border-radius:13px;}',
        )
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(10, 10, 10, 10)
        self.layout_.setSpacing(7)
        row = QHBoxLayout()
        ic = QLabel(icon)
        ic.setFixedSize(24, 24)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet(
            'QLabel{color:#087D63;background:#ECFDF5;border:1px solid #D7F0E8;border-radius:7px;font-size:10px;font-weight:800;}',
        )
        row.addWidget(ic)
        tl = _lbl(title, '#52525B', 10, True)
        tl.setStyleSheet(tl.styleSheet() + 'letter-spacing:1.2px;')
        row.addWidget(tl)
        row.addStretch()
        self.layout_.addLayout(row)

    def add_content(self, w):
        self.layout_.addWidget(w)
        self.weight += max(1, int(max(40, w.minimumHeight()) / 55))

    def add_spacing(self, v):
        self.layout_.addSpacing(min(8, max(0, int(v / 2))))


class DashboardColumns:
    """将多个功能分组按权重分配到双栏布局。"""

    def __init__(self, parent):
        self._root = QVBoxLayout(parent)
        self._root.setContentsMargins(22, 2, 22, 20)
        self._root.setSpacing(8)
        self._pre = QVBoxLayout()
        self._pre.setSpacing(10)
        self._root.addLayout(self._pre)
        cols = QWidget()
        cols.setAutoFillBackground(False)
        hl = QHBoxLayout(cols)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        self._cols = []
        for _ in range(2):
            v = QVBoxLayout()
            v.setSpacing(12)
            v.setAlignment(Qt.AlignmentFlag.AlignTop)
            self._cols.append(v)
            hl.addLayout(v, 1)
        self._root.addWidget(cols)
        self._pending = None
        self._weights = [0, 0]
        self._finished = False

    def _finalize(self):
        if not self._pending:
            return
        idx = 0 if self._weights[0] <= self._weights[1] else 1
        self._cols[idx].addWidget(self._pending)
        self._weights[idx] += self._pending.weight
        self._pending = None

    def addWidget(self, w, *args):
        if isinstance(w, SectionHeader):
            self._finalize()
            self._pending = SectionPanel(w.title, w.icon)
            return
        if isinstance(w, SectionSeparator):
            return
        if self._pending:
            self._pending.add_content(w)
        else:
            self._pre.addWidget(w)

    def addSpacing(self, v):
        if self._pending:
            self._pending.add_spacing(v)
        else:
            self._pre.addSpacing(v)

    def addStretch(self, *args):
        self._finalize()
        if not self._finished:
            for col in self._cols:
                col.addStretch(1)
            self._finished = True


class MascotHeader(QWidget):
    ASSET_NAME = 'gpt.png'
    EXTRA_NAMES = ()
    _SOURCE_CACHE = {}
    _SCALED_CACHE = {}
    _RESOLVED_PATH = ''

    def __init__(self, title, subtitle, eyebrow, stats, parent=None):
        super().__init__(parent)
        self._source = None
        self._asset_path_value = ''
        self._last_asset_key = None
        self.setObjectName('MascotHeader')
        self.setStyleSheet(
            'QWidget#MascotHeader{background:#FFFFFF;border:1px solid #ECECEF;border-radius:14px;}',
        )
        self.setMinimumHeight(178)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 12, 22, 10)
        lay.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(5)
        ey = _lbl(eyebrow, '#087D63', 10, True)
        ey.setStyleSheet(ey.styleSheet() + 'letter-spacing:1.0px;')
        left.addWidget(ey)
        left.addWidget(_lbl(title, '#18181B', 22, True))
        sl = _lbl(subtitle, '#71717A', 11)
        sl.setWordWrap(True)
        left.addWidget(sl)
        left.addStretch()
        lay.addLayout(left, 1)
        self.image = QLabel()
        self.image.setMinimumSize(420, 138)
        self.image.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self.image.setStyleSheet('background:transparent;')
        lay.addWidget(self.image, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self._load_asset()
        self._refresh_asset()

    def _asset_candidates(self):
        paths = []
        for base in candidate_base_dirs():
            for name in (self.ASSET_NAME,) + self.EXTRA_NAMES:
                for rel in (('ico', name), (name,)):
                    p = os.path.join(base, *rel)
                    if p not in paths:
                        paths.append(p)
        return paths

    def _asset_file(self):
        cached = self.__class__._RESOLVED_PATH
        if cached and os.path.exists(cached):
            return cached
        for p in self._asset_candidates():
            if os.path.exists(p):
                self.__class__._RESOLVED_PATH = p
                return p
        return ''

    def _load_asset(self):
        path = self._asset_file()
        self._asset_path_value = path
        if not path:
            self._source = None
            return
        px = self._SOURCE_CACHE.get(path)
        if px is None:
            px = QPixmap(path)
            if px.isNull():
                self._source = None
                return
            self._SOURCE_CACHE[path] = px
        self._source = px

    def showEvent(self, event):
        super().showEvent(event)
        if self._source is None:
            self._load_asset()
        self._refresh_asset()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_asset()

    def _refresh_asset(self):
        if self._source:
            h = min(168, max(136, self.height() - 12))
            dpr = max(1.0, float(self.devicePixelRatioF()))
            key = (self._asset_path_value, h, round(dpr, 2))
            if key != self._last_asset_key:
                scaled = self._SCALED_CACHE.get(key)
                if scaled is None:
                    scaled = self._source.scaledToHeight(
                        max(1, int(round(h * dpr))),
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    scaled.setDevicePixelRatio(dpr)
                    if len(self._SCALED_CACHE) >= 24:
                        self._SCALED_CACHE.clear()
                    self._SCALED_CACHE[key] = scaled
                self.image.setPixmap(scaled)
                self._last_asset_key = key
            self.image.show()
            return
        self.image.clear()
        self.image.hide()


def _scroll(cw):
    sc = QScrollArea()
    sc.setWidgetResizable(True)
    sc.setFrameShape(QFrame.Shape.NoFrame)
    sc.setAutoFillBackground(False)
    sc.setStyleSheet(f'QScrollArea,QAbstractScrollArea{{background:transparent;border:none;}}{SB_QSS}')
    sc.viewport().setAutoFillBackground(False)
    sc.viewport().setStyleSheet('background:transparent;')
    cw.setAutoFillBackground(False)
    cw.setStyleSheet('background:transparent;')
    sc.setWidget(cw)
    return sc


def _gl(t):
    return SectionHeader(t)


def _sep():
    return SectionSeparator()


def _page_header(title, subtitle, eyebrow, stats=None):
    w = QWidget()
    w.setAutoFillBackground(False)
    l = QVBoxLayout(w)
    l.setContentsMargins(18, 8, 18, 4)
    l.addWidget(MascotHeader(title, subtitle, eyebrow, stats or []))
    return w


def _toolbar(items):
    w = QWidget()
    w.setAutoFillBackground(False)
    l = QHBoxLayout(w)
    l.setContentsMargins(22, 0, 22, 7)
    l.setSpacing(8)
    for t, s, fn in items:
        l.addWidget(_btn(t, s, fn))
    l.addStretch()
    return w
