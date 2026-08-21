"""应用目录、资源目录和日志路径解析。"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime


LOG_PATH = os.path.join(tempfile.gettempdir(), 'WinTuner_error.log')


def app_base_dir() -> str:
    """返回源码运行或 Nuitka 发布版的应用根目录。"""

    try:
        if sys.argv and sys.argv[0]:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.dirname(os.path.abspath(sys.executable))
    except Exception:
        return os.getcwd()


def candidate_base_dirs() -> list[str]:
    """返回资源文件可能出现的目录，顺序即查找优先级。"""

    candidates = [
        app_base_dir(),
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.abspath(sys.executable)),
    ]

    result: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in result:
            result.append(candidate)
    return result


# 与旧版 UI 的圆角/布局计算保持一致。
WR = 10


def write_error_log(text: object) -> None:
    """诊断日志失败时静默返回，避免日志系统反过来影响主功能。"""

    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as handle:
            handle.write(
                f"\n{'=' * 60}\n"
                f'[{datetime.now():%Y-%m-%d %H:%M:%S}]\n'
                f'{text}\n'
            )
    except Exception:
        pass
