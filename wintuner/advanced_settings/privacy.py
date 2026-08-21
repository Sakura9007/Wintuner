"""数据收集、广告、输入反馈、云语音与 Windows Error Reporting。"""

from __future__ import annotations

import winreg
from wintuner.core.constants import FEEDBACK_TASK_PATH
from wintuner.core.state import TaskTxn, _rr, _wr, _dr


class PrivacySettingsMixin:
    """数据收集、广告、输入反馈、云语音与 Windows Error Reporting。"""

    @classmethod
    def get_data_collection_status(cls):
        a = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection',
            'AllowTelemetry',
        )
        b = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection',
            'AllowTelemetry',
        )
        off = sum([a == 0, b == 0])
        return '已关闭' if off == 2 else '部分关闭' if off else '已开启'

    @classmethod
    def disable_data_collection(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection',
            'AllowTelemetry',
            0,
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection',
            'AllowTelemetry',
            0,
        )
        return (True, '诊断数据收集已关闭')

    @classmethod
    def enable_data_collection(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection',
            'AllowTelemetry',
        )
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection',
            'AllowTelemetry',
            1,
        )
        return (True, '诊断数据收集已恢复')

    @classmethod
    def get_license_telemetry_status(cls):
        v = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows NT\\CurrentVersion\\Software Protection Platform',
            'NoGenTicket',
        )
        return '已关闭' if v == 1 else '已开启'

    @classmethod
    def disable_license_telemetry(cls):
        _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows NT\\CurrentVersion\\Software Protection Platform',
            'NoGenTicket',
            1,
        )
        return (True, '许可证遥测已关闭')

    @classmethod
    def enable_license_telemetry(cls):
        _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows NT\\CurrentVersion\\Software Protection Platform',
            'NoGenTicket',
        )
        return (True, '许可证遥测已恢复')

    @classmethod
    def get_search_data_status(cls):
        vals = [
            _rr(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Policies\\Microsoft\\Windows\\Explorer', 'DisableSearchBoxSuggestions'),
            _rr(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Search', 'BingSearchEnabled'),
            _rr(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Search', 'CortanaConsent'),
        ]
        off = sum([vals[0] == 1, vals[1] == 0, vals[2] == 0])
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_search_data(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\Explorer',
            'DisableSearchBoxSuggestions',
            1,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Search',
            'BingSearchEnabled',
            0,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Search',
            'CortanaConsent',
            0,
        )
        return (True, '搜索数据收集/Bing搜索已关闭')

    @classmethod
    def enable_search_data(cls):
        _dr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\Explorer',
            'DisableSearchBoxSuggestions',
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Search',
            'BingSearchEnabled',
            1,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Search',
            'CortanaConsent',
            1,
        )
        return (True, '搜索数据收集已恢复')

    @classmethod
    def get_targeted_ads_status(cls):
        path = 'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager'
        names = [
            'SilentInstalledAppsEnabled',
            'SystemPaneSuggestionsEnabled',
            'SoftLandingEnabled',
            'SubscribedContent-310093Enabled',
            'SubscribedContent-338388Enabled',
            'SubscribedContent-338389Enabled',
        ]
        off = sum((_rr(winreg.HKEY_CURRENT_USER, path, n) == 0 for n in names))
        off += _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'ShowSyncProviderNotifications') == 0
        total = len(names) + 1
        return '已关闭' if off == total else f'部分关闭 ({off}/{total})' if off else '已开启'

    @classmethod
    def disable_targeted_ads(cls):
        names = [
            'SilentInstalledAppsEnabled',
            'SystemPaneSuggestionsEnabled',
            'SoftLandingEnabled',
            'SubscribedContent-310093Enabled',
            'SubscribedContent-338388Enabled',
            'SubscribedContent-338389Enabled',
        ]
        ms = []
        ok = True
        path = 'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager'
        for n in names:
            r = _wr(winreg.HKEY_CURRENT_USER, path, n, 0)
            ok = ok and r
            ms.append(f'  ✓ {n}=0' if r else f'  ✗ {n}')
        r = _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'ShowSyncProviderNotifications',
            0,
        )
        ok = ok and r
        return (ok, ('定向广告/静默安装已关闭:\n' if ok else '定向广告设置未完全写入:\n') + '\n'.join(ms))

    @classmethod
    def enable_targeted_ads(cls):
        for n in ['SilentInstalledAppsEnabled', 'SystemPaneSuggestionsEnabled', 'SoftLandingEnabled', 'SubscribedContent-310093Enabled', 'SubscribedContent-338388Enabled', 'SubscribedContent-338389Enabled']:
            _wr(
                winreg.HKEY_CURRENT_USER,
                'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
                n,
                1,
            )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'ShowSyncProviderNotifications',
            1,
        )
        return (True, '定向广告已恢复')

    @classmethod
    def get_input_feedback_status(cls):
        v = _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Input\\TIPC', 'Enabled')
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_input_feedback(cls):
        _wr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Input\\TIPC', 'Enabled', 0)
        return (True, '输入反馈遥测已关闭')

    @classmethod
    def enable_input_feedback(cls):
        _wr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Input\\TIPC', 'Enabled', 1)
        return (True, '输入反馈遥测已恢复')

    @classmethod
    def get_feedback_diag_status(cls):
        v = _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Siuf\\Rules', 'NumberOfSIUFInPeriod')
        states = [TaskTxn._query(FEEDBACK_TASK_PATH, n)[0] for n in ['DmClient', 'DmClientOnScenarioDownload']]
        if 'PROTECTED' in states:
            return '检测受限'
        if 'ERROR' in states:
            return '检测失败'
        off = sum((1 for x in states if x in ('DISABLED', 'MISSING')))
        return '已关闭' if v == 0 and off == 2 else '部分关闭' if v == 0 or off else '已开启'

    @classmethod
    def disable_feedback_diag(cls):
        r = _wr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Siuf\\Rules', 'NumberOfSIUFInPeriod', 0)
        ms = ['  ✓ NumberOfSIUFInPeriod=0' if r else '  ✗ 注册表写入失败']
        oks = [r]
        for n in ['DmClient', 'DmClientOnScenarioDownload']:
            ok, msg = TaskTxn.set_enabled(FEEDBACK_TASK_PATH, n, False)
            oks.append(ok)
            ms.append(('  ✓ ' if ok else '  ✗ ') + n + ': ' + msg)
        return (all(oks), ('Windows反馈和诊断已关闭:\n' if all(oks) else 'Windows反馈和诊断关闭不完整:\n') + '\n'.join(ms))

    @classmethod
    def enable_feedback_diag(cls):
        r = _dr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Siuf\\Rules', 'NumberOfSIUFInPeriod')
        ms = []
        oks = [r]
        for n in ['DmClient', 'DmClientOnScenarioDownload']:
            ok, msg = TaskTxn.set_enabled(FEEDBACK_TASK_PATH, n, True)
            oks.append(ok)
            ms.append(('  ✓ ' if ok else '  ✗ ') + n + ': ' + msg)
        return (all(oks), 'Windows反馈和诊断已启用' if all(oks) else 'Windows反馈和诊断启用不完整: ' + '; '.join(ms))

    @classmethod
    def get_cloud_speech_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Speech_OneCore\\Settings\\OnlineSpeechPrivacy',
            'HasAccepted',
        )
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_cloud_speech(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Speech_OneCore\\Settings\\OnlineSpeechPrivacy',
            'HasAccepted',
            0,
        )
        return (True, '云语音识别已关闭')

    @classmethod
    def enable_cloud_speech(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Speech_OneCore\\Settings\\OnlineSpeechPrivacy',
            'HasAccepted',
            1,
        )
        return (True, '云语音识别已恢复')

    @classmethod
    def get_wer_status(cls):
        p = _rr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Error Reporting',
            'Disabled',
        )
        s = cls.get_service_status('WerSvc')
        if s == '检测失败':
            return '检测失败'
        if p == 1 and s in ('已禁用', '未找到'):
            return '已关闭'
        if p == 1 or s == '已禁用':
            return '部分关闭'
        return '已开启'

    @classmethod
    def disable_wer(cls):
        r1 = _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Error Reporting',
            'Disabled',
            1,
        )
        r2 = _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting',
            'Disabled',
            1,
        )
        if _rr(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Services\\WerSvc', 'Start') is None:
            sok, smsg = (True, 'WerSvc 未安装，已跳过服务项')
        else:
            sok, smsg = cls.disable_service('WerSvc')
        ok = r1 and r2 and sok
        return (ok, 'Windows错误报告(WER)已关闭' if ok else f'WER关闭不完整: {smsg}')

    @classmethod
    def enable_wer(cls):
        r1 = _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Error Reporting',
            'Disabled',
        )
        r2 = _dr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting',
            'Disabled',
        )
        if _rr(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Services\\WerSvc', 'Start') is None:
            sok, smsg = (True, 'WerSvc 未安装，已跳过服务项')
        else:
            sok, smsg = cls.enable_service('WerSvc')
        ok = r1 and r2 and sok
        return (ok, 'Windows错误报告(WER)已恢复' if ok else f'WER恢复不完整: {smsg}')
