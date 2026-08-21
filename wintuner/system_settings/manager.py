"""系统设置领域门面。

UI 只依赖这个类；具体实现按子域拆分到同包中的 mixin 模块。
"""

from wintuner.service_management.base import ServiceController

from .background_apps import BackgroundAppsSettingsMixin
from .devices import DeviceSettingsMixin
from .power import PowerSettingsMixin
from .shell import ShellSettingsMixin
from .virtualization_update import VirtualizationUpdateMixin
from .visual_input import VisualInputSettingsMixin


class SystemSettingsManager(
    VirtualizationUpdateMixin,
    DeviceSettingsMixin,
    PowerSettingsMixin,
    VisualInputSettingsMixin,
    BackgroundAppsSettingsMixin,
    ShellSettingsMixin,
    ServiceController,
):
    """系统设置统一公开接口。"""

    pass
