"""虚拟化安全与 Windows Update。"""

from __future__ import annotations

import os
import winreg
from datetime import UTC, datetime
from wintuner.core.state import _rr, _wr


class VirtualizationUpdateMixin:
    """虚拟化安全与 Windows Update。"""

    @classmethod
    def get_vbs_status(cls):
        reg = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\DeviceGuard',
            'EnableVirtualizationBasedSecurity',
        )
        (c, o, _) = cls.run_ps(
            '(Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root/Microsoft/Windows/DeviceGuard -ErrorAction Stop).VirtualizationBasedSecurityStatus',
        )
        if c == 0 and o.strip() in ('0', '1', '2'):
            runtime = int(o.strip())
            if runtime == 0:
                return '已关闭' if reg == 0 else '运行时已关闭'
            if reg == 0:
                return '待重启'
            return '已开启'
        if reg == 0:
            return '未验证(配置为关闭)'
        if reg is not None:
            return '未验证(配置为开启)'
        return '检测失败'

    @classmethod
    def disable_vbs(cls):
        msgs = []
        ok = True
        groups = [
            ('SYSTEM\\CurrentControlSet\\Control\\DeviceGuard', [('EnableVirtualizationBasedSecurity', 0), ('RequirePlatformSecurityFeatures', 0)]),
            ('SYSTEM\\CurrentControlSet\\Control\\Lsa', [('LsaCfgFlags', 0)]),
        ]
        for path, pairs in groups:
            for name, val in pairs:
                r = _wr(winreg.HKEY_LOCAL_MACHINE, path, name, val)
                ok = ok and r
                msgs.append(f'  ✓ {name}={val}' if r else f'  ✗ {name} 写入失败')
        c, _, e = cls.run_cmd('bcdedit /set hypervisorlaunchtype off')
        ok = ok and c == 0
        msgs.append('  ✓ hypervisorlaunchtype=off' if c == 0 else f'  ✗ bcdedit: {e}')
        return (ok, ('VBS 关闭设置完成 (需重启):\n' if ok else 'VBS 设置未完全写入:\n') + '\n'.join(msgs))

    @classmethod
    def get_update_pause_status(cls):
        no_auto = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU',
            'NoAutoUpdate',
        )
        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                'SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings',
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )
            v, _ = winreg.QueryValueEx(k, 'PauseUpdatesExpiryTime')
            winreg.CloseKey(k)
        except Exception:
            v = None
        valid_date = None
        if v:
            try:
                raw = str(v).strip()
                expiry = datetime.fromisoformat(raw[:-1] + '+00:00' if raw.endswith('Z') else raw)
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=UTC)
                if expiry > datetime.now(UTC):
                    valid_date = str(v)[:10]
            except Exception:
                pass
        if no_auto == 1:
            return f'已暂停至 {valid_date}' if valid_date else '已暂停（长期）'
        return f'已暂停至 {valid_date}' if valid_date else '未暂停'

    @classmethod
    def pause_updates_100years(cls):
        now = datetime.now(UTC)
        try:
            future = now.replace(year=now.year + 100)
        except ValueError:
            future = now.replace(year=now.year + 100, month=2, day=28)
        fmt = '%Y-%m-%dT%H:%M:%SZ'
        ns, fs = (now.strftime(fmt), future.strftime(fmt))
        ms = []
        try:
            ux = 'SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings'
            ok_write = _wr(winreg.HKEY_LOCAL_MACHINE, ux, 'FlightSettingsMaxPauseDays', 36500)
            for n, v in [('PauseFeatureUpdatesStartTime', ns), ('PauseFeatureUpdatesEndTime', fs), ('PauseQualityUpdatesStartTime', ns), ('PauseQualityUpdatesEndTime', fs), ('PauseUpdatesExpiryTime', fs), ('PauseUpdatesStartTime', ns)]:
                ok_write = _wr(winreg.HKEY_LOCAL_MACHINE, ux, n, v, winreg.REG_SZ) and ok_write
            ms.append('  ✓ 长期暂停日期已写入' if ok_write else '  ✗ 部分长期暂停日期写入失败')
            au = 'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU'
            policy_ok = _wr(winreg.HKEY_LOCAL_MACHINE, au, 'NoAutoUpdate', 1)
            ms.append('  ✓ 自动更新策略已禁用' if policy_ok else '  ✗ 自动更新策略写入失败')
            cls.run_cmd('gpupdate /target:computer /force')
            ok = ok_write and policy_ok and (_rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU', 'NoAutoUpdate') == 1)
            try:
                k = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    'SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings',
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                )
                v, _ = winreg.QueryValueEx(k, 'PauseUpdatesExpiryTime')
                winreg.CloseKey(k)
                ok = ok and str(v).startswith(future.strftime('%Y-%m-%d'))
            except Exception:
                ok = False
            return (ok, (f"更新已暂停至 {future.strftime('%Y-%m-%d')}:\n" if ok else '更新暂停设置未完全写入:\n') + '\n'.join(ms))
        except Exception as e:
            return (False, f'设置失败: {e}')

    @classmethod
    def open_update_settings(cls):
        try:
            os.startfile('ms-settings:windowsupdate')
            return (True, '已打开 Windows Update 设置')
        except Exception as e:
            return (False, f'无法打开 Windows Update 设置: {e}')
