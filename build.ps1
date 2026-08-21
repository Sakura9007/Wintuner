$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$version = (python -c "from wintuner import __version__; print(__version__)").Trim()
if (-not $version) {
    throw "无法读取 WinTuner 版本号。"
}

$fileVersion = "$version.0"

$nuitkaArgs = @(
    "--standalone"
    "--windows-console-mode=disable"
    "--enable-plugin=pyqt6"
    "--windows-product-name=WinTuner Pro"
    "--windows-product-version=$fileVersion"
    "--windows-file-version=$fileVersion"
    "--windows-file-description=WinTuner Pro - Windows Performance Optimizer"
    "--windows-company-name=LiuMangStar Internet"
    "--windows-uac-admin"
    "--output-filename=WinTunerPro"
    "--output-dir=dist"
    "--assume-yes-for-downloads"
)

if (Test-Path (Join-Path $PSScriptRoot "1.ico")) {
    $nuitkaArgs += "--windows-icon-from-ico=1.ico"
} else {
    Write-Warning "未找到 1.ico，将使用默认程序图标继续构建。"
}

python -m nuitka @nuitkaArgs main.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "构建完成：dist\main.dist 或 Nuitka 实际输出目录" -ForegroundColor Green
