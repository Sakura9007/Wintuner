"""诊断事件、遥测服务、CompatTelRunner、CEIP 与 AIT。"""

from __future__ import annotations

import os
import winreg
from wintuner.core.constants import APP_EXP_TASK_PATH, CEIP_TASK_PATH, POWER_DIAG_TASK_PATH
from wintuner.core.state import TaskTxn, _rr, _wr, _dr


class TelemetrySettingsMixin:
    """诊断事件、遥测服务、CompatTelRunner、CEIP 与 AIT。"""

    @classmethod
    def get_diag_events_status(cls):
        task, why = TaskTxn._query(POWER_DIAG_TASK_PATH, 'AnalyzeSystem')
        if task == 'PROTECTED':
            return '检测受限'
        if task == 'ERROR':
            return '检测失败'
        return '已关闭' if task in ('DISABLED', 'MISSING') else '已开启'

    @classmethod
    def disable_diag_events(cls):
        ok, msg = TaskTxn.set_enabled(POWER_DIAG_TASK_PATH, 'AnalyzeSystem', False)
        st = cls.get_diag_events_status()
        ok = ok and st == '已关闭'
        return (ok, '电源效率诊断任务已关闭' if ok else f'电源效率诊断任务关闭失败 (当前: {st}): {msg}')

    @classmethod
    def enable_diag_events(cls):
        ok, msg = TaskTxn.set_enabled(POWER_DIAG_TASK_PATH, 'AnalyzeSystem', True)
        if not ok:
            return (False, '电源效率诊断任务恢复失败: ' + msg)
        return (True, '电源效率诊断任务已执行恢复；最终状态将按修改前快照还原')

    @classmethod
    def get_dotnet_telemetry_status(cls):
        return '已关闭' if str(_rr(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment', 'DOTNET_CLI_TELEMETRY_OPTOUT')) == '1' else '已开启'

    @classmethod
    def disable_dotnet_telemetry(cls):
        ok = _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment',
            'DOTNET_CLI_TELEMETRY_OPTOUT',
            '1',
            winreg.REG_SZ,
        )
        if ok:
            os.environ['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
        return (ok, '.NET CLI遥测已关闭' if ok else '.NET CLI遥测关闭失败')

    @classmethod
    def enable_dotnet_telemetry(cls):
        ok = _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment',
            'DOTNET_CLI_TELEMETRY_OPTOUT',
        )
        if ok:
            os.environ.pop('DOTNET_CLI_TELEMETRY_OPTOUT', None)
        return (ok, '.NET CLI遥测已恢复' if ok else '.NET CLI遥测恢复失败')

    @classmethod
    def get_ps_telemetry_status(cls):
        return '已关闭' if str(_rr(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment', 'POWERSHELL_TELEMETRY_OPTOUT')) == '1' else '已开启'

    @classmethod
    def disable_ps_telemetry(cls):
        ok = _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment',
            'POWERSHELL_TELEMETRY_OPTOUT',
            '1',
            winreg.REG_SZ,
        )
        if ok:
            os.environ['POWERSHELL_TELEMETRY_OPTOUT'] = '1'
        return (ok, 'PowerShell遥测已关闭' if ok else 'PowerShell遥测关闭失败')

    @classmethod
    def enable_ps_telemetry(cls):
        ok = _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment',
            'POWERSHELL_TELEMETRY_OPTOUT',
        )
        if ok:
            os.environ.pop('POWERSHELL_TELEMETRY_OPTOUT', None)
        return (ok, 'PowerShell遥测已恢复' if ok else 'PowerShell遥测恢复失败')

    @classmethod
    def get_telemetry_svc_status(cls):
        states = [cls.get_service_status(s) for s in ['DiagTrack', 'diagsvc', 'dmwappushservice']]
        if '检测失败' in states:
            return '检测失败'
        present = [x for x in states if x != '未找到']
        if not present:
            return '未找到'
        off = sum((1 for x in present if x == '已禁用'))
        return '已关闭' if off == len(present) else f'部分关闭 ({off}/{len(present)})' if off else '已开启'

    @classmethod
    def disable_telemetry_svc(cls):
        ms = []
        oks = []
        for svc in ['DiagTrack', 'diagsvc', 'dmwappushservice']:
            if _rr(winreg.HKEY_LOCAL_MACHINE, f'SYSTEM\\CurrentControlSet\\Services\\{svc}', 'Start') is None:
                ms.append(f'  ℹ {svc} 未安装')
                continue
            ok, msg = cls.disable_service(svc)
            oks.append(ok)
            ms.append(('  ✓ ' if ok else '  ✗ ') + msg)
        ok = all(oks) if oks else True
        return (ok, ('遥测服务已关闭:\n' if ok else '遥测服务未完全关闭:\n') + '\n'.join(ms))

    @classmethod
    def enable_telemetry_svc(cls):
        ms = []
        oks = []
        for svc in ['DiagTrack', 'diagsvc', 'dmwappushservice']:
            if _rr(winreg.HKEY_LOCAL_MACHINE, f'SYSTEM\\CurrentControlSet\\Services\\{svc}', 'Start') is None:
                continue
            ok, msg = cls.enable_service(svc)
            oks.append(ok)
            ms.append(('  ✓ ' if ok else '  ✗ ') + msg)
        ok = all(oks) if oks else True
        return (ok, ('遥测服务已恢复:\n' if ok else '遥测服务恢复不完整:\n') + '\n'.join(ms))

    @classmethod
    def get_compat_telrunner_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\AppCompat',
            'DisableInventory',
        )
        return '已关闭' if v == 1 else '已开启'

    @classmethod
    def disable_compat_telrunner(cls):
        path = 'SOFTWARE\\Policies\\Microsoft\\Windows\\AppCompat'
        ok = _wr(winreg.HKEY_LOCAL_MACHINE, path, 'DisableInventory', 1)
        return (ok, 'Windows Inventory Collector 已关闭 (DisableInventory=1，建议重启)' if ok else 'Inventory Collector 策略写入失败')

    @classmethod
    def enable_compat_telrunner(cls):
        ok = _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\AppCompat',
            'DisableInventory',
        )
        return (ok, 'Inventory Collector 策略已执行恢复；最终值将按修改前快照还原' if ok else 'Inventory Collector 策略恢复失败')

    @classmethod
    def get_ceip_updater_status(cls):
        st, _ = TaskTxn._query(APP_EXP_TASK_PATH, 'ProgramDataUpdater')
        if st == 'PROTECTED':
            return '检测受限'
        if st == 'ERROR':
            return '检测失败'
        return '已关闭' if st in ('DISABLED', 'MISSING') else '已开启'

    @classmethod
    def disable_ceip_updater(cls):
        ok, msg = TaskTxn.set_enabled(APP_EXP_TASK_PATH, 'ProgramDataUpdater', False)
        return (ok, 'CEIP ProgramDataUpdater已关闭' if ok else 'CEIP ProgramDataUpdater禁用失败: ' + msg)

    @classmethod
    def enable_ceip_updater(cls):
        ok, msg = TaskTxn.set_enabled(APP_EXP_TASK_PATH, 'ProgramDataUpdater', True)
        return (ok, 'CEIP ProgramDataUpdater已启用' if ok else 'CEIP ProgramDataUpdater启用失败: ' + msg)

    @classmethod
    def get_aitagent_status(cls):
        st, _ = TaskTxn._query(APP_EXP_TASK_PATH, 'AitAgent')
        if st == 'PROTECTED':
            return '检测受限'
        if st == 'ERROR':
            return '检测失败'
        return '已关闭' if st in ('DISABLED', 'MISSING') else '已开启'

    @classmethod
    def disable_aitagent(cls):
        ok, msg = TaskTxn.set_enabled(APP_EXP_TASK_PATH, 'AitAgent', False)
        return (ok, 'AitAgent任务已关闭' if ok else 'AitAgent任务禁用失败: ' + msg)

    @classmethod
    def enable_aitagent(cls):
        ok, msg = TaskTxn.set_enabled(APP_EXP_TASK_PATH, 'AitAgent', True)
        return (ok, 'AitAgent任务已启用' if ok else 'AitAgent任务启用失败: ' + msg)

    @classmethod
    def get_ceip_tasks_status(cls):
        states = [TaskTxn._query(CEIP_TASK_PATH, n)[0] for n in ['Consolidator', 'KernelCeipTask', 'UsbCeip']]
        if 'PROTECTED' in states:
            return '检测受限'
        if 'ERROR' in states:
            return '检测失败'
        off = sum((1 for x in states if x in ('DISABLED', 'MISSING')))
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_ceip_tasks(cls):
        ms = []
        oks = []
        for n in ['Consolidator', 'KernelCeipTask', 'UsbCeip']:
            ok, msg = TaskTxn.set_enabled(CEIP_TASK_PATH, n, False)
            oks.append(ok)
            ms.append(('  ✓ ' if ok else '  ✗ ') + n + ': ' + msg)
        return (all(oks), ('CEIP任务已关闭:\n' if all(oks) else 'CEIP任务关闭不完整:\n') + '\n'.join(ms))

    @classmethod
    def enable_ceip_tasks(cls):
        ms = []
        oks = []
        for n in ['Consolidator', 'KernelCeipTask', 'UsbCeip']:
            ok, msg = TaskTxn.set_enabled(CEIP_TASK_PATH, n, True)
            oks.append(ok)
            ms.append(('  ✓ ' if ok else '  ✗ ') + n + ': ' + msg)
        return (all(oks), ('CEIP任务已启用:\n' if all(oks) else 'CEIP任务启用不完整:\n') + '\n'.join(ms))

    @classmethod
    def get_ceip_sqm_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\SQMClient\\Windows', 'CEIPEnable')
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_ceip_sqm(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\SQMClient\\Windows', 'CEIPEnable', 0)
        return (True, 'CEIP/SQM已关闭')

    @classmethod
    def enable_ceip_sqm(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\SQMClient\\Windows', 'CEIPEnable')
        return (True, 'CEIP/SQM已恢复')

    @classmethod
    def get_ait_enable_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\AppCompat', 'AITEnable')
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_ait_enable(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\AppCompat', 'AITEnable', 0)
        return (True, '应用程序影响遥测已关闭')

    @classmethod
    def enable_ait_enable(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\AppCompat', 'AITEnable')
        return (True, '应用程序影响遥测已恢复')
