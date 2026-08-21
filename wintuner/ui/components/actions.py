"""服务卡片、通用动作卡片、确认框和批量状态检测。"""

from __future__ import annotations

from functools import partial

from PyQt6.QtCore import Qt

from PyQt6.QtGui import QColor

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from wintuner.core.constants import EDGE_STOP_GREEN_SERVICES

from wintuner.core.runtime import _DETECT_CANCELLED, _DETECT_CTX, _next_detect_batch_id, _pending_mutations, _system_generation

from wintuner.core.workers import MixIn

from wintuner.service_management import ServiceManager

from wintuner.ui.styles import BD, BG, BS

from .primitives import Card, Badge, _btn, _lbl
from .layout import _gl, _sep


class SvcCard(Card, MixIn):
    """单个 Windows Service 的状态与操作卡片。"""

    def __init__(self, svc, cn, logger, parent=None):
        Card.__init__(self, parent)
        MixIn._init_workers(self)
        self.svc = svc
        self.logger = logger
        self._detect_seq = 0
        self.setMinimumHeight(62)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 9, 12, 9)
        lay.setSpacing(8)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl = _lbl(cn, '#27272A', 12, True)
        self.sub = _lbl(f'服务名  ·  {svc}', '#A1A1AA', 10)
        info.addWidget(self.lbl)
        info.addWidget(self.sub)
        lay.addLayout(info, 1)
        self.badge = Badge()
        lay.addWidget(self.badge)
        self.status_overrides = {'已停止': 'on'} if svc in EDGE_STOP_GREEN_SERVICES else {}
        self.bd = _btn('禁用', BD, self._dis)
        self.be = _btn('恢复', BS, self._ena)
        self.bd.setFixedWidth(60)
        self.be.setFixedWidth(60)
        lay.addWidget(self.bd)
        lay.addWidget(self.be)

    def detect(self, done_cb=None):
        self._detect_seq += 1
        seq = self._detect_seq
        svc = self.svc
        gen = _system_generation()

        def _g():
            if seq != self._detect_seq or gen != _system_generation() or _pending_mutations() != 0:
                return (True, _DETECT_CANCELLED)
            return (True, ServiceManager.get_service_status(svc))

        def _done(ok, t):
            cancelled = ok and str(t) == _DETECT_CANCELLED
            status = '检测已取消' if cancelled else str(t) if ok else '检测失败'
            applied = not cancelled and seq == self._detect_seq and (gen == _system_generation()) and (_pending_mutations() == 0)
            if applied:
                self.badge.set_status(status, self.status_overrides)
            if done_cb:
                try:
                    done_cb(self.lbl.text(), status, applied)
                except Exception:
                    pass
        self._run_async(_g, _done)

    def _dis(self, done_cb=None, post_detect=True):
        if not self.bd.isEnabled():
            return False
        self._detect_seq += 1
        self.logger(f'▶ 禁用: {self.lbl.text()}')
        self.bd.setEnabled(False)
        self.be.setEnabled(False)
        self._run_action(
            f'service::{self.svc}',
            'apply',
            ServiceManager.disable_service,
            partial(self._done, done_cb=done_cb, post_detect=post_detect),
            self.svc,
        )
        return True

    def _ena(self, done_cb=None, post_detect=True):
        if not self.be.isEnabled():
            return False
        self._detect_seq += 1
        self.logger(f'▶ 恢复: {self.lbl.text()}')
        self.bd.setEnabled(False)
        self.be.setEnabled(False)
        self._run_action(
            f'service::{self.svc}',
            'restore',
            ServiceManager.enable_service,
            partial(self._done, done_cb=done_cb, post_detect=post_detect),
            self.svc,
        )
        return True

    def _done(self, ok, msg, done_cb=None, post_detect=True):
        self.bd.setEnabled(True)
        self.be.setEnabled(True)
        self.logger(f"  {('✓' if ok else '✗')} {msg}")
        if post_detect:
            self.detect()
        if done_cb:
            try:
                done_cb()
            except Exception:
                pass


