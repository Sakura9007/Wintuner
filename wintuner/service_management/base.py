"""服务查询、禁用与严格恢复的底层控制器。"""

import winreg
from wintuner.core.commands import CommandRunner
from wintuner.core.native import _native_service_running, _sc_service_running
from wintuner.core.state import SecureState, _rr, _wr, _dr


class ServiceController(CommandRunner):
    """封装 Windows Service 的读取、禁用与按原状态恢复。"""

    # --------------------------------------------------------------------
    # 服务状态解析
    # --------------------------------------------------------------------
    @staticmethod
    def _service_missing_text(text):
        t = str(text or '').lower()
        return any((x in t for x in ('1060', 'does not exist', 'not exist', 'specified service does not exist', '服务未安装', '指定的服务未安装', '找不到指定的服务', '不存在')))

    # --------------------------------------------------------------------
    # 公开服务操作
    # --------------------------------------------------------------------
    @staticmethod
    def get_service_status(svc):
        native = _native_service_running(svc)
        if native is not None:
            exists, running = native
            if not exists:
                return '未找到'
            path = f'SYSTEM\\CurrentControlSet\\Services\\{svc}'
            start = _rr(winreg.HKEY_LOCAL_MACHINE, path, 'Start')
            if start is None:
                return '检测失败'
            if start == 4:
                return '部分禁用(仍运行)' if running else '已禁用'
            return '运行中' if running else '已停止'
        c, o, e = ServiceController.run_cmd(['sc', 'query', str(svc)])
        if c != 0:
            return '未找到' if ServiceController._service_missing_text(o + '\n' + e) else '检测失败'
        path = f'SYSTEM\\CurrentControlSet\\Services\\{svc}'
        start = _rr(winreg.HKEY_LOCAL_MACHINE, path, 'Start')
        if start is None:
            return '检测失败'
        running = _sc_service_running(o)
        if start == 4:
            return '部分禁用(仍运行)' if running else '已禁用'
        return '运行中' if running else '已停止'

    @staticmethod
    def disable_service(svc):
        cq0, oq0, eq0 = ServiceController.run_cmd(['sc', 'query', str(svc)])
        if cq0 != 0:
            if ServiceController._service_missing_text(oq0 + '\n' + eq0):
                return (True, f'服务 [{svc}] 未安装，无需禁用')
            return (False, f'服务 [{svc}] 无法查询: {eq0 or oq0}')
        path = f'SYSTEM\\CurrentControlSet\\Services\\{svc}'
        start = _rr(winreg.HKEY_LOCAL_MACHINE, path, 'Start')
        if start is None:
            return (False, f'服务 [{svc}] 注册表启动类型无法读取')
        snapkey = f'service_restore::{svc}'
        if SecureState.get(snapkey) is None:
            delayed = _rr(winreg.HKEY_LOCAL_MACHINE, path, 'DelayedAutoStart')
            c0, o0, e0 = ServiceController.run_cmd(f'sc query "{svc}"')
            if c0 != 0:
                return (False, f'服务 [{svc}] 当前运行状态无法确认，已拒绝修改: {e0 or o0}')
            SecureState.set(
                snapkey,
                {'start': int(start), 'delayed': int(delayed or 0), 'delayed_present': delayed is not None, 'running': _sc_service_running(o0)},
            )
            if not SecureState.save():
                SecureState.delete(snapkey)
                return (False, f'服务 [{svc}] 原状态快照保存失败，已拒绝禁用')
        if start == 4:
            c0, o0, e0 = ServiceController.run_cmd(f'sc query "{svc}"')
            if c0 != 0:
                return (False, f'服务 [{svc}] 状态复核失败: {e0 or o0}')
            if _sc_service_running(o0):
                ServiceController.run_cmd(f'net stop "{svc}"', 60)
                cq, oq, eq = ServiceController.run_cmd(f'sc query "{svc}"')
                if cq != 0 or _sc_service_running(oq):
                    return (False, f'服务 [{svc}] 已禁用但停止失败: {eq or oq}')
            return (True, f'服务 [{svc}] 已处于禁用状态')
        ServiceController.run_cmd(f'net stop "{svc}"', 60)
        c, o, e = ServiceController.run_cmd(f'sc config "{svc}" start= disabled')
        c2, o2, _ = ServiceController.run_cmd(f'sc query "{svc}"')
        ok = c == 0 and _rr(winreg.HKEY_LOCAL_MACHINE, path, 'Start') == 4 and (c2 == 0) and (not _sc_service_running(o2))
        return (True, f'服务 [{svc}] 已禁用并停止') if ok else (False, f'禁用未完全生效: {e or o or o2}')

    @staticmethod
    def enable_service(svc):
        snapkey = f'service_restore::{svc}'
        state = SecureState.get(snapkey)
        cq0, oq0, eq0 = ServiceController.run_cmd(['sc', 'query', str(svc)])
        if cq0 != 0:
            if ServiceController._service_missing_text(oq0 + '\n' + eq0):
                return (False, f'服务 [{svc}] 已不存在，但仍有恢复快照，已保留快照') if state is not None else (True, f'服务 [{svc}] 未安装，无需恢复')
            return (False, f'服务 [{svc}] 无法查询: {eq0 or oq0}')
        path = f'SYSTEM\\CurrentControlSet\\Services\\{svc}'
        current = _rr(winreg.HKEY_LOCAL_MACHINE, path, 'Start')
        if current is None:
            return (False, f'服务 [{svc}] 注册表启动类型无法读取')
        if state is None:
            if current != 4:
                return (True, f'服务 [{svc}] 当前未被禁用，无需恢复')
            return (False, f'服务 [{svc}] 没有本工具保存的禁用前快照，已拒绝猜测原启动类型')
        try:
            start = int(state['start'])
            delayed = int(state.get('delayed', 0))
            delayed_present = bool(state.get('delayed_present', True))
            was_running = bool(state.get('running', False))
        except Exception:
            return (False, f'服务 [{svc}] 的恢复快照损坏，未执行恢复')
        mode = {0: 'boot', 1: 'system', 2: 'auto', 3: 'demand', 4: 'disabled'}.get(start)
        if mode is None:
            return (False, f'服务 [{svc}] 快照中的启动类型无效: {start}')
        c, o, e = ServiceController.run_cmd(f'sc config "{svc}" start= {mode}')
        if c != 0:
            return (False, f'恢复失败: {e or o}')
        delayed_ok = True
        if start == 2 and delayed_present:
            delayed_ok = _wr(winreg.HKEY_LOCAL_MACHINE, path, 'DelayedAutoStart', 1 if delayed else 0)
        else:
            delayed_ok = _dr(winreg.HKEY_LOCAL_MACHINE, path, 'DelayedAutoStart')
        start_ok = _rr(winreg.HKEY_LOCAL_MACHINE, path, 'Start') == start
        running_ok = True
        if start != 4:
            if was_running:
                cs, os_, es = ServiceController.run_cmd(f'net start "{svc}"', 60)
                cq, oq, _ = ServiceController.run_cmd(f'sc query "{svc}"')
                running_ok = cq == 0 and _sc_service_running(oq)
            else:
                cq, oq, eq = ServiceController.run_cmd(f'sc query "{svc}"')
                if cq != 0:
                    running_ok = False
                elif _sc_service_running(oq):
                    ServiceController.run_cmd(f'net stop "{svc}"', 60)
                    cq, oq, _ = ServiceController.run_cmd(f'sc query "{svc}"')
                    running_ok = cq == 0 and (not _sc_service_running(oq))
        if not (start_ok and delayed_ok and running_ok):
            return (False, f'服务 [{svc}] 恢复不完整，原状态快照已保留，可再次重试')
        SecureState.delete(snapkey)
        if not SecureState.save():
            SecureState.set(snapkey, state)
            return (False, f'服务 [{svc}] 已恢复，但恢复快照文件无法安全更新')
        label = '自动(延迟启动)' if start == 2 and delayed else {0: '引导', 1: '系统', 2: '自动', 3: '手动', 4: '禁用'}.get(start, str(start))
        return (True, f'服务 [{svc}] 已严格恢复为{label}')
