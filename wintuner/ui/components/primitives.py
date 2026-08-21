"""基础视觉组件：卡片、按钮、状态徽章和常用构建辅助函数。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF

from PyQt6.QtGui import QColor, QPainter, QPalette, QPen

from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy

from wintuner.ui.styles import CB, CCARD, CD, CS, CW, SM


class Card(QFrame):
    _BG = CCARD
    _BG_H = QColor(253, 254, 254)
    _PEN = QPen(CB, 1)
    _PEN_H = QPen(QColor(198, 226, 218), 1)
    _ACCENT = QColor(16, 163, 127, 190)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hov = False
        self._bg_ov = None
        self._bd_pen = None
        self._paint_rect = QRectF()
        self._stripe_rect = QRectF()
        self.setAutoFillBackground(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)

    def _rebuild_geometry(self):
        self._paint_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        self._stripe_rect = QRectF(1, 16, 3, max(0, self.height() - 32))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rebuild_geometry()

    def set_special(self, bg, bd):
        self._bg_ov = bg
        self._bd_pen = QPen(bd or CB, 1)
        self.update()

    def enterEvent(self, e):
        if not self._hov:
            self._hov = True
            self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self._hov:
            self._hov = False
            self.update()
        super().leaveEvent(e)

    def paintEvent(self, event):
        if self._paint_rect.isNull():
            self._rebuild_geometry()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._bg_ov is not None:
            p.setPen(self._bd_pen or self._PEN)
            p.setBrush(self._bg_ov)
            p.drawRoundedRect(self._paint_rect, 12, 12)
            p.end()
            return
        p.setPen(self._PEN_H if self._hov else self._PEN)
        p.setBrush(self._BG_H if self._hov else self._BG)
        p.drawRoundedRect(self._paint_rect, 12, 12)
        if self._hov:
            p.fillRect(self._stripe_rect, self._ACCENT)


class ModernButton(QPushButton):

    def __init__(self, text, style, slot=None, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(style)
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        if slot:
            self.clicked.connect(slot)


class Badge(QLabel):
    _COLORS = {
        'on': (CS, QColor(CS.red(), CS.green(), CS.blue(), 20), QColor(CS.red(), CS.green(), CS.blue(), 56)),
        'off': (CD, QColor(CD.red(), CD.green(), CD.blue(), 20), QColor(CD.red(), CD.green(), CD.blue(), 56)),
        'w': (CW, QColor(CW.red(), CW.green(), CW.blue(), 20), QColor(CW.red(), CW.green(), CW.blue(), 56)),
        'n': (QColor(113, 113, 122), QColor(244, 244, 245), QColor(228, 228, 231)),
    }
    _PENS = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(84)
        self.setMaximumWidth(154)
        self.setFixedHeight(25)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setContentsMargins(8, 0, 8, 0)
        self.setStyleSheet(
            "QLabel{background:transparent;border:none;font-size:10px;font-weight:700;font-family:'Microsoft YaHei UI','Segoe UI';}",
        )
        if not self.__class__._PENS:
            self.__class__._PENS = {k: QPen(v[2], 1) for k, v in self._COLORS.items()}
        self._status = None
        self._mode = None
        self._bg = self._COLORS['n'][1]
        self._pen = self._PENS['n']
        self._paint_rect = QRectF()
        self.set_status('检测中...')

    @staticmethod
    def _mode_for(text, overrides):
        mode = (overrides or {}).get(text)
        if mode:
            return mode
        for key, value in SM.items():
            if key in text:
                return value
        return 'n'

    def set_status(self, text, overrides=None):
        mode = self._mode_for(text, overrides)
        if text == self._status and mode == self._mode:
            return
        self._status = text
        self._mode = mode
        fg, bg, _ = self._COLORS.get(mode, self._COLORS['n'])
        self._bg = bg
        self._pen = self._PENS.get(mode, self._PENS['n'])
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.WindowText, fg)
        self.setPalette(pal)
        self.setText(f'●  {text}')
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._paint_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

    def paintEvent(self, event):
        if self._paint_rect.isNull():
            self._paint_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(self._pen)
        p.setBrush(self._bg)
        p.drawRoundedRect(self._paint_rect, 12, 12)
        p.end()
        super().paintEvent(event)


def _btn(t, s, slot=None):
    return ModernButton(t, s, slot)


def _lbl(t, c='#52525B', sz=12, bold=False):
    l = QLabel(t)
    w = '700' if bold else '400'
    l.setStyleSheet(
        f"color:{c};font-size:{sz}px;font-weight:{w};font-family:'Microsoft YaHei UI','Segoe UI Variable','Segoe UI';background:transparent;",
    )
    return l