class ACard(Card, MixIn):
    """通用动作卡片，绑定应用、恢复、检测三个操作。"""

    def __init__(self, title, desc, cid, ot='关闭', ont='恢复', os_=BD, ons=BS, ov=True, eb=None, logger=None, parent=None):
        Card.__init__(self, parent)
        MixIn._init_workers(self)
        self.cid = cid
        self.logger = logger
        self._detect_seq = 0
        self.title = title
        self._gfn = None
        self._ofn = None
        self._onfn = None
        self._cfn = None
        self._restore_snapshot = True
        self.status_overrides = {}
        self.setMinimumHeight(68)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 12, 10)
        lay.setSpacing(8)
        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(_lbl(title, '#27272A', 12, True))
        dl = _lbl(desc, '#71717A', 10)
        dl.setWordWrap(True)
        info.addWidget(dl)
        lay.addLayout(info, 1)
        self.badge = Badge()
        lay.addWidget(self.badge)
        self.bo = _btn(ot, os_)
        self.bo.setMinimumWidth(64)
        lay.addWidget(self.bo)
        if ov:
            self.bn = _btn(ont, ons)
            self.bn.setMinimumWidth(64)
            lay.addWidget(self.bn)
        else:
            self.bn = None
        if eb:
            ex = _btn(eb[0], BG, eb[1])
            ex.setMinimumWidth(76)
            lay.addWidget(ex)

    def bind(self, ofn, gfn, onfn=None, cfn=None, restore_snapshot=True):
        self._ofn = ofn
        self._onfn = onfn
        self._gfn = gfn
        self._cfn = cfn
        self._restore_snapshot = restore_snapshot
        self.bo.clicked.connect(self._do_off)
        if self.bn and onfn:
            self.bn.clicked.connect(self._do_on)

    def detect(self, done_cb=None, batch_id=None):
        if self._gfn:
            self._detect_seq += 1
            seq = self._detect_seq
            gfn = self._gfn
            gen = _system_generation()

            def _g():
                if seq != self._detect_seq or gen != _system_generation() or _pending_mutations() != 0:
                    return (True, _DETECT_CANCELLED)
                prev = getattr(_DETECT_CTX, 'batch_id', None)
                _DETECT_CTX.batch_id = batch_id
                try:
                    return (True, gfn())
                finally:
                    if prev is None:
                        try:
                            delattr(_DETECT_CTX, 'batch_id')
                        except Exception:
                            pass
                    else:
                        _DETECT_CTX.batch_id = prev

            def _done(ok, t):
                cancelled = ok and str(t) == _DETECT_CANCELLED
                status = '检测已取消' if cancelled else str(t) if ok else '检测失败'
                applied = not cancelled and seq == self._detect_seq and (gen == _system_generation()) and (_pending_mutations() == 0)
                if applied:
                    self.badge.set_status(status, self.status_overrides)
                if done_cb:
                    try:
                        done_cb(self.title, status, applied)
                    except Exception:
                        pass
            self._run_async(_g, _done)

    def _done(self, ok, msg):
        self.bo.setEnabled(True)
        if self.bn:
            self.bn.setEnabled(True)
        if self.logger:
            self.logger(f"  {('✓' if ok else '✗')} {msg}")
        self.detect()

    def _do_off(self):
        if not self._ofn or not self.bo.isEnabled():
            return
        if self._cfn and (not self._cfn()):
            return
        self._detect_seq += 1
        if self.logger:
            self.logger(f'▶ 执行: {self.cid}')
        self.bo.setEnabled(False)
        if self.bn:
            self.bn.setEnabled(False)
        self._run_action(
            self.cid,
            'apply' if self.bn and self._restore_snapshot else 'apply_once',
            self._ofn,
            self._done,
        )

    def _do_on(self):
        if not self._onfn or not self.bo.isEnabled():
            return
        self._detect_seq += 1
        if self.logger:
            self.logger(f'▶ 恢复: {self.cid}')
        self.bo.setEnabled(False)
        if self.bn:
            self.bn.setEnabled(False)
        self._run_action(
            self.cid,
            'restore' if self._restore_snapshot else 'apply_once',
            self._onfn,
            self._done,
        )


def _info_card(icon, title, lines, bg_c, bd_c, icon_c):
    card = Card()
    card.set_special(bg_c, bd_c)
    card.setMinimumHeight(58)
    lay = QHBoxLayout(card)
    lay.setContentsMargins(14, 11, 14, 11)
    lay.setSpacing(10)
    ic = QLabel(icon)
    ic.setStyleSheet(f'font-size:16px;color:{icon_c};background:transparent;')
    ic.setFixedWidth(24)
    ic.setAlignment(Qt.AlignmentFlag.AlignTop)
    lay.addWidget(ic)
    info = QVBoxLayout()
    info.setSpacing(3)
    tl = _lbl(title, icon_c, 12, True)
    info.addWidget(tl)
    for line in lines:
        ll = _lbl(line, '#5F6368', 10)
        ll.setWordWrap(True)
        info.addWidget(ll)
    lay.addLayout(info, 1)
    return card

