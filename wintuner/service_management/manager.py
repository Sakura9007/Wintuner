"""面向 UI 的 Windows 服务管理门面。"""

from .base import ServiceController


class ServiceManager(ServiceController):
    """服务管理层公开入口；UI 不直接接触底层命令和注册表。"""
    pass
