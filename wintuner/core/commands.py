"""受限的高权限命令执行器。\n\n所有外部命令都必须命中明确的 Windows 系统组件白名单，并始终使用\n``shell=False`` 执行。PowerShell 脚本通过 EncodedCommand 传递，以避免\n本地代码页和复杂引号导致的参数解析差异。\n"""

from __future__ import annotations

import base64
import ctypes
import locale
import os
import subprocess
import threading
from collections.abc import Sequence


Command = str | Sequence[object]
CommandResult = tuple[int, str, str]

_PROC_SEM = threading.Semaphore(8)
_SYSTEM_ROOT = os.environ.get('SystemRoot', r'C:\Windows')
_DEFAULT_ENCODING = locale.getpreferredencoding(False) or 'utf-8'
_SYSTEM_DIR_NAME = (
    'Sysnative' if os.environ.get('PROCESSOR_ARCHITEW6432') else 'System32'
)

# 只允许这些受信任系统组件作为高权限子进程入口。
_CMD_COMPONENTS: dict[str, tuple[str, ...]] = {
    'sc': (_SYSTEM_DIR_NAME, 'sc.exe'),
    'net': (_SYSTEM_DIR_NAME, 'net.exe'),
    'bcdedit': (_SYSTEM_DIR_NAME, 'bcdedit.exe'),
    'gpupdate': (_SYSTEM_DIR_NAME, 'gpupdate.exe'),
    'manage-bde': (_SYSTEM_DIR_NAME, 'manage-bde.exe'),
    'control': (_SYSTEM_DIR_NAME, 'control.exe'),
    'schtasks': (_SYSTEM_DIR_NAME, 'schtasks.exe'),
    'dism': (_SYSTEM_DIR_NAME, 'Dism.exe'),
    'powercfg': (_SYSTEM_DIR_NAME, 'powercfg.exe'),
    'rundll32': (_SYSTEM_DIR_NAME, 'rundll32.exe'),
    'powershell': (
        _SYSTEM_DIR_NAME,
        'WindowsPowerShell',
        'v1.0',
        'powershell.exe',
    ),
}

_CMD_PATHS: dict[str, str] = {}
for _name, _parts in _CMD_COMPONENTS.items():
    _path = os.path.join(_SYSTEM_ROOT, *_parts)
    _CMD_PATHS[_name] = _path
    _CMD_PATHS[_name + '.exe'] = _path

# CommandLineToArgvW 用于安全解析旧代码传入的字符串命令行。
_CMDLINE_TO_ARGV = ctypes.windll.shell32.CommandLineToArgvW
_CMDLINE_TO_ARGV.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
_CMDLINE_TO_ARGV.restype = ctypes.POINTER(ctypes.c_wchar_p)

_LOCAL_FREE = ctypes.windll.kernel32.LocalFree
_LOCAL_FREE.argtypes = [ctypes.c_void_p]
_LOCAL_FREE.restype = ctypes.c_void_p

_PS_PREFIX = (
    "$ProgressPreference='SilentlyContinue';"
    "$InformationPreference='SilentlyContinue';"
    "$VerbosePreference='SilentlyContinue';"
    "$ErrorActionPreference='Stop';"
    "$u=[System.Text.UTF8Encoding]::new($false);"
    '[Console]::OutputEncoding=$u;'
    '$OutputEncoding=$u;'
)


class CommandRunner:
    """解析参数、强制白名单路径并执行 Windows 系统命令。"""

    @staticmethod
    def _parse_command(command: Command) -> tuple[list[str] | None, str | None]:
        if isinstance(command, (list, tuple)):
            return [str(item) for item in command], None

        text = str(command).strip()
        if not text:
            return None, '无效命令'

        argc = ctypes.c_int(0)
        argv = _CMDLINE_TO_ARGV(text, ctypes.byref(argc))
        if not argv:
            return None, '无法解析命令行'

        try:
            return [argv[index] for index in range(argc.value)], None
        finally:
            _LOCAL_FREE(ctypes.cast(argv, ctypes.c_void_p))

    @staticmethod
    def _decode_output(raw: bytes, encoding: str) -> str:
        if not raw:
            return ''

        try:
            if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
                return raw.decode('utf-16').strip()
            if raw.startswith(b'\xef\xbb\xbf'):
                return raw.decode('utf-8-sig').strip()
            if raw.count(b'\x00') > max(4, len(raw) // 8):
                return raw.decode('utf-16le', errors='replace').strip()
            return raw.decode(encoding, errors='replace').strip()
        except Exception:
            return raw.decode('utf-8', errors='replace').strip()

    @staticmethod
    def run_cmd(
        command: Command,
        timeout: float = 45,
        encoding: str | None = None,
    ) -> CommandResult:
        try:
            args, parse_error = CommandRunner._parse_command(command)
            if not args:
                return -1, '', parse_error or '无效命令'

            executable_name = os.path.basename(args[0]).lower()
            executable_path = _CMD_PATHS.get(executable_name)
            if not executable_path:
                return (
                    -1,
                    '',
                    f'拒绝执行未列入白名单的高权限命令: {executable_name}',
                )
            if not os.path.isfile(executable_path):
                return -1, '', f'系统组件不存在: {executable_path}'

            args[0] = executable_path
            output_encoding = encoding or _DEFAULT_ENCODING

            with _PROC_SEM:
                result = subprocess.run(
                    args,
                    shell=False,
                    capture_output=True,
                    text=False,
                    timeout=timeout,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

            return (
                result.returncode,
                CommandRunner._decode_output(result.stdout, output_encoding),
                CommandRunner._decode_output(result.stderr, output_encoding),
            )
        except subprocess.TimeoutExpired:
            return -1, '', f'命令执行超时 ({timeout}s)'
        except Exception as exc:
            return -1, '', str(exc)

    @staticmethod
    def _clean_ps_stream(text: object) -> str:
        value = str(text or '').strip()
        if not value:
            return ''

        lower = value.lower()
        is_progress_only_clixml = (
            ('#< clixml' in lower or '<objs' in lower)
            and 's="error"' not in lower
            and 's="warning"' not in lower
            and 's="progress"' in lower
        )
        if is_progress_only_clixml:
            return ''
        return value

    @staticmethod
    def run_ps(command: str, timeout: float = 60) -> CommandResult:
        encoded = base64.b64encode(
            (_PS_PREFIX + command).encode('utf-16le')
        ).decode('ascii')

        code, stdout, stderr = CommandRunner.run_cmd(
            [
                'powershell',
                '-NoLogo',
                '-NoProfile',
                '-NonInteractive',
                '-InputFormat',
                'Text',
                '-OutputFormat',
                'Text',
                '-ExecutionPolicy',
                'Bypass',
                '-EncodedCommand',
                encoded,
            ],
            timeout,
            'utf-8',
        )
        return (
            code,
            CommandRunner._clean_ps_stream(stdout),
            CommandRunner._clean_ps_stream(stderr),
        )
