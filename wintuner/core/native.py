"""Windows 原生 API 封装，用于低开销地读取服务运行状态。"""

import ctypes
import re
_GET_LAST_ERROR = ctypes.windll.kernel32.GetLastError
_GET_LAST_ERROR.restype = ctypes.c_ulong
_ADVAPI32 = ctypes.windll.advapi32
_OPEN_SCM = _ADVAPI32.OpenSCManagerW
_OPEN_SCM.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulong]
_OPEN_SCM.restype = ctypes.c_void_p
_OPEN_SERVICE = _ADVAPI32.OpenServiceW
_OPEN_SERVICE.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong]
_OPEN_SERVICE.restype = ctypes.c_void_p
_QUERY_SERVICE_STATUS_EX = _ADVAPI32.QueryServiceStatusEx
_QUERY_SERVICE_STATUS_EX.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong),
]
_QUERY_SERVICE_STATUS_EX.restype = ctypes.c_bool
_CLOSE_SERVICE_HANDLE = _ADVAPI32.CloseServiceHandle
_CLOSE_SERVICE_HANDLE.argtypes = [ctypes.c_void_p]
_CLOSE_SERVICE_HANDLE.restype = ctypes.c_bool


class _SERVICE_STATUS_PROCESS(ctypes.Structure):
    _fields_ = [
        ('dwServiceType', ctypes.c_ulong),
        ('dwCurrentState', ctypes.c_ulong),
        ('dwControlsAccepted', ctypes.c_ulong),
        ('dwWin32ExitCode', ctypes.c_ulong),
        ('dwServiceSpecificExitCode', ctypes.c_ulong),
        ('dwCheckPoint', ctypes.c_ulong),
        ('dwWaitHint', ctypes.c_ulong),
        ('dwProcessId', ctypes.c_ulong),
        ('dwServiceFlags', ctypes.c_ulong),
    ]


def _native_service_running(name):
    scm = _OPEN_SCM(None, None, 1)
    if not scm:
        return None
    try:
        svc = _OPEN_SERVICE(scm, str(name), 4)
        if not svc:
            return (False, False) if int(_GET_LAST_ERROR()) == 1060 else None
        try:
            status = _SERVICE_STATUS_PROCESS()
            needed = ctypes.c_ulong(0)
            if not _QUERY_SERVICE_STATUS_EX(svc, 0, ctypes.byref(status), ctypes.sizeof(status), ctypes.byref(needed)):
                return None
            return (True, status.dwCurrentState == 4)
        finally:
            _CLOSE_SERVICE_HANDLE(svc)
    finally:
        _CLOSE_SERVICE_HANDLE(scm)


def _sc_service_running(output):
    text = str(output or '')
    for line in text.splitlines():
        if 'STATE' in line.upper() or '状态' in line:
            m = re.search(':\\s*(\\d+)', line)
            if m:
                return int(m.group(1)) == 4
    return 'RUNNING' in text.upper() or '正在运行' in text
