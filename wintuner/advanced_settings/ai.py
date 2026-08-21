"""Copilot、Recall、Windows AI 服务以及 Edge/Paint/Notepad AI。"""

from __future__ import annotations

import winreg
from wintuner.core.state import _rr, _wr, _dr


class AISettingsMixin:
    """Copilot、Recall、Windows AI 服务以及 Edge/Paint/Notepad AI。"""

    @classmethod
    def get_copilot_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Policies\\Microsoft\\Windows\\WindowsCopilot',
            'TurnOffWindowsCopilot',
        )
        v2 = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot',
            'TurnOffWindowsCopilot',
        )
        return '已关闭' if v == 1 or v2 == 1 else '已开启'

    @classmethod
    def disable_copilot(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Policies\\Microsoft\\Windows\\WindowsCopilot',
            'TurnOffWindowsCopilot',
            1,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot',
            'TurnOffWindowsCopilot',
            1,
        )
        return (True, 'Windows Copilot已关闭')

    @classmethod
    def enable_copilot(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Policies\\Microsoft\\Windows\\WindowsCopilot',
            'TurnOffWindowsCopilot',
        )
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot',
            'TurnOffWindowsCopilot',
        )
        return (True, 'Windows Copilot已恢复')

    @classmethod
    def get_recall_status(cls):
        vals = [
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Policies\\Microsoft\\Windows\\WindowsAI', 'DisableAIDataAnalysis'),
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI', 'DisableAIDataAnalysis'),
            _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI', 'AllowRecallEnablement'),
        ]
        off = sum([vals[0] == 1, vals[1] == 1, vals[2] == 0])
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_recall(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Policies\\Microsoft\\Windows\\WindowsAI',
            'DisableAIDataAnalysis',
            1,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI',
            'DisableAIDataAnalysis',
            1,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI',
            'AllowRecallEnablement',
            0,
        )
        return (True, 'Windows Recall快照已关闭')

    @classmethod
    def enable_recall(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Policies\\Microsoft\\Windows\\WindowsAI',
            'DisableAIDataAnalysis',
        )
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI',
            'DisableAIDataAnalysis',
        )
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI',
            'AllowRecallEnablement',
        )
        return (True, 'Windows Recall已恢复')

    @classmethod
    def get_ai_svc_status(cls):
        st = cls.get_service_status('WSAIFabricSvc')
        if st == '未找到':
            return '未安装'
        if st == '已禁用':
            return '已关闭'
        if st.startswith('部分禁用'):
            return '部分关闭'
        return st

    @classmethod
    def disable_ai_svc(cls):
        return cls.disable_service('WSAIFabricSvc')

    @classmethod
    def enable_ai_svc(cls):
        return cls.enable_service('WSAIFabricSvc')

    @classmethod
    def get_edge_ai_status(cls):
        names = [
            'HubsSidebarEnabled',
            'CopilotCDPPageContext',
            'CopilotPageContext',
            'DiscoverPageContextEnabled',
            'ShowAcrobatSubscriptionButton',
        ]
        off = sum(
            (_rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', n) == 0 for n in names),
        )
        return '已关闭' if off == len(names) else f'部分关闭 ({off}/{len(names)})' if off else '已开启'

    @classmethod
    def disable_edge_ai(cls):
        for n, v in [('HubsSidebarEnabled', 0), ('CopilotCDPPageContext', 0), ('CopilotPageContext', 0), ('DiscoverPageContextEnabled', 0), ('ShowAcrobatSubscriptionButton', 0)]:
            _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', n, v)
        return (True, 'Edge AI/Copilot侧边栏已关闭')

    @classmethod
    def enable_edge_ai(cls):
        for n in ['HubsSidebarEnabled', 'CopilotCDPPageContext', 'CopilotPageContext', 'DiscoverPageContextEnabled', 'ShowAcrobatSubscriptionButton']:
            _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Edge', n)
        return (True, 'Edge AI功能已恢复')

    @classmethod
    def get_paint_ai_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Paint', 'DisableAIFeatures')
        return '已关闭' if v == 1 else '已开启'

    @classmethod
    def disable_paint_ai(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Paint', 'DisableAIFeatures', 1)
        return (True, 'Paint AI功能已关闭')

    @classmethod
    def enable_paint_ai(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Paint', 'DisableAIFeatures')
        return (True, 'Paint AI功能已恢复')

    @classmethod
    def get_notepad_ai_status(cls):
        v = _rr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Notepad', 'DisableAIFeatures')
        return '已关闭' if v == 1 else '已开启'

    @classmethod
    def disable_notepad_ai(cls):
        _wr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Notepad', 'DisableAIFeatures', 1)
        return (True, 'Notepad AI功能已关闭')

    @classmethod
    def enable_notepad_ai(cls):
        _dr(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Policies\\Microsoft\\Notepad', 'DisableAIFeatures')
        return (True, 'Notepad AI功能已恢复')
