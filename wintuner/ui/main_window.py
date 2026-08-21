"""主窗口、侧边导航、页面懒加载和窗口生命周期管理。"""

import ctypes
from datetime import datetime
from functools import partial
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QColor, QTextCharFormat
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from wintuner.core.admin import is_admin
from wintuner.core.runtime import _pending_mutations
from wintuner.ui.background import BackgroundHost
from wintuner.ui.pages import ServicesPage, SystemPage, AdvancedPage, AppRemovalPage, InstallSoftwarePage
from wintuner.ui.styles import BG, SB_QSS
from wintuner.ui.widgets import NavItem, SidePanel, TitleBar, _btn, _lbl


class LogPanel(QFrame):
    """带缓冲刷新的操作日志面板，避免频繁 UI 重绘。"""
    EXPANDED_HEIGHT = 154
    COLLAPSED_HEIGHT = 40
    _TIME_FMT = None
    _MSG_FMTS = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buf = []
        self._empty = True
        self._expanded = True
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._flush)
        self.setFixedHeight(self.EXPANDED_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName('LogPanel')
        self.setStyleSheet('QFrame#LogPanel{background:#FBFBFC;border:1px solid #E8E8EB;border-radius:12px;}')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        hdr = QWidget()
        hdr.setFixedHeight(38)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 0, 10, 0)
        dot = QLabel('●')
        dot.setStyleSheet('color:#10A37F;font-size:9px;background:transparent;')
        hl.addWidget(dot)
        ll = QLabel('OPERATION LOG')
        ll.setStyleSheet(
            "color:#71717A;font-size:10px;font-weight:700;letter-spacing:1.2px;font-family:'Cascadia Code','Consolas';background:transparent;",
        )
        hl.addWidget(ll)
        hl.addStretch()
        self.fold = _btn('收起', BG, self._toggle)
        self.fold.setFixedHeight(27)
        hl.addWidget(self.fold)
        cl = _btn('清空', BG, self._clear)
        cl.setFixedHeight(27)
        hl.addWidget(cl)
        root.addWidget(hdr)
        self.le = QPlainTextEdit()
        self.le.setReadOnly(True)
        self.le.setUndoRedoEnabled(False)
        self.le.document().setMaximumBlockCount(800)
        self.le.setAutoFillBackground(False)
        self.le.setStyleSheet(
            f"QPlainTextEdit{{background:transparent;border:none;padding:5px 14px 12px 14px;color:#3F3F46;font-size:11px;font-family:'Cascadia Code','Consolas';}}{SB_QSS}",
        )
        root.addWidget(self.le, 1)
        if self.__class__._TIME_FMT is None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(161, 161, 170))
            self.__class__._TIME_FMT = fmt

    @classmethod
    def _msg_format(cls, color):
        fmt = cls._MSG_FMTS.get(color)
        if fmt is None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            cls._MSG_FMTS[color] = fmt
        return fmt

    def _toggle(self):
        self._expanded = not self._expanded
        self.fold.setText('收起' if self._expanded else '展开')
        self.le.setVisible(self._expanded)
        self.setFixedHeight(self.EXPANDED_HEIGHT if self._expanded else self.COLLAPSED_HEIGHT)

    def _clear(self):
        self.le.clear()
        self._empty = True
        self._buf.clear()

    def _flush(self):
        if not self._buf:
            return
        lines, self._buf = (self._buf, [])
        self.le.setUpdatesEnabled(False)
        cursor = self.le.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        for i, (ts, msg, color) in enumerate(lines):
            if not self._empty or i > 0:
                cursor.insertBlock()
            cursor.insertText(f'[{ts}] ', self._TIME_FMT)
            cursor.insertText(msg, self._msg_format(color))
        self._empty = False
        self.le.setTextCursor(cursor)
        self.le.setUpdatesEnabled(True)
        sb = self.le.verticalScrollBar()
        sb.setValue(sb.maximum())

    def append(self, msg):
        ts = datetime.now().strftime('%H:%M:%S')
        if '✓' in msg or '完成' in msg:
            color = '#087D63'
        elif '✗' in msg or '失败' in msg:
            color = '#C93636'
        elif '▶' in msg:
            color = '#18181B'
        elif '⏳' in msg:
            color = '#B7791F'
        elif '═' in msg:
            color = '#D4D4D8'
        else:
            color = '#52525B'
        self._buf.append((ts, str(msg), color))
        if not self._timer.isActive():
            self._timer.start()


