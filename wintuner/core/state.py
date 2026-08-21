"""可逆系统修改的持久化快照与注册表/计划任务事务支持。"""

import base64
import copy
import json
import re
import threading
import winreg
from .commands import CommandRunner
from .paths import write_error_log
_ACTION_CTX = threading.local()


class SecureState:
    """将恢复快照持久化到 HKLM，确保高权限修改具备可恢复依据。"""
    PATH = 'SOFTWARE\\WinTuner\\Recovery'
    VALUE = 'StateJson'
    _data = None
    _lock = threading.RLock()
    _error = None

    @classmethod
    def _load(cls):
        with cls._lock:
            if cls._data is not None:
                return cls._error is None
            try:
                k = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    cls.PATH,
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                )
                try:
                    raw, _ = winreg.QueryValueEx(k, cls.VALUE)
                finally:
                    winreg.CloseKey(k)
                data = json.loads(str(raw))
                if not isinstance(data, dict):
                    raise ValueError('恢复状态根节点不是 JSON 对象')
                cls._data = data
                cls._error = None
                return True
            except FileNotFoundError:
                cls._data = {}
                cls._error = None
                return True
            except Exception as e:
                cls._data = {}
                cls._error = str(e)
                write_error_log(f'受保护恢复状态读取失败: {e}')
                return False

    @classmethod
    def available(cls):
        return cls._load()

    @classmethod
    def get(cls, key, d=None):
        with cls._lock:
            if not cls._load():
                return copy.deepcopy(d)
            return copy.deepcopy(cls._data.get(key, d))

    @classmethod
    def set(cls, key, v):
        with cls._lock:
            if not cls._load():
                return False
            cls._data[key] = copy.deepcopy(v)
            return True

    @classmethod
    def delete(cls, key):
        with cls._lock:
            if not cls._load():
                return False
            cls._data.pop(key, None)
            return True

    @classmethod
    def save(cls):
        with cls._lock:
            if not cls._load():
                return False
            try:
                k = winreg.CreateKeyEx(
                    winreg.HKEY_LOCAL_MACHINE,
                    cls.PATH,
                    0,
                    winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
                )
                try:
                    winreg.SetValueEx(
                        k,
                        cls.VALUE,
                        0,
                        winreg.REG_SZ,
                        json.dumps(cls._data, ensure_ascii=False, separators=(',', ':')),
                    )
                finally:
                    winreg.CloseKey(k)
                return True
            except Exception as e:
                write_error_log(f'受保护恢复状态保存失败: {e}')
                return False


