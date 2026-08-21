"""Synaptics 蠕虫/残留扫描、签名验证与保守清理。"""

from __future__ import annotations

import ctypes
import os
import winreg


class SynapticsCleanupMixin:
    """Synaptics 蠕虫/残留扫描、签名验证与保守清理。"""

    @classmethod
    def _process_paths_by_name(cls, exe_name):
        results = []
        errors = []
        try:
            TH32CS_SNAPPROCESS = 2
            PROCESS_QUERY_LIMITED_INFORMATION = 4096

            class PROCESSENTRY32W(ctypes.Structure):
                _fields_ = [
                    ('dwSize', ctypes.c_ulong),
                    ('cntUsage', ctypes.c_ulong),
                    ('th32ProcessID', ctypes.c_ulong),
                    ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                    ('th32ModuleID', ctypes.c_ulong),
                    ('cntThreads', ctypes.c_ulong),
                    ('th32ParentProcessID', ctypes.c_ulong),
                    ('pcPriClassBase', ctypes.c_long),
                    ('dwFlags', ctypes.c_ulong),
                    ('szExeFile', ctypes.c_wchar * 260),
                ]
            k = ctypes.windll.kernel32
            k.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
            k.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
            k.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
            k.OpenProcess.restype = ctypes.c_void_p
            k.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            k.QueryFullProcessImageNameW.restype = ctypes.c_bool
            k.CloseHandle.argtypes = [ctypes.c_void_p]
            k.CloseHandle.restype = ctypes.c_bool
            snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            invalid = ctypes.c_void_p(-1).value
            if not snap or snap == invalid:
                return ([], ['无法创建进程快照'])
            try:
                pe = PROCESSENTRY32W()
                pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
                first = k.Process32FirstW
                first.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
                first.restype = ctypes.c_bool
                nxt = k.Process32NextW
                nxt.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
                nxt.restype = ctypes.c_bool
                ok = first(snap, ctypes.byref(pe))
                target = str(exe_name).lower()
                while ok:
                    if str(pe.szExeFile).lower() == target:
                        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pe.th32ProcessID)
                        if h:
                            try:
                                size = ctypes.c_ulong(32768)
                                buf = ctypes.create_unicode_buffer(size.value)
                                if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                                    results.append((int(pe.th32ProcessID), buf.value))
                                else:
                                    errors.append(f'PID {int(pe.th32ProcessID)} 路径读取失败，已安全跳过')
                            finally:
                                k.CloseHandle(h)
                        else:
                            errors.append(f'PID {int(pe.th32ProcessID)} 无法读取进程路径，已安全跳过')
                    ok = nxt(snap, ctypes.byref(pe))
            finally:
                k.CloseHandle(snap)
        except Exception as e:
            errors.append(str(e))
        return (results, errors)

    @classmethod
    def _terminate_process_exact(cls, pid, path):
        try:
            k = ctypes.windll.kernel32
            PROCESS_TERMINATE = 1
            PROCESS_QUERY_LIMITED_INFORMATION = 4096
            k.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
            k.OpenProcess.restype = ctypes.c_void_p
            k.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            k.QueryFullProcessImageNameW.restype = ctypes.c_bool
            k.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            k.TerminateProcess.restype = ctypes.c_bool
            k.CloseHandle.argtypes = [ctypes.c_void_p]
            k.CloseHandle.restype = ctypes.c_bool
            h = k.OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not h:
                return (False, '无法打开进程')
            try:
                size = ctypes.c_ulong(32768)
                buf = ctypes.create_unicode_buffer(size.value)
                if not k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                    return (False, '无法复核进程路径')
                if os.path.normcase(buf.value) != os.path.normcase(path):
                    return (False, '进程路径已变化，已跳过')
                return (True, '') if k.TerminateProcess(h, 1) else (False, 'TerminateProcess 失败')
            finally:
                k.CloseHandle(h)
        except Exception as e:
            return (False, str(e))

    @classmethod
    def _synaptics_findings(cls):
        candidates = [
            os.path.expandvars('%APPDATA%\\Synaptics\\Synaptics.exe'),
            os.path.expandvars('%ProgramData%\\Synaptics\\Synaptics.exe'),
            os.path.expandvars('%LOCALAPPDATA%\\Synaptics\\Synaptics.exe'),
            os.path.expandvars('%TEMP%\\Synaptics.exe'),
        ]
        suspicious = []
        trusted = []
        unverified = []
        errors = []
        for p in candidates:
            if not os.path.isfile(p):
                continue
            q = p.replace("'", "''")
            (c, o, e) = cls.run_ps(
                f"$s=Get-AuthenticodeSignature -LiteralPath '{q}' -ErrorAction Stop;$sub=if($s.SignerCertificate){{$s.SignerCertificate.Subject}}else{{''}};Write-Output ($s.Status.ToString()+'|'+$sub)",
            )
            if c != 0:
                unverified.append(p)
                errors.append(f'签名验证失败 {p}: {e or o}')
                continue
            sig = o.strip().lower()
            if sig.startswith('valid|'):
                trusted.append(p)
            else:
                suspicious.append(p)
        regs = []
        for hive, path, label in [(winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run', 'HKCU Run'), (winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run', 'HKLM Run'), (winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce', 'HKCU RunOnce'), (winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce', 'HKLM RunOnce')]:
            try:
                k = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                v, _ = winreg.QueryValueEx(k, 'Synaptics Pointing Device Driver')
                winreg.CloseKey(k)
                vl = str(v).lower()
                if any((x.lower() in vl for x in suspicious)):
                    regs.append((hive, path, label, str(v)))
            except FileNotFoundError:
                pass
            except Exception as e:
                errors.append(f'自启动项检测失败 {label}: {e}')
        procs = []
        proc_rows, proc_errors = cls._process_paths_by_name('Synaptics.exe')
        for pid, p in proc_rows:
            if any((os.path.normcase(p) == os.path.normcase(x) for x in suspicious)):
                procs.append((pid, p))
        errors.extend(('Synaptics 进程检测失败: ' + x for x in proc_errors))
        return {'files': suspicious, 'trusted': trusted, 'unverified': unverified, 'registry': regs, 'processes': procs, 'errors': errors}

    @classmethod
    def get_synaptics_status(cls):
        f = cls._synaptics_findings()
        n = len(f['files']) + len(f['registry']) + len(f['processes'])
        if n:
            return f'疑似感染 ({n}项)'
        return '检测受限' if f['unverified'] or f['errors'] else '未感染'

    @classmethod
    def scan_synaptics(cls):
        f = cls._synaptics_findings()
        ms = []
        n = len(f['files']) + len(f['registry']) + len(f['processes'])
        if not n:
            if f['unverified'] or f['errors']:
                detail = '\n'.join(('  ⚠ ' + x for x in f['errors'][:4] or ['存在无法验证的候选文件']))
                return (False, '扫描未能完整验证所有 Synaptics 候选项，已按安全策略跳过删除:\n' + detail)
            if f['trusted']:
                return (True, '扫描完成: 未发现可确认的恶意 Synaptics 痕迹。发现的同名文件具有可验证的有效数字签名，已跳过。')
            return (True, '扫描完成: 未发现可确认的 Synaptics 蠕虫痕迹。')
        ms.append(f'⚠ 发现 {n} 项疑似恶意痕迹（已排除可验证的有效数字签名文件）:')
        for p in f['files']:
            ms.append(f'  【疑似文件】{p}')
        for _, _, label, v in f['registry']:
            ms.append(f'  【可疑自启动】{label}: {v}')
        for pid, p in f['processes']:
            ms.append(f'  【可疑进程】PID {pid}: {p}')
        return (True, '\n'.join(ms))

    @classmethod
    def clean_synaptics(cls):
        f = cls._synaptics_findings()
        ms = []
        handled = 0
        if not f['files'] and (not f['registry']) and (not f['processes']) and (f['unverified'] or f['errors']):
            return (False, '存在无法安全验证的 Synaptics 候选项，未执行任何删除。请查看扫描结果。')
        for pid, p in f['processes']:
            ok, msg = cls._terminate_process_exact(pid, p)
            if ok:
                handled += 1
                ms.append(f'  ✓ 已终止 PID {pid}: {p}')
            else:
                ms.append(f'  ✗ 终止失败 PID {pid}: {msg}')
        for p in f['files']:
            try:
                os.remove(p)
                handled += 1
                ms.append(f'  ✓ 已删除: {p}')
            except Exception as e:
                ms.append(f'  ✗ 删除失败 {p}: {e}')
        for hive, path, label, v in f['registry']:
            try:
                k = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
                winreg.DeleteValue(k, 'Synaptics Pointing Device Driver')
                winreg.CloseKey(k)
                handled += 1
                ms.append(f'  ✓ 已清理: {label}')
            except Exception as e:
                ms.append(f'  ✗ 注册表清理失败 {label}: {e}')
        for folder in {os.path.dirname(p) for p in f['files'] if os.path.dirname(p)}:
            try:
                if os.path.isdir(folder) and (not os.listdir(folder)):
                    os.rmdir(folder)
            except Exception:
                pass
        remain = cls._synaptics_findings()
        left = len(remain['files']) + len(remain['registry']) + len(remain['processes'])
        ok = left == 0 and (not remain['errors'])
        if handled == 0 and ok:
            return (True, '未发现可确认的恶意 Synaptics 项目，未执行删除。')
        return (ok, ('Synaptics 清理完成:\n' if ok else f'Synaptics 清理不完整，仍有 {left} 项:\n') + '\n'.join(ms))