MESSAGE_QSS = (
    'QMessageBox{background:#FFFFFF;}'
    'QMessageBox QLabel{'
    "color:#27272A;font-size:12px;font-family:'Microsoft YaHei UI';"
    '}'
    'QMessageBox QPushButton{'
    'background:#FFFFFF;color:#3F3F46;border:1px solid #E4E4E7;'
    'border-radius:8px;padding:6px 15px;min-width:64px;'
    '}'
    'QMessageBox QPushButton:hover{'
    'background:#F4F4F5;border-color:#D4D4D8;'
    '}'
)


def _ask(parent, title, text):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setStyleSheet(MESSAGE_QSS)
    return box.exec() == QMessageBox.StandardButton.Yes


def _tip(tip_text):
    card = Card()
    card.set_special(QColor(242, 249, 247), QColor(207, 235, 226))
    card.setMinimumHeight(34)
    lay = QHBoxLayout(card)
    lay.setContentsMargins(11, 8, 11, 8)
    tl = _lbl(f'↳  {tip_text}', '#217A64', 10)
    tl.setWordWrap(True)
    lay.addWidget(tl, 1)
    return card


def _make_toggle(
    cl,
    grp,
    cid,
    title,
    desc,
    tip,
    logger,
    off_fn,
    on_fn,
    get_fn,
    cards,
    pre_widgets=None,
    eb=None,
    ot='关闭',
    ont='恢复',
    restore_snapshot=True,
):
    cl.addWidget(_gl(grp))
    cl.addWidget(_sep())
    if pre_widgets:
        for pw in pre_widgets:
            cl.addWidget(pw)
    card = ACard(title, desc, cid, ot, ont, BD, BS, True, eb, logger)
    card.bind(off_fn, get_fn, on_fn, restore_snapshot=restore_snapshot)
    cards[cid] = card
    cl.addWidget(card)
    if tip:
        cl.addWidget(_tip(tip))
    cl.addSpacing(3)


def _warn_card(icon_text, msg_text, bg_c, bd_c, icon_c, text_c):
    card = Card()
    card.setMinimumHeight(44)
    card.set_special(bg_c, bd_c)
    lay = QHBoxLayout(card)
    lay.setContentsMargins(14, 10, 14, 10)
    ic = QLabel(icon_text)
    ic.setStyleSheet(f'color:{icon_c};font-size:15px;background:transparent;')
    ic.setAlignment(Qt.AlignmentFlag.AlignTop)
    tl = _lbl(msg_text, text_c, 12)
    tl.setWordWrap(True)
    lay.addWidget(ic)
    lay.addSpacing(6)
    lay.addWidget(tl, 1)
    return card


def _detect_cards_batch(cards, logger, label, owner=None):
    items = list(cards)
    total = len(items)
    if not total:
        logger(f'✓ {label}状态检测完成: 无可检测项目')
        return
    if owner is not None and (not owner._begin_detect_batch()):
        return
    logger(f'⏳ 正在检测{label}状态 ({total} 项)...')
    batch_id = _next_detect_batch_id()
    state = {'left': total, 'fail': [], 'partial': [], 'restricted': [], 'stale': 0}

    def _finish():
        valid = total - state['stale']
        normal = max(0, valid - len(state['fail']) - len(state['restricted']) - len(state['partial']))
        logger(
            f"✓ {label}状态检测完成: {normal} 正常 / {len(state['partial'])} 部分 / {len(state['restricted'])} 受限 / {len(state['fail'])} 失败",
        )
        if state['partial']:
            logger('  ⚠ 部分状态: ' + '、'.join(state['partial'][:6]))
        if state['restricted']:
            logger('  ⚠ 检测受限: ' + '、'.join(state['restricted'][:6]))
        if state['fail']:
            logger('  ✗ 检测失败: ' + '、'.join(state['fail'][:6]))
        if state['stale']:
            logger(f"  ℹ {state['stale']} 项检测结果因期间发生系统修改或刷新请求而作废")
        if owner is not None:
            owner._end_detect_batch(lambda: _detect_cards_batch(items, logger, label, owner))

    def _one(name, status, applied):
        if not applied:
            state['stale'] += 1
        elif '检测失败' in status:
            state['fail'].append(name)
        elif '检测受限' in status or '系统保护' in status:
            state['restricted'].append(name)
        elif '部分' in status:
            state['partial'].append(name)
        state['left'] -= 1
        if state['left'] == 0:
            _finish()
    for c in items:
        c.detect(_one, batch_id)
