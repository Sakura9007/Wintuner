"""AppX/预装应用检测与卸载管理。"""

from __future__ import annotations

import json
from collections.abc import Iterable

from wintuner.core.commands import CommandRunner
from wintuner.core.constants import BLOAT_APPS, THIRD_BLOAT_APPS


class ApplicationManager(CommandRunner):
    """应用管理公开入口，负责 AppX 库存检测和批量清理。"""

    # ------------------------------------------------------------------
    # AppX 库存检测
    # ------------------------------------------------------------------
    @staticmethod
    def _appx_inventory(apps: Iterable[str]) -> tuple[dict[str, list[str]] | None, str]:
        """返回目标 AppX 包的存在状态和系统保护状态。"""

        joined = "','".join(name.replace("'", "''") for name in apps)
        script = (
            f"$targets=@('{joined}');"
            "$installed=@(Get-AppxPackage -AllUsers -PackageTypeFilter Main,Bundle -ErrorAction Stop);"
            "$prov=@(Get-AppxProvisionedPackage -Online -ErrorAction Stop);"
            "$present=@();"
            "$protected=@();"
            "foreach($n in $targets){"
            "$ip=@($installed|Where-Object{$_.Name -eq $n});"
            "$pp=@($prov|Where-Object{$_.DisplayName -eq $n});"
            "if($ip.Count -gt 0 -or $pp.Count -gt 0){$present+=$n};"
            "if(@($ip|Where-Object{($_.PSObject.Properties.Name -contains 'NonRemovable') "
            "-and $_.NonRemovable}).Count -gt 0){$protected+=$n}"
            "};"
            "[pscustomobject]@{"
            "present=@($present|Sort-Object -Unique);"
            "protected=@($protected|Sort-Object -Unique)"
            "}|ConvertTo-Json -Compress -Depth 4"
        )

        code, stdout, stderr = ApplicationManager.run_ps(script, 120)
        if code != 0 or not stdout.strip():
            return None, stderr or stdout or 'Appx inventory returned no data'

        try:
            data = json.loads(stdout.strip())
            for key in ('present', 'protected'):
                value = data.get(key, [])
                if value is None:
                    value = []
                elif isinstance(value, str):
                    value = [value]
                data[key] = list(value)
            return data, ''
        except Exception as exc:
            return None, f'Appx inventory JSON parse failed: {exc}: {stdout[:300]}'

    # ------------------------------------------------------------------
    # AppX 批量卸载
    # ------------------------------------------------------------------
    @staticmethod
    def _remove_appx_targets(apps: Iterable[str], label: str) -> tuple[bool, str]:
        """删除所有用户注册与系统镜像中的对应预配包。"""

        apps = tuple(apps)
        joined = "','".join(name.replace("'", "''") for name in apps)
        script = (
            f"$targets=@('{joined}');"
            "$errs=New-Object System.Collections.Generic.List[string];"
            "$skipped=New-Object System.Collections.Generic.List[string];"
            "foreach($n in $targets){"
            "$pkgs=@(Get-AppxPackage -AllUsers -Name $n -PackageTypeFilter Main,Bundle "
            "-ErrorAction SilentlyContinue);"
            "foreach($p in $pkgs){"
            "if(($p.PSObject.Properties.Name -contains 'NonRemovable') -and $p.NonRemovable){"
            "[void]$skipped.Add($n+': Windows 标记为 NonRemovable');"
            "continue"
            "};"
            "$done=$false;"
            "try{"
            "Remove-AppxPackage -Package $p.PackageFullName -AllUsers -Confirm:$false "
            "-ErrorAction Stop;"
            "$done=$true"
            "}catch{"
            "$uis=@($p.PackageUserInformation|Where-Object{$_.InstallState -ne 'NotInstalled'});"
            "if($uis.Count -eq 0){"
            "[void]$errs.Add($n+': '+$_.Exception.Message)"
            "}else{"
            "$all=$true;"
            "foreach($ui in $uis){"
            "$sid=[string]$ui.UserSecurityId;"
            "try{"
            "Remove-AppxPackage -Package $p.PackageFullName -User $sid -Confirm:$false "
            "-ErrorAction Stop"
            "}catch{"
            "$all=$false;"
            "[void]$errs.Add($n+' ['+$sid+']: '+$_.Exception.Message)"
            "}"
            "};"
            "$done=$all"
            "}"
            "}"
            "};"
            "$prov=@(Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue|"
            "Where-Object{$_.DisplayName -eq $n});"
            "foreach($p in $prov){"
            "try{"
            "Remove-AppxProvisionedPackage -Online -PackageName $p.PackageName -AllUsers "
            "-ErrorAction Stop|Out-Null"
            "}catch{"
            "[void]$errs.Add($n+' [Provisioned]: '+$_.Exception.Message)"
            "}"
            "}"
            "};"
            "[pscustomobject]@{errors=$errs.ToArray();skipped=$skipped.ToArray()}"
            "|ConvertTo-Json -Compress -Depth 4"
        )

        code, stdout, stderr = ApplicationManager.run_ps(script, 300)
        report: dict[str, list[str]] = {'errors': [], 'skipped': []}

        if code == 0 and stdout.strip():
            try:
                report = json.loads(stdout.strip())
                for key in ('errors', 'skipped'):
                    value = report.get(key, [])
                    if value is None:
                        value = []
                    elif isinstance(value, str):
                        value = [value]
                    report[key] = list(value)
            except Exception:
                report = {
                    'errors': ['卸载结果解析失败: ' + stdout[:300]],
                    'skipped': [],
                }
        elif code != 0:
            report = {
                'errors': [stderr or stdout or 'Appx 卸载命令失败'],
                'skipped': [],
            }

        inventory, inventory_error = ApplicationManager._appx_inventory(apps)
        if inventory is None:
            return False, f'{label}执行后状态检测失败: {inventory_error}'

        remaining = list(inventory['present'])
        protected = set(inventory['protected'])
        if not remaining:
            return True, f'{label}完成: 所有可检测目标均已卸载，并已移除对应预配记录'

        protected_remaining = [name for name in remaining if name in protected]
        normal_remaining = [name for name in remaining if name not in protected]
        lines = [f'{label}完成后仍有 {len(remaining)} 项目标存在。']

        if protected_remaining:
            lines.append(
                '  ℹ Windows 系统保护/不可移除: '
                + ', '.join(protected_remaining[:8])
            )
        if normal_remaining:
            lines.append(
                '  ⚠ 仍可检测但未成功移除: '
                + ', '.join(normal_remaining[:8])
            )
        for item in report.get('skipped', [])[:4]:
            lines.append('  ℹ ' + str(item))
        for item in report.get('errors', [])[:6]:
            lines.append('  ✗ ' + str(item))

        if protected_remaining and not normal_remaining:
            detail = '\n'.join(lines[1:])
            return (
                True,
                f'{label}已完成所有可卸载项目；Windows 保留 '
                f'{len(protected_remaining)} 项系统保护包，未强制破坏系统组件:\n{detail}',
            )

        return False, '\n'.join(lines)

    # ------------------------------------------------------------------
    # 面向 UI 的公开操作
    # ------------------------------------------------------------------
    @staticmethod
    def remove_bloatware() -> tuple[bool, str]:
        return ApplicationManager._remove_appx_targets(BLOAT_APPS, '批量卸载')

    @staticmethod
    def remove_third_party_bloat() -> tuple[bool, str]:
        return ApplicationManager._remove_appx_targets(
            THIRD_BLOAT_APPS,
            '第三方应用清理',
        )

    @staticmethod
    def get_bloat_status() -> str:
        inventory, _ = ApplicationManager._appx_inventory(BLOAT_APPS)
        if inventory is None:
            return '检测失败'

        count = len(inventory['present'])
        if not count:
            return '已清理'

        present = set(inventory['present'])
        protected = set(inventory['protected'])
        if present.issubset(protected):
            return f'系统保留 {count} 项'
        return f'发现 {count} 项'

    @staticmethod
    def get_3rd_bloat_status() -> str:
        inventory, _ = ApplicationManager._appx_inventory(THIRD_BLOAT_APPS)
        if inventory is None:
            return '检测失败'
        count = len(inventory['present'])
        return f'发现 {count} 项' if count else '已清理'

    @staticmethod
    def _appx_count(apps: Iterable[str]) -> int | None:
        inventory, _ = ApplicationManager._appx_inventory(apps)
        return None if inventory is None else len(inventory['present'])
