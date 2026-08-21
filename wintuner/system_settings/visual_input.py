"""视觉效果、鼠标、粘滞键、透明与动画。"""

from __future__ import annotations

import winreg
from wintuner.core.state import SecureState, RegistryTxn, _rr, _wr


class VisualInputSettingsMixin:
    """视觉效果、鼠标、粘滞键、透明与动画。"""

    @classmethod
    def get_visual_fx_status(cls):
        vals = [
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects', 'VisualFXSetting'),
            _rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Desktop', 'FontSmoothing'),
            _rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Desktop', 'FontSmoothingType'),
            _rr(winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'ListviewShadow'),
        ]
        ok = sum([vals[0] == 2, str(vals[1]) == '2', vals[2] == 2, vals[3] == 1])
        return '已设置' if ok == 4 else f'部分设置 ({ok}/4)' if ok else '未设置'

    @classmethod
    def set_best_performance(cls):
        ms = []
        ok = True
        r = _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects',
            'VisualFXSetting',
            2,
        )
        ok = ok and r
        ms.append('  ✓ 视觉效果 → 最佳性能' if r else '  ✗ 视觉效果写入失败')
        r1 = _wr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Desktop', 'FontSmoothing', '2', winreg.REG_SZ)
        r2 = _wr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Desktop', 'FontSmoothingType', 2)
        ok = ok and r1 and r2
        ms.append('  ✓ 平滑屏幕字体边缘 → 已启用' if r1 and r2 else '  ✗ 字体平滑写入失败')
        r3 = _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'ListviewShadow',
            1,
        )
        ok = ok and r3
        ms.append('  ✓ 桌面图标标签阴影 → 已启用' if r3 else '  ✗ 图标阴影写入失败')
        cls.run_cmd('RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters ,1 ,True')
        return (ok, ('性能视觉设置完成 (部分需注销生效):\n' if ok else '性能视觉设置未完全写入:\n') + '\n'.join(ms))

    @classmethod
    def get_mouse_accel_status(cls):
        vals = [str(_rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Mouse', n)) for n in ['MouseSpeed', 'MouseThreshold1', 'MouseThreshold2']]
        off = sum([vals[0] == '0', vals[1] == '0', vals[2] == '0'])
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_mouse_accel(cls):
        ms = []
        for n, v in [('MouseSpeed', '0'), ('MouseThreshold1', '0'), ('MouseThreshold2', '0')]:
            ms.append(
                f'  ✓ {n}={v}' if _wr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Mouse', n, v, winreg.REG_SZ) else f'  ✗ {n}',
            )
        cls.run_cmd('RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters ,1 ,True')
        return (True, '鼠标加速已关闭 (线性1:1移动):\n' + '\n'.join(ms))

    @classmethod
    def enable_mouse_accel(cls):
        for n, v in [('MouseSpeed', '1'), ('MouseThreshold1', '6'), ('MouseThreshold2', '10')]:
            _wr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Mouse', n, v, winreg.REG_SZ)
        cls.run_cmd('RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters ,1 ,True')
        return (True, '鼠标加速已恢复默认')

    @classmethod
    def get_sticky_keys_status(cls):
        vals = [
            str(_rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Accessibility\\StickyKeys', 'Flags')),
            str(_rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Accessibility\\ToggleKeys', 'Flags')),
            str(_rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Accessibility\\Keyboard Response', 'Flags')),
        ]
        off = sum([vals[0] == '506', vals[1] == '58', vals[2] == '122'])
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_sticky_keys(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Accessibility\\StickyKeys',
            'Flags',
            '506',
            winreg.REG_SZ,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Accessibility\\ToggleKeys',
            'Flags',
            '58',
            winreg.REG_SZ,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Accessibility\\Keyboard Response',
            'Flags',
            '122',
            winreg.REG_SZ,
        )
        return (True, '粘滞键/切换键/筛选键快捷方式已关闭')

    @classmethod
    def enable_sticky_keys(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Accessibility\\StickyKeys',
            'Flags',
            '510',
            winreg.REG_SZ,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Accessibility\\ToggleKeys',
            'Flags',
            '62',
            winreg.REG_SZ,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Accessibility\\Keyboard Response',
            'Flags',
            '126',
            winreg.REG_SZ,
        )
        return (True, '粘滞键/切换键/筛选键快捷方式已恢复')

    @classmethod
    def get_transparency_status(cls):
        v = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',
            'EnableTransparency',
        )
        return '已关闭' if v == 0 else '已开启'

    @classmethod
    def disable_transparency(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',
            'EnableTransparency',
            0,
        )
        return (True, '透明效果已关闭')

    @classmethod
    def enable_transparency(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',
            'EnableTransparency',
            1,
        )
        return (True, '透明效果已恢复')

    @classmethod
    def get_animation_status(cls):
        a = str(_rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Desktop\\WindowMetrics', 'MinAnimate'))
        b = _rr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarAnimations',
        )
        c = _rr(winreg.HKEY_CURRENT_USER, 'Control Panel\\Desktop', 'UserPreferencesMask')
        mask = bytes([144, 18, 3, 128, 16, 0, 0, 0])
        off = sum([a == '0', b == 0, c == mask])
        return '已关闭' if off == 3 else f'部分关闭 ({off}/3)' if off else '已开启'

    @classmethod
    def disable_animation(cls):
        r1 = _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Desktop\\WindowMetrics',
            'MinAnimate',
            '0',
            winreg.REG_SZ,
        )
        r2 = _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarAnimations',
            0,
        )
        mask = bytes([144, 18, 3, 128, 16, 0, 0, 0])
        r3 = _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Desktop',
            'UserPreferencesMask',
            mask,
            winreg.REG_BINARY,
        )
        ok = r1 and r2 and r3
        return (ok, '动画和视觉特效已关闭 (需重启)' if ok else '动画和视觉特效设置未完全写入')

    @classmethod
    def enable_animation(cls):
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Control Panel\\Desktop\\WindowMetrics',
            'MinAnimate',
            '1',
            winreg.REG_SZ,
        )
        _wr(
            winreg.HKEY_CURRENT_USER,
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
            'TaskbarAnimations',
            1,
        )
        if SecureState.get(RegistryTxn._key('animation')) is None:
            return (False, '前两项已恢复，但没有 tx-v4 保存的 UserPreferencesMask 原值，已拒绝猜测该二进制值')
        return (True, '动画和视觉特效恢复步骤完成，UserPreferencesMask 将按快照精确还原')
