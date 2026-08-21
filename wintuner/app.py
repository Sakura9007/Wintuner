"""应用启动、Qt 初始化、单实例与退出清理。"""

from __future__ import annotations

import os
import sys
import traceback

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QMessageBox

from wintuner import __version__
from wintuner.core.admin import (
    ORIGIN_PROFILE_ARG,
    _acquire_single_instance,
    _release_single_instance,
    require_admin,
)
from wintuner.core.paths import LOG_PATH, write_error_log
from wintuner.core.runtime import shutdown_pools
from wintuner.ui.main_window import MainWindow


APP_QSS = (
    'QToolTip{'
    'background:#18181B;color:#FFFFFF;border:1px solid #3F3F46;'
    'font-size:10px;border-radius:7px;padding:5px 8px;'
    '}'
    "QPushButton{font-family:'Microsoft YaHei UI','Segoe UI';}"
    'QMessageBox{background:#FFFFFF;}'
    'QMessageBox QLabel{'
    "color:#27272A;font-size:12px;font-family:'Microsoft YaHei UI';"
    '}'
    'QMessageBox QPushButton{'
    'background:#FFFFFF;color:#3F3F46;border:1px solid #E4E4E7;'
    'border-radius:8px;padding:6px 15px;min-width:64px;'
    '}'
    'QMessageBox QPushButton:hover{background:#F4F4F5;}'
)


def _shutdown_workers() -> None:
    shutdown_pools()
    _release_single_instance()


def _configure_palette(app: QApplication) -> None:
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(247, 247, 248))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(250, 250, 251))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(24, 24, 27))
    palette.setColor(QPalette.ColorRole.Text, QColor(24, 24, 27))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(24, 24, 27))
    palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(24, 24, 27))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(16, 163, 127))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def _origin_user_matches_current_user() -> bool:
    if not ORIGIN_PROFILE_ARG:
        return True

    current = os.environ.get('USERPROFILE', '')
    origin_path = os.path.normcase(os.path.abspath(ORIGIN_PROFILE_ARG))
    current_path = os.path.normcase(os.path.abspath(current))
    return origin_path == current_path


def main() -> None:
    require_admin()
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

    app = QApplication(sys.argv)
    app.setApplicationName('WinTuner')
    app.setApplicationDisplayName('WinTuner')
    app.setApplicationVersion(__version__)

    # HKCU 优化必须落在启动程序的原用户上，不能因 UAC 凭据切换到另一个账户。
    if not _origin_user_matches_current_user():
        QMessageBox.critical(
            None,
            'WinTuner',
            '检测到当前提升后的管理员账户与启动 WinTuner 的 Windows 用户不是同一账户。\n\n'
            '为避免把 HKCU 优化应用到错误用户，WinTuner 已拒绝运行。'
            '请使用属于管理员组的同一账户启动并通过 UAC 提升。',
        )
        return

    if not _acquire_single_instance():
        QMessageBox.information(
            None,
            'WinTuner',
            'WinTuner 已经在当前 Windows 会话中运行。',
        )
        return

    app.aboutToQuit.connect(_shutdown_workers)
    _configure_palette(app)
    app.setFont(QFont('Microsoft YaHei UI', 11))
    app.setStyleSheet(APP_QSS)

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception:
        error = traceback.format_exc()
        write_error_log(error)
        QMessageBox.critical(
            None,
            'WinTuner — 启动错误',
            f'启动异常:\n\n{error}\n\n日志: {LOG_PATH}',
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
