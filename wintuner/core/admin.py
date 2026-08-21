"""Windows 管理员权限提升与单实例控制。"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys

from .paths import write_error_log


_ORIGIN_PROFILE_PREFIX = '--wintuner-origin-profile='
_INSTANCE_MUTEX = None


def _consume_origin_profile_arg() -> str | None:
    """读取并移除 UAC 提升前注入的原用户目录参数。"""

    value: str | None = None
    for index in range(len(sys.argv) - 1, 0, -1):
        argument = str(sys.argv[index])
        if argument.startswith(_ORIGIN_PROFILE_PREFIX):
            value = str(sys.argv.pop(index)).split('=', 1)[1]
    return value


ORIGIN_PROFILE_ARG = _consume_origin_profile_arg()


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def require_admin() -> None:
    """若当前进程未提升，则通过 UAC 重新启动当前入口。"""

    if is_admin():
        return

    script = os.path.abspath(sys.argv[0])
    origin = os.environ.get('USERPROFILE', '')
    params = subprocess.list2cmdline(
        [
            script,
            *sys.argv[1:],
            f'--wintuner-origin-profile={origin}',
        ]
    )
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        'runas',
        sys.executable,
        params,
        None,
        1,
    )
    if int(result) <= 32:
        write_error_log(f'请求管理员权限失败，ShellExecuteW={int(result)}')
        raise RuntimeError(f'无法获取管理员权限 (ShellExecuteW={int(result)})')

    sys.exit(0)


def _acquire_single_instance() -> bool:
    """使用命名 Mutex 保证同一桌面会话只运行一个 WinTuner。"""

    global _INSTANCE_MUTEX

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_bool,
            ctypes.c_wchar_p,
        ]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.GetLastError.restype = ctypes.c_ulong

        handle = kernel32.CreateMutexW(
            None,
            False,
            'Local\\WinTuner_SingleInstance',
        )
        if not handle:
            return False

        # ERROR_ALREADY_EXISTS
        if kernel32.GetLastError() == 183:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
            return False

        _INSTANCE_MUTEX = handle
        return True
    except Exception as exc:
        # 单实例保护失败不应阻止用户进入程序，但需要记录诊断信息。
        write_error_log(f'单实例互斥创建失败: {exc}')
        return True


def _release_single_instance() -> None:
    global _INSTANCE_MUTEX

    if not _INSTANCE_MUTEX:
        return

    try:
        ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(_INSTANCE_MUTEX))
    except Exception:
        pass
    finally:
        _INSTANCE_MUTEX = None
