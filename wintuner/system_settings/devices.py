"""即插即用设备、BitLocker、传递优化与基础隐私。"""

from __future__ import annotations

import json
import os
import winreg
from wintuner.core.constants import DEVICES_TO_MANAGE, PRIVACY_GENERAL_ITEMS
from wintuner.core.runtime import _DETECT_CTX, _PNP_DETECT_KEY, _PNP_DETECT_LOCK, _PNP_DETECT_ROWS, _system_generation
from wintuner.core.state import StateTxn, _rr, _wr


class DeviceSettingsMixin:
    """即插即用设备、BitLocker、传递优化与基础隐私。"""

    @classmethod
    def _pnp_devices(cls, hw):
        q = hw.replace("'", "''")
        script = f"$d=@(Get-PnpDevice -ErrorAction Stop|Where-Object{{$_.InstanceId -like '*{q}*'}}|Select-Object InstanceId,Status,Problem);if(-not $d){{'[]'}}else{{$d|ConvertTo-Json -Compress}}"
        c, o, e = cls.run_ps(script)
        if c != 0 or not o.strip():
            return None
        try:
            data = json.loads(o)
            items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            out = []
            for x in items:
                problem = str(x.get('Problem', '')).upper()
                status = str(x.get('Status', '')).upper()
                disabled = 'DISABLED' in problem or problem in ('22', 'CM_PROB_DISABLED')
                out.append(
                    {'id': str(x.get('InstanceId', '')), 'status': status, 'problem': problem, 'disabled': disabled},
                )
            return [x for x in out if x['id']]
        except Exception:
            return None

    @classmethod
    def _pnp_detection_rows(cls):
        global _PNP_DETECT_KEY, _PNP_DETECT_ROWS
        batch = getattr(_DETECT_CTX, 'batch_id', None)
        if batch is None:
            return None
        key = (_system_generation(), batch)
        with _PNP_DETECT_LOCK:
            if _PNP_DETECT_KEY == key:
                return _PNP_DETECT_ROWS
            targets = tuple((hw for _, hw in DEVICES_TO_MANAGE))
            joined = "','".join((x.replace("'", "''") for x in targets))
            script = f"$targets=@('{joined}');$d=@(Get-PnpDevice -ErrorAction Stop|Where-Object{{$id=[string]$_.InstanceId;$hit=$false;foreach($q in $targets){{if($id -like ('*'+$q+'*')){{$hit=$true;break}}}};$hit}}|Select-Object InstanceId,Status,Problem);if(-not $d){{'[]'}}else{{$d|ConvertTo-Json -Compress}}"
            c, o, e = cls.run_ps(script)
            rows = None
            if c == 0 and o.strip():
                try:
                    data = json.loads(o)
                    items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
                    rows = []
                    for x in items:
                        iid = str(x.get('InstanceId', ''))
                        problem = str(x.get('Problem', '')).upper()
                        status = str(x.get('Status', '')).upper()
                        disabled = 'DISABLED' in problem or problem in ('22', 'CM_PROB_DISABLED')
                        if iid:
                            rows.append(
                                {'id': iid, 'status': status, 'problem': problem, 'disabled': disabled},
                            )
                except Exception:
                    rows = None
            _PNP_DETECT_KEY = key
            _PNP_DETECT_ROWS = rows
            return rows

    @classmethod
    def get_device_status_detect(cls, hw):
        if getattr(_DETECT_CTX, 'batch_id', None) is None:
            return cls.get_device_status(hw)
        rows = cls._pnp_detection_rows()
        if rows is None:
            return '检测失败'
        key = str(hw).lower()
        devices = [x for x in rows if key in x['id'].lower()]
        if not devices:
            return '未找到'
        disabled = sum((x['disabled'] for x in devices))
        healthy = sum((x['status'] == 'OK' and (not x['disabled']) for x in devices))
        n = len(devices)
        if disabled == n:
            return '已禁用'
        if disabled:
            return f'部分禁用 ({disabled}/{n})'
        if healthy == n:
            return '已启用'
        return '状态异常'

    @classmethod
    def get_device_status(cls, hw):
        devices = cls._pnp_devices(hw)
        if devices is None:
            return '检测失败'
        if not devices:
            return '未找到'
        disabled = sum((x['disabled'] for x in devices))
        healthy = sum((x['status'] == 'OK' and (not x['disabled']) for x in devices))
        n = len(devices)
        if disabled == n:
            return '已禁用'
        if disabled:
            return f'部分禁用 ({disabled}/{n})'
        if healthy == n:
            return '已启用'
        return '状态异常'

    @classmethod
    def disable_device(cls, hw):
        devices = cls._pnp_devices(hw)
        if devices is None:
            return (False, f'设备 [{hw}] 原始状态检测失败，已拒绝修改')
        if not devices:
            return (False, f'设备 [{hw}] 未找到')
        key = 'device::' + hw
        snap = [{'id': x['id'], 'disabled': bool(x['disabled'])} for x in devices]
        if not StateTxn.save_once(key, snap):
            return (False, f'设备 [{hw}] 原始状态快照保存失败，已拒绝修改')
        errs = []
        for x in devices:
            q = x['id'].replace("'", "''")
            (c, o, e) = cls.run_ps(
                f"Get-PnpDevice -InstanceId '{q}' -ErrorAction Stop|Disable-PnpDevice -Confirm:$false -ErrorAction Stop",
            )
            if c != 0:
                errs.append(f"{x['id']}: {e or o}")
        after = cls._pnp_devices(hw)
        ok = not errs and after is not None and after and all((x['disabled'] for x in after))
        return (ok, f'设备 [{hw}] 已禁用' if ok else f'设备 [{hw}] 禁用未完全生效: ' + ('; '.join(errs[:3]) or '状态验证失败'))

    @classmethod
    def enable_device(cls, hw):
        key = 'device::' + hw
        snap = StateTxn.get(key)
        current = cls._pnp_devices(hw)
        if current is None:
            return (False, f'设备 [{hw}] 当前状态检测失败')
        if not current:
            return (False, f'设备 [{hw}] 未找到')
        if isinstance(snap, list):
            expected = {str(x.get('id')): bool(x.get('disabled')) for x in snap if x.get('id')}
            errs = []
            for instance, was_disabled in expected.items():
                q = instance.replace("'", "''")
                cmd = 'Disable-PnpDevice' if was_disabled else 'Enable-PnpDevice'
                (c, o, e) = cls.run_ps(
                    f"Get-PnpDevice -InstanceId '{q}' -ErrorAction Stop|{cmd} -Confirm:$false -ErrorAction Stop",
                )
                if c != 0:
                    errs.append(f'{instance}: {e or o}')
            after = cls._pnp_devices(hw)
            actual = {x['id']: bool(x['disabled']) for x in after or []}
            ok = not errs and all((actual.get(k) == v for k, v in expected.items()))
            if ok and (not StateTxn.clear(key)):
                return (False, f'设备 [{hw}] 已恢复，但无法安全清除恢复快照')
            return (ok, f'设备 [{hw}] 已严格恢复到修改前状态' if ok else f'设备 [{hw}] 恢复不完整: ' + ('; '.join(errs[:3]) or '状态验证失败'))
        errs = []
        for x in current:
            q = x['id'].replace("'", "''")
            (c, o, e) = cls.run_ps(
                f"Get-PnpDevice -InstanceId '{q}' -ErrorAction Stop|Enable-PnpDevice -Confirm:$false -ErrorAction Stop",
            )
            if c != 0:
                errs.append(f"{x['id']}: {e or o}")
        st = cls.get_device_status(hw)
        ok = not errs and st == '已启用'
        return (ok, f'设备 [{hw}] 未找到历史快照，已按显式启用处理' if ok else f'设备 [{hw}] 启用失败: ' + ('; '.join(errs[:3]) or f'当前: {st}'))

    @classmethod
    def get_bitlocker_status(cls):
        drive = os.environ.get('SystemDrive', 'C:')
        c, o, _ = cls.run_cmd(f'manage-bde -status "{drive}"')
        if c != 0:
            return '检测失败'
        lo = o.lower()
        return '已开启' if 'protection on' in lo or '保护已打开' in lo or 'protection status: protection on' in lo else '未加密'

    @classmethod
    def disable_bitlocker(cls):
        drive = os.environ.get('SystemDrive', 'C:')
        c, o, e = cls.run_cmd(f'manage-bde -off "{drive}"', 60)
        if c == 0:
            return (True, f'BitLocker 正在后台解密 {drive}')
        if '80310008' in (o + e).upper():
            return (False, f'{drive} 未启用 BitLocker，当前无需操作')
        return (False, f'关闭失败 (错误码: {c}): {e or o}')

    @classmethod
    def open_bitlocker_settings(cls):
        cls.run_cmd('control /name Microsoft.BitLockerDriveEncryption')

    @classmethod
    def get_delivery_opt_status(cls):
        for p in ['SOFTWARE\\Policies\\Microsoft\\Windows\\DeliveryOptimization', 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\DeliveryOptimization\\Config']:
            try:
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, p, 0, winreg.KEY_READ)
                v, _ = winreg.QueryValueEx(k, 'DODownloadMode')
                winreg.CloseKey(k)
                return '已关闭' if v == 0 else '已开启'
            except Exception:
                continue
        return '已开启'

    @classmethod
    def disable_delivery_opt(cls):
        ok = _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\DeliveryOptimization',
            'DODownloadMode',
            0,
        )
        return (ok, '传递优化已关闭' if ok else '关闭失败: 无法写入 DODownloadMode')

    @classmethod
    def enable_delivery_opt(cls):
        ok = _wr(
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Policies\\Microsoft\\Windows\\DeliveryOptimization',
            'DODownloadMode',
            1,
        )
        return (ok, '传递优化已恢复' if ok else '恢复失败: 无法写入 DODownloadMode')

    @classmethod
    def get_privacy_status(cls):
        off = sum((1 for h, p, n, ov, _, __ in PRIVACY_GENERAL_ITEMS if _rr(h, p, n) == ov))
        t = len(PRIVACY_GENERAL_ITEMS)
        return '已全部关闭' if off == t else f'部分关闭 ({off}/{t})' if off > 0 else '全部开启'

    @classmethod
    def disable_privacy_general(cls):
        ms = []
        ok = True
        for h, p, n, ov, _, d in PRIVACY_GENERAL_ITEMS:
            r = _wr(h, p, n, ov)
            ok = ok and r
            ms.append(f'  ✓ {d}' if r else f'  ✗ {d}')
        return (ok, ('隐私常规项已关闭:\n' if ok else '隐私常规项未完全关闭:\n') + '\n'.join(ms))

    @classmethod
    def enable_privacy_general(cls):
        ms = []
        ok = True
        for h, p, n, _, onv, d in PRIVACY_GENERAL_ITEMS:
            r = _wr(h, p, n, onv)
            ok = ok and r
            ms.append(f'  ✓ {d}' if r else f'  ✗ {d}')
        return (ok, ('隐私常规项已恢复:\n' if ok else '隐私常规项恢复不完整:\n') + '\n'.join(ms))
