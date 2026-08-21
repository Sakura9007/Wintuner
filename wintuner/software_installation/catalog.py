"""装机软件官方入口目录。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)


class SoftwareEntry:
    """一个展示在“装机软件”页面中的官方软件入口。"""

    name: str
    description: str
    url: str


SOFTWARE_ITEMS: tuple[SoftwareEntry, ...] = (
    SoftwareEntry(
        name='Steam',
        description='Steam PC 游戏平台与商店',
        url='https://store.steampowered.com',
    ),
    SoftwareEntry(
        name='图吧工具箱',
        description='硬件检测、测试与装机常用工具集合',
        url='https://www.tbtool.cn/index.html',
    ),
    SoftwareEntry(
        name='MSI Afterburner',
        description='显卡监控、超频与 OSD 工具（微星小飞机）',
        url='https://www.msi.com/Landing/afterburner',
    ),
)
