"""稳定的窗口渐变背景。

此前版本使用 QOpenGLWidget + 自定义 Shader 绘制动态背景。该方案在部分
Windows 显卡驱动 / Qt 6 组合下会把整个顶层窗口切换到 OpenGL 合成路径，
页面大量重绘或切换时一旦底层驱动异常，Python 层无法捕获原生崩溃。

WinTuner 的背景只是装饰，因此这里改为纯 QWidget + QPainter 软件绘制。
视觉效果保持接近原版，但不再依赖 OpenGL 上下文、Shader、VBO 或定时刷新。
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PyQt6.QtWidgets import QWidget


class GradientWidget(QWidget):
    """轻量静态渐变背景，不参与鼠标事件和后台动画。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            rect = self.rect()
            gradient = QLinearGradient(0, 0, max(1, self.width()), max(1, self.height()))
            gradient.setColorAt(0.00, QColor(255, 250, 253))
            gradient.setColorAt(0.22, QColor(255, 247, 252))
            gradient.setColorAt(0.46, QColor(253, 234, 247))
            gradient.setColorAt(0.68, QColor(244, 232, 255))
            gradient.setColorAt(0.86, QColor(249, 244, 255))
            gradient.setColorAt(1.00, QColor(255, 255, 255))
            painter.fillRect(rect, gradient)
        finally:
            painter.end()

    def pause(self):
        """兼容旧 BackgroundHost 接口。"""

    def resume(self):
        """兼容旧 BackgroundHost 接口。"""


# 保留旧名字，避免外部代码若有引用时立即失效。
GradientGLWidget = GradientWidget


class BackgroundHost(QWidget):
    """背景与前景内容宿主。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(252, 247, 253))
        self.setPalette(palette)

        self.gradient = GradientWidget(self)
        self.content = QWidget(self)
        self.content.setAutoFillBackground(False)
        self.content.setStyleSheet('background:transparent;')

        self.gradient.lower()
        self.content.raise_()

    def resizeEvent(self, event):
        rect = self.rect()
        if self.gradient.geometry() != rect:
            self.gradient.setGeometry(rect)
        if self.content.geometry() != rect:
            self.content.setGeometry(rect)
        super().resizeEvent(event)

    def pause(self):
        self.gradient.pause()

    def resume(self):
        self.gradient.resume()
