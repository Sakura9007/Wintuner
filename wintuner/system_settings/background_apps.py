"""后台应用、系统服务、同步与启动体验。"""

from __future__ import annotations

import winreg
from wintuner.core.constants import SETTING_SYNC_TASK_PATH
from wintuner.core.state import TaskTxn, _rr, _wr, _dr


class BackgroundAppsSettingsMixin:
    """后台应用、系统服务、同步与启动体验。"""

    @classmethod
    def get_auto_update_apps_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsStore\\WindowsUpdate',
            'AutoDownload',
        )
        return '已关闭' if v == 2 else '已开启'

    @classmethod
    def disable_auto_update_apps(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsStore\\WindowsUpdate',
            'AutoDownload',
            2,
        )
        return (True, '系统启动时自动更新应用程序已关闭')

    @classmethod
    def enable_auto_update_apps(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsStore\\WindowsUpdate',
            'AutoDownload',
            4,
        )
        return (True, '系统启动时自动更新应用程序已恢复')

    @classmethod
    def get_uwp_background_status(cls):
        a = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\BackgroundAccessApplications',
            'GlobalUserDisabled',
        )
        b = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Search',
            'BackgroundAppGlobalToggle',
        )
        off = sum([a == 1, b == 0])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_uwp_background(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\BackgroundAccessApplications',
            'GlobalUserDisabled',
            1,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Search',
            'BackgroundAppGlobalToggle',
            0,
        )
        return (True, 'UWP后台运行已关闭')

    @classmethod
    def enable_uwp_background(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\BackgroundAccessApplications',
            'GlobalUserDisabled',
            0,
        )
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Search',
            'BackgroundAppGlobalToggle',
        )
        return (True, 'UWP后台运行已恢复')

    @classmethod
    def get_offline_maps_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\Maps', 'AutoUpdateEnabled')
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_offline_maps(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\Maps', 'AutoUpdateEnabled', 0)
        return (True, '离线地图自动更新已关闭')

    @classmethod
    def enable_offline_maps(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\Maps', 'AutoUpdateEnabled', 1)
        return (True, '离线地图自动更新已恢复')

    @classmethod
    def get_store_auto_update_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\WindowsStore', 'AutoDownload')
        return '已关闭' if v == 2 else '已开启'

    @classmethod
    def disable_store_auto_update(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\WindowsStore', 'AutoDownload', 2)
        return (True, 'Microsoft Store后台自动更新已关闭')

    @classmethod
    def enable_store_auto_update(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\WindowsStore', 'AutoDownload')
        return (True, 'Microsoft Store后台自动更新已恢复')

    @classmethod
    def get_indexing_status(cls):
        st = cls.get_service_status('WSearch')
        if st in ('未找到', '检测失败'):
            return st
        return '已关闭' if st == '已禁用' else '已停止' if st == '已停止' else '已开启'

    @classmethod
    def disable_indexing(cls):
        return cls.disable_service('WSearch')

    @classmethod
    def enable_indexing(cls):
        return cls.enable_service('WSearch')

    @classmethod
    def get_edge_startup_status(cls):
        vals = [
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', 'StartupBoostEnabled'),
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\MicrosoftEdge\\Main', 'AllowPrelaunch'),
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', 'BackgroundModeEnabled'),
        ]
        off = sum((v == 0 for v in vals))
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_edge_startup(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', 'StartupBoostEnabled', 0)
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\MicrosoftEdge\\Main',
            'AllowPrelaunch',
            0,
        )
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', 'BackgroundModeEnabled', 0)
        return (True, 'Edge启动加速和后台运行已关闭')

    @classmethod
    def enable_edge_startup(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', 'StartupBoostEnabled')
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\MicrosoftEdge\\Main', 'AllowPrelaunch')
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', 'BackgroundModeEnabled')
        return (True, 'Edge启动加速和后台运行已恢复')

    @classmethod
    def get_fast_startup_delay_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Serialize',
            'StartupDelayInMSec',
        )
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_fast_startup_delay(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Serialize',
            'StartupDelayInMSec',
            0,
        )
        return (True, '启动延迟已消除 (StartupDelayInMSec=0)')

    @classmethod
    def enable_fast_startup_delay(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Serialize',
            'StartupDelayInMSec',
        )
        return (True, '启动延迟已恢复默认')

    @classmethod
    def get_cloud_sync_status(cls):
        a = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync',
            'DisableSettingSync',
        )
        b = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync',
            'DisableSettingSyncUserOverride',
        )
        off = sum([a == 2, b == 1])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_cloud_sync(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync',
            'DisableSettingSync',
            2,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync',
            'DisableSettingSyncUserOverride',
            1,
        )
        return (True, '云同步已关闭')

    @classmethod
    def enable_cloud_sync(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync',
            'DisableSettingSync',
        )
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync',
            'DisableSettingSyncUserOverride',
        )
        return (True, '云同步已恢复')

    @classmethod
    def get_printer_device_status(cls):
        st = cls.get_service_status('Spooler')
        if st in ('未找到', '检测失败'):
            return st
        return '已关闭' if st == '已禁用' else '已停止' if st == '已停止' else '已开启'

    @classmethod
    def disable_printer_device(cls):
        return cls.disable_service('Spooler')

    @classmethod
    def enable_printer_device(cls):
        return cls.enable_service('Spooler')

    @classmethod
    def get_ms_sync_status(cls):
        names = [
            'DisableApplicationSettingSync',
            'DisableWebBrowserSettingSync',
            'DisableDesktopThemeSettingSync',
            'DisablePersonalizationSettingSync',
            'DisableStartLayoutSettingSync',
        ]
        off = sum(
            (_rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync', n) == 2 for n in names),
        )
        st, _ = TaskTxn._query(SETTING_SYNC_TASK_PATH, 'BackgroundUploadTask')
        if st == 'PROTECTED':
            return '检测受限'
        if st == 'ERROR':
            return '检测失败'
        if st in ('DISABLED', 'MISSING'):
            off += 1
        total = len(names) + 1
        return '已关闭' if off == total else f'部分关闭 ({off}/{total})' if off else '已开启'

    @classmethod
    def disable_ms_sync(cls):
        ok = True
        for n in ['DisableApplicationSettingSync', 'DisableWebBrowserSettingSync', 'DisableDesktopThemeSettingSync', 'DisablePersonalizationSettingSync', 'DisableStartLayoutSettingSync']:
            ok = _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync', n, 2) and ok
        tok, tmsg = TaskTxn.set_enabled(SETTING_SYNC_TASK_PATH, 'BackgroundUploadTask', False)
        ok = ok and tok
        return (ok, 'Microsoft账户同步已关闭' if ok else 'Microsoft账户同步关闭不完整: ' + tmsg)

    @classmethod
    def enable_ms_sync(cls):
        ok = True
        for n in ['DisableApplicationSettingSync', 'DisableWebBrowserSettingSync', 'DisableDesktopThemeSettingSync', 'DisablePersonalizationSettingSync', 'DisableStartLayoutSettingSync']:
            ok = _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\SettingSync', n) and ok
        tok, tmsg = TaskTxn.set_enabled(SETTING_SYNC_TASK_PATH, 'BackgroundUploadTask', True)
        ok = ok and tok
        return (ok, 'Microsoft账户同步已恢复' if ok else 'Microsoft账户同步恢复不完整: ' + tmsg)

    @classmethod
    def get_fast_boot_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power',
            'HiberbootEnabled',
        )
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_fast_boot(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power',
            'HiberbootEnabled',
            0,
        )
        return (True, '快速启动已关闭')

    @classmethod
    def enable_fast_boot(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power',
            'HiberbootEnabled',
            1,
        )
        return (True, '快速启动已恢复')

    @classmethod
    def get_widgets_status(cls):
        a = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Dsh', 'AllowNewsAndInterests')
        b = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarDa',
        )
        off = sum([a == 0, b == 0])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_widgets(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Dsh', 'AllowNewsAndInterests', 0)
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarDa',
            0,
        )
        return (True, 'Win11小部件面板已关闭')

    @classmethod
    def enable_widgets(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Dsh', 'AllowNewsAndInterests')
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarDa',
            1,
        )
        return (True, 'Win11小部件面板已恢复')
