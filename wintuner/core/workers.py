"""Qt 后台任务封装，以及 UI 页面共享的异步执行 MixIn。"""

import os
import traceback
import weakref
import winreg
from PyQt6.QtCore import QObject, QRunnable, QTimer, pyqtSignal
from .runtime import _DETECT_POOL, _MUTATION_LOCK, _MUTATION_POOL, _pending_mutations, _system_generation
from .state import RegistryTxn, SecureState, TaskTxn, _rr


class _Sig(QObject):
    done = pyqtSignal(bool, str)


class _ObjSig(QObject):
    done = pyqtSignal(bool, object)


class _Worker(QRunnable):

    def __init__(self, func, args, sig):
        super().__init__()
        self._func = func
        self._args = args
        self._sig = sig
        self.setAutoDelete(True)

    def run(self):
        try:
            r = self._func(*self._args)
            ok, msg = (bool(r[0]), str(r[1])) if isinstance(r, tuple) and len(r) == 2 else (True, str(r))
        except Exception:
            try:
                ok, msg = (False, f'执行异常: {traceback.format_exc()}')
            except Exception:
                return
        self._sig.done.emit(ok, msg)


class _ObjWorker(QRunnable):

    def __init__(self, func, args, sig):
        super().__init__()
        self._func = func
        self._args = args
        self._sig = sig
        self.setAutoDelete(True)

    def run(self):
        try:
            self._sig.done.emit(True, self._func(*self._args))
        except Exception:
            self._sig.done.emit(False, traceback.format_exc())


class MixIn:
    """页面共享的异步任务、批量检测与可逆操作执行能力。"""

    def _init_workers(self):
        self._sigs = set()
        self._detect_batch_running = False
        self._detect_batch_pending = False

    def _track_sig(self, sig):
        _ref = weakref.ref(self._sigs)

        def _rm(*_):
            s = _ref()
            if s is not None:
                s.discard(sig)
            try:
                sig.done.disconnect()
            except Exception:
                pass
        sig.done.connect(_rm)
        self._sigs.add(sig)

    def _run_async(self, func, cb, *args, pool=None):
        sig = _Sig()
        sig.done.connect(cb)
        self._track_sig(sig)
        (pool or _DETECT_POOL).start(_Worker(func, args, sig))

    def _run_object_async(self, func, cb, *args, pool=None):
        sig = _ObjSig()
        sig.done.connect(cb)
        self._track_sig(sig)
        (pool or _DETECT_POOL).start(_ObjWorker(func, args, sig))

    def _begin_detect_batch(self):
        if self._detect_batch_running:
            self._detect_batch_pending = True
            return False
        self._detect_batch_running = True
        self._detect_batch_pending = False
        return True

    def _end_detect_batch(self, rerun):
        self._detect_batch_running = False
        if self._detect_batch_pending:
            self._detect_batch_pending = False
            QTimer.singleShot(0, rerun)

    def _run_action(self, action, mode, func, cb, *args):

        def _wrapped():
            with _MUTATION_LOCK:
                RegistryTxn.begin(action, mode)
                try:
                    if mode in ('apply', 'restore') and (not SecureState.available()):
                        return (False, '受保护的恢复状态存储不可用，已拒绝执行可逆高权限操作，以避免无法安全恢复')
                    r = func(*args)
                    ok, msg = (bool(r[0]), str(r[1])) if isinstance(r, tuple) and len(r) == 2 else (True, str(r))
                    errs = RegistryTxn.errors()
                    if errs:
                        ok = False
                        msg = (msg + '\n' if msg else '') + '底层写入失败: ' + '; '.join(errs[:3])
                    if mode == 'restore':
                        rok, rmsg = RegistryTxn.restore(action)
                        tok, tmsg = TaskTxn.restore(action)
                        if not rok or not tok:
                            return (False, (msg + '\n' if msg else '') + '; '.join((x for x in (rmsg, tmsg) if x)))
                        for x in (rmsg, tmsg):
                            if x:
                                msg = (msg + '\n' if msg else '') + '  ✓ ' + x
                        env_map = {
                            'dotnet_tele': 'DOTNET_CLI_TELEMETRY_OPTOUT',
                            'ps_tele': 'POWERSHELL_TELEMETRY_OPTOUT',
                        }
                        if action in env_map:
                            n = env_map[action]
                            v = _rr(
                                winreg.HKEY_LOCAL_MACHINE,
                                'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment',
                                n,
                            )
                            if v is None:
                                os.environ.pop(n, None)
                            else:
                                os.environ[n] = str(v)
                    return (ok, msg)
                finally:
                    RegistryTxn.end()

        def _finished(ok, msg):
            _pending_mutations(-1)
            _system_generation(True)
            cb(ok, msg)
        _system_generation(True)
        _pending_mutations(1)
        try:
            self._run_async(_wrapped, _finished, pool=_MUTATION_POOL)
        except Exception:
            _pending_mutations(-1)
            raise
