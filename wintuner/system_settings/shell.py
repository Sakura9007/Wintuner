"""右键菜单、任务栏与文件资源管理器设置。"""

from __future__ import annotations

import winreg
from wintuner.core.state import _rr, _wr, _dr


class ShellSettingsMixin:
    """右键菜单、任务栏与文件资源管理器设置。"""

    @classmethod
    def get_context_menu_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32',
            '',
        )
        return '已还原Win10' if v is not None else 'Win11默认'

    @classmethod
    def disable_context_menu(cls):
        ok = _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32',
            '',
            '',
            winreg.REG_SZ,
        )
        return (ok, '已还原Win10经典右键菜单 (需重启Explorer)' if ok else 'Win10右键菜单设置写入失败')

    @classmethod
    def enable_context_menu(cls):
        path = 'Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32'
        ok = _dr(winreg.HKEY_CURRENT_USER, path, '')
        if not ok:
            return (False, 'Win11右键菜单恢复失败')
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            pass
        try:
            winreg.DeleteKey(
                winreg.HKEY_CURRENT_USER,
                'Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}',
            )
        except OSError:
            pass
        return (True, '已恢复Win11默认右键菜单')

    @classmethod
    def get_taskbar_align_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarAl',
        )
        return '已左对齐' if v == 0 else '居中(默认)'

    @classmethod
    def disable_taskbar_center(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarAl',
            0,
        )
        return (True, '任务栏图标已左对齐')

    @classmethod
    def enable_taskbar_center(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarAl',
            1,
        )
        return (True, '任务栏图标已居中')

    @classmethod
    def get_taskview_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'ShowTaskViewButton',
        )
        return '已隐藏' if v == 0 else '已显示'

    @classmethod
    def disable_taskview(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'ShowTaskViewButton',
            0,
        )
        return (True, '任务视图按钮已隐藏')

    @classmethod
    def enable_taskview(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'ShowTaskViewButton',
            1,
        )
        return (True, '任务视图按钮已恢复')

    @classmethod
    def get_chat_icon_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarMn',
        )
        return '已隐藏' if v == 0 else '已显示'

    @classmethod
    def disable_chat_icon(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarMn',
            0,
        )
        return (True, 'Chat图标已隐藏')

    @classmethod
    def enable_chat_icon(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarMn',
            1,
        )
        return (True, 'Chat图标已恢复')

    @classmethod
    def get_end_task_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\\TaskbarDeveloperSettings',
            'TaskbarEndTask',
        )
        return '已启用' if v == 1 else '未启用'

    @classmethod
    def enable_end_task(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\\TaskbarDeveloperSettings',
            'TaskbarEndTask',
            1,
        )
        return (True, '任务栏右键「结束任务」已启用')

    @classmethod
    def disable_end_task(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\\TaskbarDeveloperSettings',
            'TaskbarEndTask',
            0,
        )
        return (True, '任务栏右键「结束任务」已关闭')

    @classmethod
    def get_file_ext_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'HideFileExt',
        )
        return '已显示' if v == 0 else '已隐藏'

    @classmethod
    def show_file_ext(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'HideFileExt',
            0,
        )
        return (True, '已知文件扩展名已显示')

    @classmethod
    def hide_file_ext(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'HideFileExt',
            1,
        )
        return (True, '已知文件扩展名已隐藏')

    @classmethod
    def get_hidden_files_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'Hidden',
        )
        return '已显示' if v == 1 else '已隐藏'

    @classmethod
    def show_hidden_files(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'Hidden',
            1,
        )
        return (True, '隐藏文件已显示')

    @classmethod
    def hide_hidden_files(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'Hidden',
            2,
        )
        return (True, '隐藏文件已恢复隐藏')

    @classmethod
    def get_explorer_thispc_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'LaunchTo',
        )
        return '此电脑' if v == 1 else '主页' if v == 2 else '默认'

    @classmethod
    def set_explorer_thispc(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'LaunchTo',
            1,
        )
        return (True, '文件资源管理器默认打开「此电脑」')

    @classmethod
    def set_explorer_home(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'LaunchTo',
            2,
        )
        return (True, '文件资源管理器默认打开「主页」')