class RegistryTxn:
    """一次 UI 动作对应的注册表事务快照。"""
    PREFIX = 'registry_restore::'

    @staticmethod
    def _key(action):
        return RegistryTxn.PREFIX + str(action)

    @staticmethod
    def begin(action, mode):
        _ACTION_CTX.action = action
        _ACTION_CTX.mode = mode
        _ACTION_CTX.errors = []

    @staticmethod
    def end():
        _ACTION_CTX.action = None
        _ACTION_CTX.mode = None
        _ACTION_CTX.errors = []

    @staticmethod
    def note_error(msg):
        try:
            _ACTION_CTX.errors.append(str(msg))
        except Exception:
            pass

    @staticmethod
    def errors():
        return list(getattr(_ACTION_CTX, 'errors', []) or [])

    @staticmethod
    def _pack(v):
        if isinstance(v, bytes):
            return {'__bytes__': base64.b64encode(v).decode('ascii')}
        return v

    @staticmethod
    def _unpack(v):
        if isinstance(v, dict) and '__bytes__' in v:
            return base64.b64decode(v['__bytes__'])
        return v

    @staticmethod
    def capture(hive, path, name):
        if getattr(_ACTION_CTX, 'mode', None) != 'apply':
            return True
        action = getattr(_ACTION_CTX, 'action', None)
        if not action:
            return True
        if path.lower().startswith('system\\currentcontrolset\\services\\'):
            return True
        try:
            snap = SecureState.get(RegistryTxn._key(action), {}) or {}
            item_key = f'{int(hive)}|{path}|{name}'
            if item_key in snap:
                return True
            try:
                k = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                key_exists = True
                try:
                    v, t = winreg.QueryValueEx(k, name)
                    snap[item_key] = {
                        'hive': int(hive),
                        'path': path,
                        'name': name,
                        'key_exists': True,
                        'exists': True,
                        'type': int(t),
                        'value': RegistryTxn._pack(v),
                    }
                except FileNotFoundError:
                    snap[item_key] = {
                        'hive': int(hive),
                        'path': path,
                        'name': name,
                        'key_exists': True,
                        'exists': False,
                    }
                finally:
                    winreg.CloseKey(k)
            except FileNotFoundError:
                snap[item_key] = {
                    'hive': int(hive),
                    'path': path,
                    'name': name,
                    'key_exists': False,
                    'exists': False,
                }
            key = RegistryTxn._key(action)
            SecureState.set(key, snap)
            if not SecureState.save():
                snap.pop(item_key, None)
                if snap:
                    SecureState.set(key, snap)
                else:
                    SecureState.delete(key)
                RegistryTxn.note_error(f'无法持久化原状态快照: {path}\\{name}')
                return False
            return True
        except Exception as e:
            write_error_log(f'Registry snapshot failed [{action}] {path}\\{name}: {e}')
            RegistryTxn.note_error(f'原状态快照失败: {path}\\{name}')
            return False

    @staticmethod
    def restore(action):
        snap = SecureState.get(RegistryTxn._key(action))
        if not snap:
            return (True, '')
        errors = []
        for item in snap.values():
            hive = item.get('hive')
            path = item.get('path')
            name = item.get('name')
            try:
                if item.get('exists'):
                    if path.lower().startswith('system\\currentcontrolset\\services\\'):
                        k = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
                    else:
                        k = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
                    winreg.SetValueEx(k, name, 0, int(item['type']), RegistryTxn._unpack(item.get('value')))
                    winreg.CloseKey(k)
                else:
                    try:
                        k = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
                        try:
                            winreg.DeleteValue(k, name)
                        except FileNotFoundError:
                            pass
                        winreg.CloseKey(k)
                    except FileNotFoundError:
                        pass
            except Exception as e:
                errors.append(f'{path}\\{name}: {e}')
        if errors:
            return (False, '原状态恢复不完整: ' + '; '.join(errors[:4]))
        prune = {(int(item.get('hive')), str(item.get('path'))) for item in snap.values() if item.get('key_exists') is False}
        for hive, path in sorted(prune, key=lambda x: x[1].count('\\'), reverse=True):
            try:
                if hasattr(winreg, 'DeleteKeyEx'):
                    winreg.DeleteKeyEx(hive, path, winreg.KEY_WOW64_64KEY, 0)
                else:
                    winreg.DeleteKey(hive, path)
            except FileNotFoundError:
                pass
            except OSError as e:
                try:
                    k = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                    subs, vals, _ = winreg.QueryInfoKey(k)
                    winreg.CloseKey(k)
                    if subs == 0 and vals == 0:
                        errors.append(f'{path}: 空注册表键清理失败: {e}')
                except FileNotFoundError:
                    pass
                except Exception as qe:
                    errors.append(f'{path}: 注册表键恢复复核失败: {qe}')
        if errors:
            return (False, '原状态恢复不完整: ' + '; '.join(errors[:4]))
        key = RegistryTxn._key(action)
        SecureState.delete(key)
        if not SecureState.save():
            SecureState.set(key, snap)
            return (False, '注册表已恢复，但无法安全更新恢复快照文件')
        return (True, '原始注册表状态已恢复')