class MainWindow(QMainWindow):
    """WinTuner 主窗口；按需创建页面并协调检测与退出。"""
    RM = 6
    _E_NONE = Qt.Edge(0)
    _E_L = Qt.Edge.LeftEdge
    _E_R = Qt.Edge.RightEdge
    _E_T = Qt.Edge.TopEdge
    _E_B = Qt.Edge.BottomEdge
    _E_LT = Qt.Edge.LeftEdge | Qt.Edge.TopEdge
    _E_RT = Qt.Edge.RightEdge | Qt.Edge.TopEdge
    _E_LB = Qt.Edge.LeftEdge | Qt.Edge.BottomEdge
    _E_RB = Qt.Edge.RightEdge | Qt.Edge.BottomEdge
    _CURSORS = {
        _E_LT: Qt.CursorShape.SizeFDiagCursor,
        _E_RB: Qt.CursorShape.SizeFDiagCursor,
        _E_RT: Qt.CursorShape.SizeBDiagCursor,
        _E_LB: Qt.CursorShape.SizeBDiagCursor,
        _E_L: Qt.CursorShape.SizeHorCursor,
        _E_R: Qt.CursorShape.SizeHorCursor,
        _E_T: Qt.CursorShape.SizeVerCursor,
        _E_B: Qt.CursorShape.SizeVerCursor,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle('WinTuner')
        self.setMinimumSize(1060, 640)
        self.resize(1240, 760)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet('QMainWindow{background:#F8F8F9;}')
        self.setMouseTracking(True)
        self._anim_done = False
        self._resize_cursor = Qt.CursorShape.ArrowCursor
        self._page_detected = [False, False, False, False, False]
        self._pages = [None, None, None, None, None]
        self._placeholders = []
        self._setup_ui()
        self._navs[0].set_active(True)
        self._ensure_page(0)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(self.winId()),
                33,
                ctypes.byref(ctypes.c_int(2)),
                ctypes.sizeof(ctypes.c_int),
            )
        except Exception:
            pass
        if not self._anim_done:
            self._anim_done = True
            QTimer.singleShot(120, self._startup_detect)

    def _setup_ui(self):
        self.bgw = BackgroundHost()
        self.setCentralWidget(self.bgw)
        root = QVBoxLayout(self.bgw.content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(TitleBar())
        body = QWidget()
        body.setAutoFillBackground(False)
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        sb = SidePanel()
        sb.setFixedWidth(220)
        sl = QVBoxLayout(sb)
        sl.setContentsMargins(10, 14, 10, 14)
        sl.setSpacing(4)
        cap = _lbl('CONTROL CENTER', '#A1A1AA', 9, True)
        cap.setContentsMargins(12, 0, 0, 4)
        sl.addWidget(cap)
        self._navs = []
        for label in ('服务管理', '系统设置', '高级设置', '应用管理', '装机软件'):
            ni = NavItem(label)
            ni.clicked.connect(partial(self.switch_page, len(self._navs)))
            self._navs.append(ni)
            sl.addWidget(ni)
        sl.addStretch()
        vl = _lbl(
            'WinTuner  ·  local performance console\n' + ('Administrator privileges' if is_admin() else 'Limited privileges'),
            '#A1A1AA',
            8,
        )
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.setContentsMargins(0, 3, 0, 0)
        sl.addWidget(vl)
        bl.addWidget(sb)
        right = QWidget()
        right.setAutoFillBackground(False)
        right.setStyleSheet('background:transparent;')
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.stack = QStackedWidget()
        self.stack.setAutoFillBackground(False)
        self.stack.setStyleSheet('QStackedWidget{background:transparent;}')
        self.log = LogPanel()
        self._logger = self.log.append
        for _ in range(5):
            ph = QWidget()
            ph.setAutoFillBackground(False)
            ph.setStyleSheet('background:transparent;')
            self._placeholders.append(ph)
            self.stack.addWidget(ph)
        rl.addWidget(self.stack, 1)
        lh = QWidget()
        lh.setAutoFillBackground(False)
        lh.setStyleSheet('background:transparent;')
        ll = QVBoxLayout(lh)
        ll.setContentsMargins(22, 0, 22, 14)
        ll.addWidget(self.log)
        rl.addWidget(lh)
        bl.addWidget(right, 1)
        root.addWidget(body, 1)
        self._gradient = self.bgw.gradient

    def _ensure_page(self, idx):
        page = self._pages[idx]
        if page is not None:
            return page
        factories = (ServicesPage, SystemPage, AdvancedPage, AppRemovalPage, InstallSoftwarePage)
        page = factories[idx](self._logger)
        page.setAutoFillBackground(False)
        page.setStyleSheet('background:transparent;')
        old = self.stack.widget(idx)
        was_current = self.stack.currentIndex() == idx
        self.stack.removeWidget(old)
        self.stack.insertWidget(idx, page)
        old.deleteLater()
        self._pages[idx] = page
        if was_current:
            self.stack.setCurrentIndex(idx)
        return page

    def switch_page(self, idx):
        if self.stack.currentIndex() == idx and self._pages[idx] is not None:
            return
        page = self._ensure_page(idx)
        self.stack.setCurrentIndex(idx)
        for i, n in enumerate(self._navs):
            n.set_active(i == idx)
        if not self._page_detected[idx]:
            self._page_detected[idx] = True
            QTimer.singleShot(80, page.detect_all)

    def _startup_detect(self):
        self.log.append('═' * 48)
        self.log.append('WinTuner 启动完成')
        self.log.append(f"权限: {('管理员' if is_admin() else '⚠ 非管理员 (功能受限)')}")
        self.log.append('═' * 48)
        page = self._ensure_page(0)
        self._page_detected[0] = True
        page.detect_all()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.bgw.pause()
            else:
                self.bgw.resume()

    def closeEvent(self, event):
        if _pending_mutations() > 0:
            QMessageBox.warning(self, '系统操作进行中', '仍有高权限系统修改正在执行。为避免留下半完成状态，请等待当前操作完成后再关闭 WinTuner。')
            event.ignore()
            return
        super().closeEvent(event)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            try:
                eg = self._edges(e.position().toPoint())
                if eg != self._E_NONE:
                    wh = self.windowHandle()
                    if wh:
                        wh.startSystemResize(eg)
            except Exception:
                pass

    def mouseMoveEvent(self, e):
        try:
            cur = self._CURSORS.get(self._edges(e.position().toPoint()), Qt.CursorShape.ArrowCursor)
        except Exception:
            cur = Qt.CursorShape.ArrowCursor
        if cur != self._resize_cursor:
            self._resize_cursor = cur
            self.setCursor(cur)

    def _edges(self, pos):
        m = self.RM
        x = pos.x()
        y = pos.y()
        w = self.width()
        h = self.height()
        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m
        if left:
            return self._E_LT if top else self._E_LB if bottom else self._E_L
        if right:
            return self._E_RT if top else self._E_RB if bottom else self._E_R
        if top:
            return self._E_T
        if bottom:
            return self._E_B
        return self._E_NONE
