"""窗口侧栏、标题栏和导航项。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF, pyqtSignal

from PyQt6.QtGui import QColor, QFont, QPainter, QPalette

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wintuner.core.admin import is_admin

from wintuner.ui.styles import BCL, BWC

from .primitives import _lbl


class SidePanel(QFrame):

    # --------------------------------------------------------------------
    # 基础窗口组件
    # --------------------------------------------------------------------
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName('SidePanel')
        self.setStyleSheet('QFrame#SidePanel{background:#FBFBFC;border:none;border-right:1px solid #E8E8EB;}')


class TitleBar(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setObjectName('TitleBar')
        self.setStyleSheet('QWidget#TitleBar{background:#FFFFFF;border-bottom:1px solid #ECECEF;}')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 8, 0)
        lay.setSpacing(9)
        mark = QLabel('W')
        mark.setFixedSize(30, 30)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet(
            'QLabel{'
            'background:#18181B;color:#FFFFFF;border:none;border-radius:8px;'
            "font-family:'Segoe UI','Microsoft YaHei UI';"
            'font-size:13px;font-weight:800;'
            '}'
        )
        lay.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)
        names = QVBoxLayout()
        names.setContentsMargins(0, 2, 0, 0)
        names.setSpacing(0)
        names.addWidget(_lbl('WinTuner', '#18181B', 14, True))
        names.addWidget(_lbl('开源 Windows 性能优化工具 · By Liumang', '#8A8A93', 10))
        lay.addLayout(names)
        lay.addStretch()
        adm = QLabel('●  ADMIN' if is_admin() else '●  LIMITED')
        adm.setFixedHeight(30)
        adm.setMinimumWidth(84)
        adm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_admin():
            admin_qss = (
                'QLabel{'
                'color:#087D63;background:#F5FCF9;border:1px solid #CDEDE3;'
                'border-radius:15px;padding:0 12px;font-size:10px;font-weight:700;'
                '}'
            )
        else:
            admin_qss = (
                'QLabel{'
                'color:#B45309;background:#FFFCF3;border:1px solid #F4DE9B;'
                'border-radius:15px;padding:0 12px;font-size:10px;font-weight:700;'
                '}'
            )
        adm.setStyleSheet(admin_qss)
        lay.addWidget(adm, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(9)
        bm = QPushButton('─')
        bm.setStyleSheet(BWC)
        bm.setFixedSize(38, 32)
        bm.clicked.connect(lambda: self.window().showMinimized())
        lay.addWidget(bm, 0, Qt.AlignmentFlag.AlignVCenter)
        bc = QPushButton('✕')
        bc.setStyleSheet(BCL)
        bc.setFixedSize(38, 32)
        bc.clicked.connect(lambda: self.window().close())
        lay.addWidget(bc, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            try:
                self.window().windowHandle().startSystemMove()
            except Exception:
                pass

    def mouseDoubleClickEvent(self, e):
        pass


class NavIcon(QLabel):
    _BG_OFF = QColor(239, 239, 241)
    _BG_ON = QColor(221, 247, 238)
    _FG_OFF = QColor(82, 82, 91)
    _FG_ON = QColor(0, 154, 120)
    _RECT = QRectF(0, 0, 38, 38)

    def __init__(self, text, font, parent=None):
        super().__init__(text, parent)
        self._active = False
        self.setFixedSize(38, 38)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setFont(font)
        self.setStyleSheet('background:transparent;border:none;')
        self._sync_palette()

    def _sync_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.WindowText, self._FG_ON if self._active else self._FG_OFF)
        self.setPalette(pal)

    def set_active(self, value):
        value = bool(value)
        if value == self._active:
            return
        self._active = value
        self._sync_palette()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._BG_ON if self._active else self._BG_OFF)
        p.drawRoundedRect(self._RECT, 10, 10)
        p.end()
        super().paintEvent(event)


class NavItem(QFrame):
    clicked = pyqtSignal()
    META = {
        '服务管理': ('S', '后台服务与启动类型'),
        '系统设置': ('W', '性能、电源与设备'),
        '高级设置': ('A', '安全、遥测与隐私'),
        '应用管理': ('P', '预装应用清理'),
        '装机软件': ('I', '常用软件官方下载'),
    }
    _FONTS = None
    _BG_IDLE = QColor(251, 251, 252)
    _BG_HOVER = QColor(243, 244, 244)
    _BG_ACTIVE = QColor(234, 248, 244)
    _TITLE = QColor(39, 39, 42)
    _TITLE_ACTIVE = QColor(24, 24, 27)
    _CAPTION = QColor(146, 146, 155)
    _CAPTION_ACTIVE = QColor(0, 154, 120)

    @classmethod
    def _fonts(cls):
        if cls._FONTS is None:
            title = QFont('Microsoft YaHei UI')
            title.setPointSizeF(10.5)
            title.setWeight(QFont.Weight.Medium)
            title.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            caption = QFont('Microsoft YaHei UI')
            caption.setPointSizeF(8.5)
            caption.setWeight(QFont.Weight.Normal)
            caption.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            icon = QFont('Segoe UI')
            icon.setPointSizeF(10.0)
            icon.setWeight(QFont.Weight.Medium)
            icon.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            cls._FONTS = (title, caption, icon)
        return cls._FONTS

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.label = label
        self.icon, self.caption = self.META.get(label, ('•', ''))
        self._active = False
        self._hover = False
        self._paint_rect = QRectF()
        self.setFixedHeight(58)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 5, 10, 5)
        lay.setSpacing(11)
        title_font, caption_font, icon_font = self._fonts()
        self.icon_box = NavIcon(self.icon, icon_font, self)
        self.icon_box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.icon_box)
        tx = QVBoxLayout()
        tx.setSpacing(0)
        tx.setContentsMargins(0, 1, 0, 1)
        self.title_label = QLabel(label)
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet('background:transparent;border:none;')
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        tx.addWidget(self.title_label)
        self.caption_label = QLabel(self.caption)
        self.caption_label.setTextFormat(Qt.TextFormat.PlainText)
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.caption_label.setFont(caption_font)
        self.caption_label.setStyleSheet('background:transparent;border:none;')
        self.caption_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        tx.addWidget(self.caption_label)
        lay.addLayout(tx, 1)
        self._sync_colors()

    @staticmethod
    def _set_color(label, color):
        pal = label.palette()
        pal.setColor(QPalette.ColorRole.WindowText, color)
        label.setPalette(pal)

    def _sync_colors(self):
        self.icon_box.set_active(self._active)
        self._set_color(self.title_label, self._TITLE_ACTIVE if self._active else self._TITLE)
        self._set_color(self.caption_label, self._CAPTION_ACTIVE if self._active else self._CAPTION)
        self.update()

    def set_active(self, value):
        value = bool(value)
        if value == self._active:
            return
        self._active = value
        self._sync_colors()

    def enterEvent(self, e):
        if not self._hover:
            self._hover = True
            self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self._hover:
            self._hover = False
            self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._paint_rect = QRectF(self.rect())

    def paintEvent(self, event):
        if self._paint_rect.isNull():
            self._paint_rect = QRectF(self.rect())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._BG_ACTIVE if self._active else self._BG_HOVER if self._hover else self._BG_IDLE)
        p.drawRoundedRect(self._paint_rect, 12, 12)
