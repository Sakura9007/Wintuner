"""Power Throttling、电源计划与隐藏电源选项。"""

from __future__ import annotations

import re
import winreg
from wintuner.core.constants import HIDDEN_POWER, PP_SUB
from wintuner.core.state import SecureState, _rr, _wr, _dr


class PowerSettingsMixin:
    """Power Throttling、电源计划与隐藏电源选项。"""

    @classmethod
    def get_power_throttling_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Power\\PowerThrottling',
            'PowerThrottlingOff',
        )
        return '已关闭' if v == 1 else '已开启' if v == 0 else '系统默认'

    @classmethod
    def disable_power_throttling(cls):
        path = 'SYSTEM\\CurrentControlSet\\Control\\Power\\PowerThrottling'
        if not _wr(winreg.HKEY_LOCAL_MACHINE, path, 'PowerThrottlingOff', 1):
            return (False, '关闭 Power Throttling 失败: 无法写入系统策略')
        if _rr(winreg.HKEY_LOCAL_MACHINE, path, 'PowerThrottlingOff') != 1:
            return (False, '关闭 Power Throttling 失败: 写入后验证未通过')
        return (True, 'Power Throttling 已关闭 (建议重启后确保所有进程应用新策略)')

    @classmethod
    def enable_power_throttling(cls):
        path = 'SYSTEM\\CurrentControlSet\\Control\\Power\\PowerThrottling'
        v = _rr(winreg.HKEY_LOCAL_MACHINE, path, 'PowerThrottlingOff')
        if v is None:
            return (True, 'Power Throttling 已处于 Windows 系统默认管理状态')
        if not _dr(winreg.HKEY_LOCAL_MACHINE, path, 'PowerThrottlingOff'):
            return (False, '恢复 Power Throttling 默认状态失败: 无法删除策略值')
        if _rr(winreg.HKEY_LOCAL_MACHINE, path, 'PowerThrottlingOff') is not None:
            return (False, '恢复 Power Throttling 默认状态失败: 删除后验证未通过')
        return (True, 'Power Throttling 已恢复为 Windows 系统默认管理 (建议重启后确保所有进程应用新策略)')

    @classmethod
    def _active_power_scheme(cls):
        c, o, e = cls.run_cmd('powercfg /getactivescheme')
        if c != 0:
            return (None, '')
        m = re.search('([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', o.lower())
        return (m.group(1) if m else None, o)

    @classmethod
    def get_power_plan_status(cls):
        guid, o = cls._active_power_scheme()
        if not guid:
            return '检测失败'
        if guid.startswith('e9a42b02'):
            return '卓越性能'
        saved = str(SecureState.get('ultimate_scheme_guid', '')).lower()
        if saved and guid == saved:
            return '卓越性能'
        lo = o.lower()
        if 'ultimate performance' in lo or '卓越性能' in o:
            return '卓越性能'
        if guid.startswith('8c5e7fda'):
            return '高性能'
        if guid.startswith('381b4222'):
            return '平衡'
        if guid.startswith('a1841308'):
            return '节能'
        return '自定义'

    @classmethod
    def set_high_performance(cls):
        target = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
        c, o, e = cls.run_cmd(f'powercfg /setactive {target}')
        guid, _ = cls._active_power_scheme()
        ok = c == 0 and guid == target
        return (True, '已切换至高性能电源计划') if ok else (False, f'切换失败或验证未通过: {e or o}')

    @classmethod
    def set_ultimate_performance(cls):
        base = 'e9a42b02-d5df-448d-aa00-03f14749eb61'
        c, o, e = cls.run_cmd(f'powercfg /setactive {base}')
        guid, _ = cls._active_power_scheme()
        if c == 0 and guid == base:
            return (True, '已切换至卓越性能电源计划')
        c2, o2, e2 = cls.run_cmd(f'powercfg -duplicatescheme {base}')
        if c2 != 0:
            return (False, '创建卓越性能计划失败: ' + (e2 or o2))
        m = re.search('([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', o2.lower())
        if not m:
            return (False, '卓越性能计划已创建，但未能解析新电源方案 GUID')
        new_guid = m.group(1)
        c3, o3, e3 = cls.run_cmd(f'powercfg /setactive {new_guid}')
        active, _ = cls._active_power_scheme()
        if c3 == 0 and active == new_guid:
            SecureState.set('ultimate_scheme_guid', new_guid)
            persisted = SecureState.save()
            return (True, '已创建并切换至卓越性能电源计划' + ('' if persisted else '（方案已生效，但持久状态标识保存失败）'))
        return (False, '卓越性能计划已创建，但激活失败: ' + (e3 or o3))

    @classmethod
    def open_power_settings(cls):
        cls.run_cmd('control /name Microsoft.PowerOptions')

    @classmethod
    def get_hidden_power_status(cls):
        hidden = 0
        known = 0
        for g, _ in HIDDEN_POWER:
            v = _rr(
                winreg.HKEY_LOCAL_MACHINE,
                f'SYSTEM\\CurrentControlSet\\Control\\Power\\PowerSettings\\{PP_SUB}\\{g}',
                'Attributes',
            )
            if isinstance(v, int):
                known += 1
                hidden += 1 if v & 1 else 0
        if known != len(HIDDEN_POWER):
            return '检测失败'
        return '已全部开放' if hidden == 0 else f'隐藏中 ({hidden}/{len(HIDDEN_POWER)})'

    @classmethod
    def unlock_hidden_power(cls):
        ms = []
        ok = True
        for g, name in HIDDEN_POWER:
            c, _, e = cls.run_cmd(f'powercfg -attributes {PP_SUB} {g} -ATTRIB_HIDE')
            ms.append(f'  ✓ {name}' if c == 0 else f'  ✗ {name}: {e}')
            ok = ok and c == 0
        if ok:
            ok = cls.get_hidden_power_status() == '已全部开放'
        return (ok, ('已开放隐藏电源选项:\n' if ok else '部分隐藏电源选项开放失败:\n') + '\n'.join(ms) + '\n\n请在电源计划高级设置中查看')
