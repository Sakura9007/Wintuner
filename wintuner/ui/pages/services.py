"""服务管理页面。"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from wintuner.core.constants import SERVICES_LIST
from wintuner.core.runtime import _pending_mutations, _system_generation
from wintuner.core.workers import MixIn
from wintuner.service_management import ServiceManager
from wintuner.ui.styles import BP, BD, BS
from wintuner.ui.widgets import DashboardColumns, SvcCard, _ask, _gl, _page_header, _scroll, _sep, _toolbar


SERVICE_GROUPS = (
    ('DIAGNOSTIC SERVICES', slice(0, 4)),
    ('WINDOWS HEALTH / OPTIMIZED EXPERIENCES', slice(4, 5)),
    ('SYSTEM MAINTENANCE', slice(5, 6)),
    ('PRINT SERVICES', slice(6, 8)),
    ('NFC / PAYMENT', slice(8, 9)),
    ('XBOX SERVICES', slice(9, 13)),
    ('RETAIL / EDGE', slice(13, None)),
)


class ServicesPage(QWidget, MixIn):
    """Windows 服务管理页面。"""

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        MixIn._init_workers(self)
        self.logger = logger
        self.cards = []
        self.setAutoFillBackground(False)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_page_header('服务管理', '集中管理 Windows 后台服务，所有可逆操作继续使用原始状态快照恢复。', 'SERVICES / CONTROL'))
        root.addWidget(
            _toolbar([('全部禁用', BD, self._dall), ('全部恢复', BS, self._eall), ('刷新状态', BP, self.detect_all)]),
        )
        ct = QWidget()
        cl = DashboardColumns(ct)
        for group_title, item_slice in SERVICE_GROUPS:
            cl.addWidget(_gl(group_title))
            cl.addWidget(_sep())
            for service_name, _, display_name in SERVICES_LIST[item_slice]:
                card = SvcCard(service_name, display_name, logger)
                self.cards.append(card)
                cl.addWidget(card)
            cl.addSpacing(4)
        cl.addStretch()
        root.addWidget(_scroll(ct))

    def detect_all(self):
        if not self._begin_detect_batch():
            return
        cards = tuple(self.cards)
        gen = _system_generation()
        self.logger(f'⏳ 正在检测服务状态 ({len(cards)} 项)...')

        def _collect():
            rows = []
            for c in cards:
                if gen != _system_generation() or _pending_mutations() != 0:
                    return None
                rows.append((c.svc, ServiceManager.get_service_status(c.svc)))
            return rows

        def _done(ok, rows):
            applied = ok and rows is not None and (gen == _system_generation()) and (_pending_mutations() == 0)
            if applied:
                by_svc = dict(rows)
                fail = []
                partial = []
                restricted = []
                for c in cards:
                    status = by_svc.get(c.svc, '检测失败')
                    c.badge.set_status(status, c.status_overrides)
                    if '检测失败' in status:
                        fail.append(c.lbl.text())
                    elif '检测受限' in status or '系统保护' in status:
                        restricted.append(c.lbl.text())
                    elif '部分' in status:
                        partial.append(c.lbl.text())
                normal = len(cards) - len(fail) - len(partial) - len(restricted)
                self.logger(
                    f'✓ 服务状态检测完成: {normal} 正常 / {len(partial)} 部分 / {len(restricted)} 受限 / {len(fail)} 失败',
                )
                if partial:
                    self.logger('  ⚠ 部分状态: ' + '、'.join(partial[:6]))
                if restricted:
                    self.logger('  ⚠ 检测受限: ' + '、'.join(restricted[:6]))
                if fail:
                    self.logger('  ✗ 检测失败: ' + '、'.join(fail[:6]))
            else:
                self.logger('  ℹ 服务检测结果因期间发生系统修改或刷新请求而作废')
            self._end_detect_batch(self.detect_all)
        self._run_object_async(_collect, _done)

    def _bulk(self, enable):
        eligible = [c for c in self.cards if (c.be.isEnabled() if enable else c.bd.isEnabled())]
        if not eligible:
            self.detect_all()
            return
        state = {'left': len(eligible)}

        def _one():
            state['left'] -= 1
            if state['left'] == 0:
                QTimer.singleShot(0, self.detect_all)
        for c in eligible:
            c._ena(_one, False) if enable else c._dis(_one, False)

    def _dall(self):
        if _ask(self, '确认', f'禁用全部 {len(self.cards)} 项服务?'):
            self.logger('▶ 批量禁用...')
            self._bulk(False)

    def _eall(self):
        if _ask(self, '确认', '恢复所有服务?'):
            self.logger('▶ 批量恢复...')
            self._bulk(True)