class TaskTxn:
    """计划任务启用状态的事务快照与恢复。"""
    PREFIX = 'task_restore::'

    @staticmethod
    def _key(action):
        return TaskTxn.PREFIX + str(action)

    @staticmethod
    def _full_name(path, name):
        p = str(path or '\\')
        if not p.startswith('\\'):
            p = '\\' + p
        if not p.endswith('\\'):
            p += '\\'
        return p + str(name)

    @staticmethod
    def _query(path, name):
        full = TaskTxn._full_name(path, name)
        c, o, e = CommandRunner.run_cmd(['schtasks', '/Query', '/TN', full, '/XML'], 45)
        if c == 0:
            m = re.search('<Enabled>\\s*(true|false)\\s*</Enabled>', o, re.I)
            if m:
                return ('ENABLED' if m.group(1).lower() == 'true' else 'DISABLED', '')
        text = (str(o) + '\n' + str(e)).lower()
        missing_marks = ('cannot find', 'not exist', 'does not exist', '找不到', '不存在', '未找到', '指定的任务名')
        if any((x in text for x in missing_marks)):
            return ('MISSING', e or o)
        p = path.replace("'", "''")
        n = name.replace("'", "''")
        (c2, o2, e2) = CommandRunner.run_ps(
            f"$t=Get-ScheduledTask -TaskPath '{p}' -TaskName '{n}' -ErrorAction Stop;if([string]$t.State -eq 'Disabled'){{'DISABLED'}}else{{'ENABLED'}}",
        )
        if c2 == 0 and o2.strip():
            st = o2.strip().upper()
            if st in ('ENABLED', 'DISABLED'):
                return (st, '')
        detail = str(e2 or e or o or o2)
        low = detail.lower()
        if any((x in low for x in missing_marks)):
            return ('MISSING', detail)
        if 'access is denied' in low or 'access denied' in low or '拒绝访问' in detail or ('权限' in detail):
            return ('PROTECTED', detail)
        return ('ERROR', detail)

    @staticmethod
    def capture(path, name):
        if getattr(_ACTION_CTX, 'mode', None) != 'apply':
            return True
        action = getattr(_ACTION_CTX, 'action', None)
        if not action:
            return True
        snap = SecureState.get(TaskTxn._key(action), {}) or {}
        item_key = path + '|' + name
        if item_key in snap:
            return True
        st, _ = TaskTxn._query(path, name)
        if st in ('ERROR', 'PROTECTED'):
            return False
        key = TaskTxn._key(action)
        snap[item_key] = {'path': path, 'name': name, 'state': st}
        SecureState.set(key, snap)
        if SecureState.save():
            return True
        snap.pop(item_key, None)
        if snap:
            SecureState.set(key, snap)
        else:
            SecureState.delete(key)
        return False

    @staticmethod
    def set_enabled(path, name, enabled):
        if not TaskTxn.capture(path, name):
            return (False, '无法保存计划任务原状态，已拒绝修改')
        st, why = TaskTxn._query(path, name)
        if st == 'PROTECTED':
            return (False, '该计划任务受 Windows ACL 保护，当前管理员令牌无法可靠读取或修改；已安全跳过')
        if st == 'ERROR':
            return (False, '任务状态检测失败: ' + str(why or '未知错误'))
        if st == 'MISSING':
            return (True, '任务不存在，跳过')
        full = TaskTxn._full_name(path, name)
        flag = '/ENABLE' if enabled else '/DISABLE'
        c, o, e = CommandRunner.run_cmd(['schtasks', '/Change', '/TN', full, flag], 45)
        if c != 0:
            p = path.replace("'", "''")
            n = name.replace("'", "''")
            cmd = 'Enable-ScheduledTask' if enabled else 'Disable-ScheduledTask'
            (c2, o2, e2) = CommandRunner.run_ps(
                f"{cmd} -TaskPath '{p}' -TaskName '{n}' -ErrorAction Stop|Out-Null",
            )
            if c2 != 0:
                err = str(e2 or o2 or e or o or '任务修改被系统拒绝')
                low = err.lower()
                if 'access is denied' in low or 'access denied' in low or '拒绝访问' in err or ('权限' in err):
                    return (False, '该计划任务受 Windows ACL 保护，当前管理员令牌也无修改权限；已安全跳过，不会破坏任务文件或 ACL')
                return (False, err)
        after, why2 = TaskTxn._query(path, name)
        ok = after == 'ENABLED' if enabled else after == 'DISABLED'
        return (ok, ('已启用' if enabled else '已禁用') if ok else f"验证失败: {after} {why2 or ''}".strip())

    @staticmethod
    def restore(action):
        snap = SecureState.get(TaskTxn._key(action))
        if not snap:
            return (True, '')
        errs = []
        for item in snap.values():
            state = item.get('state', 'ERROR')
            path = item.get('path', '')
            name = item.get('name', '')
            if state == 'MISSING':
                continue
            if state in ('ERROR', 'PROTECTED'):
                errs.append(f'{name}: 原状态未知或受系统保护')
                continue
            ok, msg = TaskTxn.set_enabled(path, name, state != 'DISABLED')
            if not ok:
                errs.append(f'{name}: {msg}')
        if errs:
            return (False, '计划任务原状态恢复不完整: ' + '; '.join(errs[:4]))
        key = TaskTxn._key(action)
        SecureState.delete(key)
        if not SecureState.save():
            SecureState.set(key, snap)
            return (False, '计划任务已恢复，但无法安全更新恢复快照')
        return (True, '原始计划任务状态已恢复')


class StateTxn:
    """通用结构化状态快照，用于防火墙、设备等非单值配置。"""
    PREFIX = 'state_restore::'

    @staticmethod
    def _key(name):
        return StateTxn.PREFIX + str(name)

    @staticmethod
    def get(name):
        return SecureState.get(StateTxn._key(name))

    @staticmethod
    def save_once(name, value):
        key = StateTxn._key(name)
        if SecureState.get(key) is not None:
            return True
        SecureState.set(key, value)
        if SecureState.save():
            return True
        SecureState.delete(key)
        return False

    @staticmethod
    def clear(name):
        key = StateTxn._key(name)
        old = SecureState.get(key)
        SecureState.delete(key)
        if SecureState.save():
            return True
        if old is not None:
            SecureState.set(key, old)
        return False


def _rr(hive, path, name):
    try:
        k = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        v, _ = winreg.QueryValueEx(k, name)
        winreg.CloseKey(k)
        return v
    except Exception:
        return None


def _wr(hive, path, name, val, typ=winreg.REG_DWORD):
    try:
        if not RegistryTxn.capture(hive, path, name):
            return False
        if path.lower().startswith('system\\currentcontrolset\\services\\'):
            k = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        else:
            k = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        winreg.SetValueEx(k, name, 0, typ, val)
        winreg.CloseKey(k)
        return True
    except Exception as e:
        RegistryTxn.note_error(e)
        return False


def _dr(hive, path, name):
    try:
        if not RegistryTxn.capture(hive, path, name):
            return False
        k = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        try:
            winreg.DeleteValue(k, name)
        except FileNotFoundError:
            pass
        winreg.CloseKey(k)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        RegistryTxn.note_error(e)
        return False
