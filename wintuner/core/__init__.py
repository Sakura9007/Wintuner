"""WinTuner 公共基础设施层。"""

from .admin import is_admin, require_admin
from .paths import LOG_PATH, write_error_log
__all__ = ['is_admin', 'require_admin', 'LOG_PATH', 'write_error_log']
