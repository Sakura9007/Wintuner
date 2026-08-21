"""全局运行时状态：线程池、变更序号、检测批次与并发锁。"""

from __future__ import annotations

import threading

from PyQt6.QtCore import QThreadPool


# 系统修改必须串行执行，避免两个高权限动作同时改写同一注册表/服务状态。
_MUTATION_LOCK = threading.RLock()
_MUTATION_POOL = QThreadPool()
_MUTATION_POOL.setMaxThreadCount(1)

# 状态检测可以并发执行，以缩短页面首次打开时的等待时间。
_DETECT_POOL = QThreadPool()
_DETECT_POOL.setMaxThreadCount(4)
_DETECT_CTX = threading.local()
_DETECT_BATCH_SEQ = 0
_DETECT_BATCH_LOCK = threading.Lock()

# PnP 批量检测缓存。缓存只在同一个检测批次和系统状态 generation 下有效。
_PNP_DETECT_LOCK = threading.Lock()
_PNP_DETECT_KEY = None
_PNP_DETECT_ROWS = None

# 修改计数与系统状态 generation 用于丢弃“修改前发起、修改后才返回”的过期检测结果。
_MUTATION_PENDING = 0
_MUTATION_PENDING_LOCK = threading.Lock()
_SYSTEM_STATE_GEN = 0
_SYSTEM_STATE_GEN_LOCK = threading.Lock()

_DETECT_CANCELLED = '__WINTUNER_DETECT_CANCELLED__'


def _pending_mutations(delta: int = 0) -> int:
    global _MUTATION_PENDING

    with _MUTATION_PENDING_LOCK:
        _MUTATION_PENDING = max(0, _MUTATION_PENDING + int(delta))
        return _MUTATION_PENDING


def _system_generation(bump: bool = False) -> int:
    global _SYSTEM_STATE_GEN

    with _SYSTEM_STATE_GEN_LOCK:
        if bump:
            _SYSTEM_STATE_GEN += 1
        return _SYSTEM_STATE_GEN


def _next_detect_batch_id() -> int:
    global _DETECT_BATCH_SEQ

    with _DETECT_BATCH_LOCK:
        _DETECT_BATCH_SEQ += 1
        return _DETECT_BATCH_SEQ


def shutdown_pools() -> None:
    """尽力停止后台任务；退出清理不能反向阻止应用关闭。"""

    try:
        _MUTATION_POOL.clear()
        _DETECT_POOL.clear()
    except Exception:
        pass

    try:
        _MUTATION_POOL.waitForDone(3000)
    except Exception:
        pass

    try:
        _DETECT_POOL.waitForDone(1500)
    except Exception:
        pass
