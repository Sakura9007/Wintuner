"""活动历史、位置、更新策略、锁屏提示与 Spotlight。"""

from __future__ import annotations

import winreg
from wintuner.core.state import _rr, _wr, _dr


class WindowsPolicySettingsMixin:
    """活动历史、位置、更新策略、锁屏提示与 Spotlight。"""

    @classmethod
    def get_activity_history_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\System',
            'PublishUserActivities',
        )
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_activity_history(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\System',
            'PublishUserActivities',
            0,
        )
        return (True, '活动历史记录已关闭')

    @classmethod
    def enable_activity_history(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\System',
            'PublishUserActivities',
        )
        return (True, '活动历史记录已恢复')

    @classmethod
    def get_tailored_exp_status(cls):
        vals = [
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Privacy', 'TailoredExperiencesWithDiagnosticDataEnabled'),
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\InputPersonalization', 'RestrictImplicitInkCollection'),
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\InputPersonalization', 'RestrictImplicitTextCollection'),
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\InputPersonalization\\TrainedDataStore', 'HarvestContacts'),
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Personalization\\Settings', 'AcceptedPrivacyPolicy'),
        ]
        off = sum([vals[0] == 0, vals[1] == 1, vals[2] == 1, vals[3] == 0, vals[4] == 0])
        return '已关闭' if off == 5 else f'部分关闭 ({off}/5)' if off else '已开启'

    @classmethod
    def disable_tailored_exp(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Privacy',
            'TailoredExperiencesWithDiagnosticDataEnabled',
            0,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\InputPersonalization',
            'RestrictImplicitInkCollection',
            1,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\InputPersonalization',
            'RestrictImplicitTextCollection',
            1,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\InputPersonalization\\TrainedDataStore',
            'HarvestContacts',
            0,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Personalization\\Settings',
            'AcceptedPrivacyPolicy',
            0,
        )
        return (True, '个性化体验和输入个性化已关闭')

    @classmethod
    def enable_tailored_exp(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Privacy',
            'TailoredExperiencesWithDiagnosticDataEnabled',
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\InputPersonalization',
            'RestrictImplicitInkCollection',
            0,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\InputPersonalization',
            'RestrictImplicitTextCollection',
            0,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\InputPersonalization\\TrainedDataStore',
            'HarvestContacts',
            1,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Personalization\\Settings',
            'AcceptedPrivacyPolicy',
            1,
        )
        return (True, '个性化体验已恢复')

    @classmethod
    def get_location_status(cls):
        vals = [
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors', 'DisableLocation'),
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors', 'DisableLocationScripting'),
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\location', 'Value'),
        ]
        off = sum([vals[0] == 1, vals[1] == 1, str(vals[2]).lower() == 'deny'])
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_location(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors',
            'DisableLocation',
            1,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors',
            'DisableLocationScripting',
            1,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\location',
            'Value',
            'Deny',
            winreg.REG_SZ,
        )
        return (True, 'Windows位置服务已关闭')

    @classmethod
    def enable_location(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors',
            'DisableLocation',
        )
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors',
            'DisableLocationScripting',
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\location',
            'Value',
            'Allow',
            winreg.REG_SZ,
        )
        return (True, 'Windows位置服务已恢复')

    @classmethod
    def get_findmydevice_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\FindMyDevice', 'AllowFindMyDevice')
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_findmydevice(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\FindMyDevice', 'AllowFindMyDevice', 0)
        return (True, '查找我的设备已关闭')

    @classmethod
    def enable_findmydevice(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\FindMyDevice', 'AllowFindMyDevice')
        return (True, '查找我的设备已恢复')

    @classmethod
    def get_update_restart_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU',
            'NoAutoRebootWithLoggedOnUsers',
        )
        return '已关闭' if v == 1 else '已开启'

    @classmethod
    def disable_update_restart(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU',
            'NoAutoRebootWithLoggedOnUsers',
            1,
        )
        return (True, '更新后自动重启已阻止')

    @classmethod
    def enable_update_restart(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU',
            'NoAutoRebootWithLoggedOnUsers',
        )
        return (True, '更新后自动重启已恢复')

    @classmethod
    def get_early_update_status(cls):
        a = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate',
            'DeferFeatureUpdatesPeriodInDays',
        )
        b = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate',
            'DeferQualityUpdatesPeriodInDays',
        )
        off = sum([isinstance(a, int) and a > 0, isinstance(b, int) and b > 0])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_early_update(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate',
            'DeferFeatureUpdatesPeriodInDays',
            30,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate',
            'DeferQualityUpdatesPeriodInDays',
            7,
        )
        return (True, '已延迟接收新更新')

    @classmethod
    def enable_early_update(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate',
            'DeferFeatureUpdatesPeriodInDays',
        )
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate',
            'DeferQualityUpdatesPeriodInDays',
        )
        return (True, '更新延迟已取消')

    @classmethod
    def get_lockscreen_tips_status(cls):
        path = 'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager'
        vals = [
            _rr(winreg.HKEY_CURRENT_USER, path, 'RotatingLockScreenEnabled'),
            _rr(winreg.HKEY_CURRENT_USER, path, 'RotatingLockScreenOverlayEnabled'),
            _rr(winreg.HKEY_CURRENT_USER, path, 'SubscribedContent-338387Enabled'),
        ]
        off = sum((v == 0 for v in vals))
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_lockscreen_tips(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
            'RotatingLockScreenEnabled',
            0,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
            'RotatingLockScreenOverlayEnabled',
            0,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
            'SubscribedContent-338387Enabled',
            0,
        )
        return (True, '锁屏界面提示和广告已关闭')

    @classmethod
    def enable_lockscreen_tips(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
            'RotatingLockScreenEnabled',
        )
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
            'RotatingLockScreenOverlayEnabled',
        )
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
            'SubscribedContent-338387Enabled',
        )
        return (True, '锁屏界面提示已恢复')

    @classmethod
    def get_desktop_spotlight_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\HideDesktopIcons\\NewStartPanel',
            '{2cc5ca98-6485-489a-920e-b3e88a6ccce3}',
        )
        return '已关闭' if v == 1 else '已开启'

    @classmethod
    def disable_desktop_spotlight(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\HideDesktopIcons\\NewStartPanel',
            '{2cc5ca98-6485-489a-920e-b3e88a6ccce3}',
            1,
        )
        return (True, '桌面Spotlight已关闭')

    @classmethod
    def enable_desktop_spotlight(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\HideDesktopIcons\\NewStartPanel',
            '{2cc5ca98-6485-489a-920e-b3e88a6ccce3}',
        )
        return (True, '桌面Spotlight已恢复')

    @classmethod
    def _reg_toggle_status(cls, items):
        off = 0
        for h, p, n, ov in items:
            if _rr(h, p, n) == ov:
                off += 1
        return '已关闭' if off == len(items) else '部分关闭' if off > 0 else '已开启'

    @classmethod
    def _reg_set_all(cls, items, msg_off):
        ms = []
        ok = True
        for h, p, n, v in items:
            r = _wr(h, p, n, v)
            ok = ok and r
            ms.append(f'  ✓ {n}={v}' if r else f'  ✗ {n}')
        return (ok, f'{msg_off}:\n' + '\n'.join(ms))

    @classmethod
    def _reg_del_all(cls, items, msg_on):
        ms = []
        ok = True
        for h, p, n, _ in items:
            r = _dr(h, p, n)
            ok = ok and r
            ms.append(f'  ✓ {n} 已恢复默认' if r else f'  ✗ {n} 删除失败')
        return (ok, f'{msg_on}:\n' + '\n'.join(ms))
