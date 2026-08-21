"""防火墙、Defender、BCD、内存压缩和安全策略。"""

from __future__ import annotations

import json
import winreg
from wintuner.core.native import _sc_service_running
from wintuner.core.state import StateTxn, _rr, _wr, _dr


class SecuritySettingsMixin:
    """防火墙、Defender、BCD、内存压缩和安全策略。"""

    @classmethod
    def _firewall_profiles(cls):
        (c, o, e) = cls.run_ps(
            'Get-NetFirewallProfile -ErrorAction Stop|Select-Object Name,Enabled|ConvertTo-Json -Compress',
        )
        if c != 0 or not o.strip():
            return None
        try:
            data = json.loads(o)
            items = data if isinstance(data, list) else [data]

            def _b(v):
                return v is True or v == 1 or str(v).strip().lower() in ('true', '1')
            return {str(x.get('Name')): _b(x.get('Enabled')) for x in items if x.get('Name')}
        except Exception:
            return None

    @classmethod
    def get_firewall_status(cls):
        p = cls._firewall_profiles()
        if not p:
            return '检测失败'
        on = sum((bool(v) for v in p.values()))
        n = len(p)
        return '已开启' if on == n else '已关闭' if on == 0 else f'部分开启 ({on}/{n})'

    @classmethod
    def disable_firewall(cls):
        before = cls._firewall_profiles()
        if before is None:
            return (False, '无法读取防火墙原始状态，已拒绝修改')
        if not StateTxn.save_once('firewall', before):
            return (False, '无法保存防火墙原始状态，已拒绝修改')
        (c, o, e) = cls.run_ps(
            'Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled $false -ErrorAction Stop',
        )
        st = cls.get_firewall_status()
        ok = c == 0 and st == '已关闭'
        return (ok, '防火墙已关闭' if ok else f'关闭失败或未完全生效: {e or o}; 当前: {st}')

    @classmethod
    def enable_firewall(cls):
        snap = StateTxn.get('firewall')
        if isinstance(snap, dict) and snap:
            errs = []
            for name, enabled in snap.items():
                val = '$true' if enabled else '$false'
                (c, o, e) = cls.run_ps(
                    f"Set-NetFirewallProfile -Name '{str(name).replace(chr(39), chr(39) * 2)}' -Enabled {val} -ErrorAction Stop",
                )
                if c != 0:
                    errs.append(f'{name}: {e or o}')
            after = cls._firewall_profiles()
            ok = not errs and after is not None and all((after.get(k) == bool(v) for k, v in snap.items()))
            if ok and (not StateTxn.clear('firewall')):
                return (False, '防火墙已恢复，但无法安全清除恢复快照')
            return (ok, '防火墙已严格恢复到修改前状态' if ok else '防火墙恢复不完整: ' + '; '.join(errs[:3]))
        (c, o, e) = cls.run_ps(
            'Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled $true -ErrorAction Stop',
        )
        st = cls.get_firewall_status()
        ok = c == 0 and st == '已开启'
        return (ok, '未找到历史快照，已按显式“开启”恢复全部防火墙配置文件' if ok else f'防火墙开启失败: {e or o}; 当前: {st}')

    @classmethod
    def get_defender_status(cls):
        (c, o, _) = cls.run_ps(
            "$s=Get-MpComputerStatus -ErrorAction SilentlyContinue;if($s){Write-Output ($s.AntivirusEnabled.ToString()+'|'+$s.RealTimeProtectionEnabled.ToString()+'|'+$s.IsTamperProtected.ToString())}",
        )
        if c == 0 and o.strip():
            p = o.strip().split('|')
            if len(p) >= 2:
                av = p[0].upper() == 'TRUE'
                rt = p[1].upper() == 'TRUE'
                if not rt:
                    return '已停止/已禁用' if not av else '部分禁用'
                return '运行中'
        c2, o2, e2 = cls.run_cmd('sc query WinDefend')
        text = o2 + ' ' + e2
        lo = text.lower()
        if c2 == 0:
            return '运行中' if _sc_service_running(o2) else '已停止'
        if 'does not exist' in lo or '不存在' in text or '1060' in text:
            return '已卸载'
        return '检测失败'

    @classmethod
    def remove_defender(cls):
        ms = []
        (c, o, e) = cls.run_ps(
            '$s=Get-MpComputerStatus -ErrorAction Stop;$s.IsTamperProtected',
        )
        if c != 0:
            return (False, '无法读取 Defender/篡改保护状态，已中止高风险操作: ' + (e or o))
        if o.strip().upper() == 'TRUE':
            return (False, '篡改保护仍处于开启状态。请先在 Windows 安全中心关闭「篡改保护」，然后重新执行。')
        (c, _, e) = cls.run_ps(
            'Set-MpPreference -DisableRealtimeMonitoring $true -DisableBehaviorMonitoring $true -DisableIOAVProtection $true -DisableScriptScanning $true -MAPSReporting 0 -SubmitSamplesConsent 2 -PUAProtection 0 -ErrorAction Stop',
        )
        ms.append('  ✓ Defender 实时/行为/脚本/下载扫描已关闭' if c == 0 else f'  ✗ PowerShell 设置失败: {e}')
        policy_ok = True
        for path, pairs in [('SOFTWARE\\Policies\\Microsoft\\Windows Defender', [('DisableRoutinelyTakingAction', 1), ('PUAProtection', 0)]), ('SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection', [('DisableRealtimeMonitoring', 1), ('DisableBehaviorMonitoring', 1), ('DisableOnAccessProtection', 1), ('DisableScanOnRealtimeEnable', 1), ('DisableIOAVProtection', 1), ('DisableScriptScanning', 1)]), ('SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Spynet', [('SpynetReporting', 0), ('SubmitSamplesConsent', 2)])]:
            for name, val in pairs:
                if not _wr(winreg.HKEY_LOCAL_MACHINE, path, name, val):
                    policy_ok = False
        ms.append('  ✓ Defender 实时保护策略已写入' if policy_ok else '  ✗ 部分 Defender 策略写入失败')
        disabled_tasks = 0
        for t in ['\\Microsoft\\Windows\\Windows Defender\\Windows Defender Cache Maintenance', '\\Microsoft\\Windows\\Windows Defender\\Windows Defender Cleanup', '\\Microsoft\\Windows\\Windows Defender\\Windows Defender Scheduled Scan', '\\Microsoft\\Windows\\Windows Defender\\Windows Defender Verification']:
            ct, _, _ = cls.run_cmd(f'schtasks /Change /TN "{t}" /Disable')
            disabled_tasks += ct == 0
        ms.append(
            ('  ✓' if disabled_tasks == 4 else '  ⚠' if disabled_tasks else '  ✗') + f' Defender 计划任务已处理 ({disabled_tasks}/4)',
        )
        cls.run_cmd('gpupdate /target:computer /force', 90)
        (c_feature, _, _) = cls.run_cmd(
            'Dism /online /Get-FeatureInfo /FeatureName:Windows-Defender /English',
            90,
        )
        if c_feature == 0:
            (cr, _, er) = cls.run_cmd(
                'Dism /online /Disable-Feature /FeatureName:Windows-Defender /Remove /NoRestart /quiet',
                180,
            )
            ms.append('  ✓ Defender 可选组件已移除' if cr == 0 else f'  ⚠ Defender 可选组件移除失败: {er}')
        else:
            ms.append('  ℹ 当前 Windows 客户端 Defender 不是可卸载 Optional Feature')
        (cv, ov, ev) = cls.run_ps(
            '$s=Get-MpComputerStatus -ErrorAction Stop;$s.RealTimeProtectionEnabled',
        )
        if cv != 0 or not ov.strip():
            return (False, 'Defender 设置已写入，但最终状态无法验证: ' + (ev or ov) + '\n' + '\n'.join(ms))
        if ov.strip().upper() != 'FALSE':
            return (False, 'Defender 设置已写入，但实时保护仍在运行。\n' + '\n'.join(ms))
        return (c == 0 and policy_ok, ('Defender 高强度禁用完成 (需重启后复核):\n' if c == 0 and policy_ok else 'Defender 已部分禁用，但存在失败项:\n') + '\n'.join(ms))

    @classmethod
    def _bcd_timer_values(cls):
        c, o, e = cls.run_cmd('bcdedit /enum {current}')
        if c != 0:
            return None
        d = {'disabledynamictick': None, 'useplatformtick': None}
        for line in o.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].lower() in d:
                d[parts[0].lower()] = parts[-1].lower()
        return d

    @classmethod
    def get_bcdedit_status(cls):
        d = cls._bcd_timer_values()
        if d is None:
            return '检测失败'
        ddt = d['disabledynamictick'] == 'yes'
        pt = d['useplatformtick'] == 'yes'
        return '已设置' if ddt and pt else '部分设置' if ddt or pt else '未设置'

    @classmethod
    def set_bcdedit_timers(cls):
        before = cls._bcd_timer_values()
        if before is None:
            return (False, '无法读取 BCD 原始值，已拒绝修改')
        if not StateTxn.save_once('bcdedit', before):
            return (False, '无法保存 BCD 原始状态，已拒绝修改')
        ms = []
        c1, _, e1 = cls.run_cmd('bcdedit /set disabledynamictick yes')
        ms.append('  ✓ disabledynamictick=yes' if c1 == 0 else f'  ✗ {e1}')
        c2, _, e2 = cls.run_cmd('bcdedit /set useplatformtick yes')
        ms.append('  ✓ useplatformtick=yes' if c2 == 0 else f'  ✗ {e2}')
        ok = c1 == 0 and c2 == 0 and (cls.get_bcdedit_status() == '已设置')
        return (ok, ('BCD 计时器设置完成 (需重启):\n' if ok else 'BCD 计时器设置未完全生效:\n') + '\n'.join(ms))

    @classmethod
    def reset_bcdedit_timers(cls):
        snap = StateTxn.get('bcdedit')
        target = snap if isinstance(snap, dict) else {'disabledynamictick': None, 'useplatformtick': None}
        ms = []
        ok = True
        for name in ('disabledynamictick', 'useplatformtick'):
            value = target.get(name)
            if value is None:
                c, o, e = cls.run_cmd(f'bcdedit /deletevalue {name}')
                good = c == 0 or 'not found' in (o + e).lower() or '找不到' in o + e
            else:
                c, o, e = cls.run_cmd(f'bcdedit /set {name} {value}')
                good = c == 0
            ok = ok and good
            ms.append(
                ('  ✓ ' if good else '  ✗ ') + f"{name} → {(value if value is not None else '未设置')}" + ('' if good else f': {e or o}'),
            )
        after = cls._bcd_timer_values()
        verify = after is not None and all((after.get(k) == target.get(k) for k in target))
        ok = ok and verify
        if ok and snap is not None and (not StateTxn.clear('bcdedit')):
            return (False, 'BCD 已恢复，但无法安全清除恢复快照')
        return (ok, ('BCD 计时器已严格恢复:\n' if ok and snap is not None else 'BCD 计时器已还原为未设置:\n' if ok else 'BCD 计时器还原未完全生效:\n') + '\n'.join(ms))

    @classmethod
    def _memory_compression_value(cls):
        c, o, e = cls.run_ps('(Get-MMAgent -ErrorAction Stop).MemoryCompression')
        if c != 0 or o.strip().upper() not in ('TRUE', 'FALSE'):
            return None
        return o.strip().upper() == 'TRUE'

    @classmethod
    def get_memory_compression_status(cls):
        v = cls._memory_compression_value()
        return '检测失败' if v is None else '压缩中' if v else '已关闭'

    @classmethod
    def disable_memory_compression(cls):
        before = cls._memory_compression_value()
        if before is None:
            return (False, '无法读取内存压缩原始状态，已拒绝修改')
        if not StateTxn.save_once('memcompress', before):
            return (False, '无法保存内存压缩原始状态，已拒绝修改')
        c, o, e = cls.run_ps('Disable-MMAgent -MemoryCompression -ErrorAction Stop')
        after = cls._memory_compression_value()
        ok = c == 0 and after is False
        return (ok, '内存压缩已关闭 (部分系统需重启后完全生效)' if ok else f'关闭失败或验证未通过: {e or o}')

    @classmethod
    def enable_memory_compression(cls):
        snap = StateTxn.get('memcompress')
        target = bool(snap) if isinstance(snap, bool) else True
        cmd = 'Enable-MMAgent -MemoryCompression -ErrorAction Stop' if target else 'Disable-MMAgent -MemoryCompression -ErrorAction Stop'
        c, o, e = cls.run_ps(cmd)
        after = cls._memory_compression_value()
        ok = c == 0 and after is target
        if ok and snap is not None and (not StateTxn.clear('memcompress')):
            return (False, '内存压缩已恢复，但无法安全清除恢复快照')
        return (ok, '内存压缩已严格恢复到修改前状态' if ok and snap is not None else '未找到历史快照，已按显式恢复启用内存压缩' if ok else f'恢复失败或验证未通过: {e or o}')

    @classmethod
    def get_xbox_gamebar_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR',
            'AppCaptureEnabled',
        )
        v2 = _rr(winreg.HKEY_CURRENT_USER, 'System\\GameConfigStore', 'GameDVR_Enabled')
        if v == 0 and v2 == 0:
            return '已关闭'
        (c, o, _) = cls.run_ps(
            "if(Get-AppxPackage Microsoft.XboxGamingOverlay -ErrorAction SilentlyContinue){'INSTALLED'}else{'MISSING'}",
        )
        if c != 0:
            return '检测失败'
        return '组件缺失' if o.strip() != 'INSTALLED' else '已开启'

    @classmethod
    def disable_xbox_gamebar(cls):
        ok1 = _wr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR',
            'AppCaptureEnabled',
            0,
        )
        ok2 = _wr(winreg.HKEY_CURRENT_USER, 'System\\GameConfigStore', 'GameDVR_Enabled', 0)
        ok3 = _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\GameDVR',
            'AllowGameDVR',
            0,
        )
        (c, _, e) = cls.run_ps(
            '$p=Get-AppxPackage Microsoft.XboxGamingOverlay -ErrorAction SilentlyContinue;if($p){$p|Remove-AppxPackage -ErrorAction Stop}',
        )
        ok = ok1 and ok2 and ok3 and (c == 0)
        return (ok, 'Xbox Game Bar已关闭' if ok else f'Xbox Game Bar关闭不完整: {e}')

    @classmethod
    def enable_xbox_gamebar(cls):
        ok1 = _wr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR',
            'AppCaptureEnabled',
            1,
        )
        ok2 = _wr(winreg.HKEY_CURRENT_USER, 'System\\GameConfigStore', 'GameDVR_Enabled', 1)
        ok3 = _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\GameDVR',
            'AllowGameDVR',
        )
        (c, o, _) = cls.run_ps(
            "if(Get-AppxPackage Microsoft.XboxGamingOverlay -ErrorAction SilentlyContinue){'INSTALLED'}else{'MISSING'}",
        )
        if c != 0:
            return (False, 'Game DVR设置已恢复，但无法检测 Xbox Game Bar 包')
        if o.strip() != 'INSTALLED':
            return (False, 'Game DVR设置已恢复，但 Xbox Game Bar 应用包已被卸载；请从 Microsoft Store 重新安装')
        return (ok1 and ok2 and ok3, 'Xbox Game Bar已恢复')

    @classmethod
    def get_security_notif_status(cls):
        vals = [
            _rr(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings\\Windows.SystemToast.SecurityAndMaintenance', 'Enabled'),
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Associations', 'DefaultFileTypeRisk'),
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Attachments', 'SaveZoneInformation'),
        ]
        off = sum([vals[0] == 0, vals[1] == 6152, vals[2] == 1])
        return '已关闭' if off == 3 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_security_notif(cls):
        vals = [
            (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings\\Windows.SystemToast.SecurityAndMaintenance', 'Enabled', 0),
            (winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Associations', 'DefaultFileTypeRisk', 6152),
            (winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Attachments', 'SaveZoneInformation', 1),
        ]
        ok = True
        for h, p, n, v in vals:
            ok = _wr(h, p, n, v) and ok
        return (ok, '安全通知和文件警告已关闭' if ok else '安全通知设置未完全写入')

    @classmethod
    def enable_security_notif(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings\\Windows.SystemToast.SecurityAndMaintenance',
            'Enabled',
        )
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Associations',
            'DefaultFileTypeRisk',
        )
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Attachments',
            'SaveZoneInformation',
        )
        return (True, '安全通知已恢复')

    @classmethod
    def get_smartscreen_status(cls):
        a = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\System',
            'EnableSmartScreen',
        )
        b = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer',
            'SmartScreenEnabled',
        )
        off = sum([a == 0, str(b).lower() == 'off'])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_smartscreen(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\System',
            'EnableSmartScreen',
            0,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer',
            'SmartScreenEnabled',
            'Off',
            winreg.REG_SZ,
        )
        return (True, 'SmartScreen已关闭')

    @classmethod
    def enable_smartscreen(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\System', 'EnableSmartScreen')
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer',
            'SmartScreenEnabled',
            'Warn',
            winreg.REG_SZ,
        )
        return (True, 'SmartScreen已恢复')

    @classmethod
    def get_wpbt_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager',
            'DisableWpbtExecution',
        )
        return '已关闭' if v == 1 else '已开启'

    @classmethod
    def disable_wpbt(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager',
            'DisableWpbtExecution',
            1,
        )
        return (True, 'WPBT已禁用 (需重启)')

    @classmethod
    def enable_wpbt(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager',
            'DisableWpbtExecution',
            0,
        )
        return (True, 'WPBT已恢复')

    @classmethod
    def get_amsi_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\AMSI', 'AmsiEnable')
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_amsi(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\AMSI', 'AmsiEnable', 0)
        return (True, 'AMSI接口已禁用')

    @classmethod
    def enable_amsi(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\AMSI', 'AmsiEnable', 1)
        return (True, 'AMSI接口已恢复')

    @classmethod
    def get_code_integrity_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\DeviceGuard\\Scenarios\\HypervisorEnforcedCodeIntegrity',
            'Enabled',
        )
        v2 = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\CI\\Config',
            'VulnerableDriverBlocklistEnable',
        )
        off = sum([v == 0, v2 == 0])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_code_integrity(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\DeviceGuard\\Scenarios\\HypervisorEnforcedCodeIntegrity',
            'Enabled',
            0,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\CI\\Config',
            'VulnerableDriverBlocklistEnable',
            0,
        )
        return (True, '代码完整性/驱动黑名单已关闭 (需重启)')

    @classmethod
    def enable_code_integrity(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\DeviceGuard\\Scenarios\\HypervisorEnforcedCodeIntegrity',
            'Enabled',
            1,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\CI\\Config',
            'VulnerableDriverBlocklistEnable',
            1,
        )
        return (True, '代码完整性已恢复 (需重启)')

    @classmethod
    def get_uac_status(cls):
        a = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
            'EnableLUA',
        )
        b = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
            'ConsentPromptBehaviorAdmin',
        )
        off = sum([a == 0, b == 0])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_uac(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
            'EnableLUA',
            0,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
            'ConsentPromptBehaviorAdmin',
            0,
        )
        return (True, 'UAC已关闭 (需重启)')

    @classmethod
    def enable_uac(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
            'EnableLUA',
            1,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
            'ConsentPromptBehaviorAdmin',
            5,
        )
        return (True, 'UAC已恢复 (需重启)')

    @classmethod
    def get_spectre_status(cls):
        a = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management',
            'FeatureSettingsOverride',
        )
        b = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management',
            'FeatureSettingsOverrideMask',
        )
        off = sum([a == 3, b == 3])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_spectre(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management',
            'FeatureSettingsOverride',
            3,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management',
            'FeatureSettingsOverrideMask',
            3,
        )
        return (True, 'Spectre V2缓解已关闭 (需重启)')

    @classmethod
    def enable_spectre(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management',
            'FeatureSettingsOverride',
        )
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management',
            'FeatureSettingsOverrideMask',
        )
        return (True, 'Spectre V2缓解已恢复 (需重启)')
