"""高级设置领域门面。

UI 只依赖这个类；具体实现按安全、遥测、隐私、AI 等子域拆分。
"""

from wintuner.service_management.base import ServiceController

from .ai import AISettingsMixin
from .privacy import PrivacySettingsMixin
from .security import SecuritySettingsMixin
from .synaptics import SynapticsCleanupMixin
from .telemetry import TelemetrySettingsMixin
from .windows_policy import WindowsPolicySettingsMixin


class AdvancedSettingsManager(
    SecuritySettingsMixin,
    SynapticsCleanupMixin,
    TelemetrySettingsMixin,
    PrivacySettingsMixin,
    AISettingsMixin,
    WindowsPolicySettingsMixin,
    ServiceController,
):
    """高级设置统一公开接口。"""

    pass
