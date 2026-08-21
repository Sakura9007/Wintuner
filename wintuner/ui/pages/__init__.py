"""WinTuner 页面集合。"""

from .services import ServicesPage
from .system import SystemPage
from .advanced import AdvancedPage
from .applications import AppRemovalPage
from .software import InstallSoftwarePage
__all__ = ['ServicesPage', 'SystemPage', 'AdvancedPage', 'AppRemovalPage', 'InstallSoftwarePage']
