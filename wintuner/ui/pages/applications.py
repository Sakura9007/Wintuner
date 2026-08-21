"""应用管理页面。"""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from wintuner.application_management import ApplicationManager
from wintuner.core.constants import BLOAT_APPS, THIRD_BLOAT_APPS
from wintuner.core.runtime import _pending_mutations, _system_generation
from wintuner.core.workers import MixIn
from wintuner.ui.styles import BP, BS, BCR
from wintuner.ui.widgets import (
    ACard,
    DashboardColumns,
    _gl,
    _info_card,
    _page_header,
    _scroll,
    _sep,
    _tip,
    _toolbar,
)


UNINSTALL_INFO = (
    '卸载先处理所有用户注册，再清除系统镜像预配记录；'
    'Windows 标记为不可移除的系统包会明确列出而不是假报成功',
    '大部分应用可通过 Microsoft Store 重新安装，操作相对安全',
    '卸载后释放的内存和磁盘空间立即生效，无需重启',
)

MICROSOFT_APP_REFERENCE = (
    'Clipchamp · Cortana(549981C3F5F10) · BingFinance/News/Sports/Weather',
    'MicrosoftOfficeHub · Solitaire · StickyNotes · 3DBuilder · 3DViewer',
    'MixedReality.Portal · Print3D · Journal · Todos · Alarms · Maps',
    'SoundRecorder · FeedbackHub · ZuneVideo · SkypeApp · MSTeams',
    'People · PowerAutomateDesktop · QuickAssist · MicrosoftFamily',
    'BingTranslator · Office.OneNote · MicrosoftTeams/MSTeams · News · Getstarted',
)

THIRD_PARTY_APP_REFERENCE = (
    'CandyCrush(Saga/Soda/BubbleWitch) · Spotify · Disney · Netflix',
    'Facebook · Instagram · TikTok · Twitter(X) · Amazon · PrimeVideo',
    'Duolingo · Flipboard · PicsArt · Plex · Shazam · Viber · Hulu',
    'WinZip · AdobePhotoshopExpress · LinkedIn',
)

KEEP_APP_REFERENCE = (
    'WindowsStore (卸载后无法重装应用) · WindowsTerminal (开发必备)',
    'WindowsCalculator · WindowsCamera · Photos · Paint · ScreenSketch',
    'GamingApp (部分PC游戏安装需要) · XboxIdentityProvider (游戏登录)',
)


class AppRemovalPage(QWidget, MixIn):
    """微软/OEM 预装应用清理页面。"""

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        MixIn._init_workers(self)
        self.logger = logger
        self.cards = {}
        self.setAutoFillBackground(False)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_page_header('应用管理', '清理微软与 OEM 预装应用，同时明确标识系统保护包与建议保留项。', 'APPS / CLEANUP'))
        root.addWidget(_toolbar([('刷新状态', BP, self.detect_all)]))
        ct = QWidget()
        ct.setAutoFillBackground(False)
        ct.setStyleSheet('background:transparent;')
        cl = DashboardColumns(ct)
        cl.addWidget(
            _info_card(
                'ℹ',
                '关于应用卸载',
                UNINSTALL_INFO,
                QColor(239, 246, 255),
                QColor(191, 219, 254),
                '#2563EB',
            )
        )
        cl.addSpacing(3)
        cl.addWidget(_gl('MICROSOFT BLOATWARE'))
        cl.addWidget(_sep())
        bl = ACard(
            '一键卸载微软垃圾应用',
            'Cortana · BingNews · Solitaire · StickyNotes · 3DBuilder · MixedReality · Teams等31个',
            'ms_bloat',
            '一键卸载',
            '',
            BCR,
            BS,
            False,
            logger=logger,
        )
        bl.bind(ApplicationManager.remove_bloatware, ApplicationManager.get_bloat_status)
        self.cards['ms_bloat'] = bl
        cl.addWidget(bl)
        cl.addWidget(_tip('游戏玩家强烈建议卸载: 这些预装应用每个都在后台占用内存，全部卸载可释放200-500MB内存'))
        cl.addSpacing(3)
        cl.addWidget(_gl('THIRD-PARTY BLOATWARE'))
        cl.addWidget(_sep())
        tl = ACard(
            '一键卸载第三方垃圾应用',
            'CandyCrush · Spotify · TikTok · Instagram · Facebook · Netflix · Amazon等22个',
            '3rd_bloat',
            '一键卸载',
            '',
            BCR,
            BS,
            False,
            logger=logger,
        )
        tl.bind(ApplicationManager.remove_third_party_bloat, ApplicationManager.get_3rd_bloat_status)
        self.cards['3rd_bloat'] = tl
        cl.addWidget(tl)
        cl.addWidget(_tip('游戏玩家强烈建议卸载: OEM预装的游戏和社交应用完全是浪费磁盘空间'))
        cl.addSpacing(3)
        cl.addWidget(_gl('应用卸载清单 (参考)'))
        cl.addWidget(_sep())
        cl.addWidget(
            _info_card(
                '📋',
                '微软应用卸载清单 (31项)',
                MICROSOFT_APP_REFERENCE,
                QColor(248, 250, 252),
                QColor(226, 232, 240),
                '#475569',
            )
        )
        cl.addSpacing(3)
        cl.addWidget(
            _info_card(
                '📋',
                '第三方应用卸载清单 (22项)',
                THIRD_PARTY_APP_REFERENCE,
                QColor(248, 250, 252),
                QColor(226, 232, 240),
                '#475569',
            )
        )
        cl.addSpacing(3)
        cl.addWidget(
            _info_card(
                '⚠',
                '以下应用建议保留',
                KEEP_APP_REFERENCE,
                QColor(255, 251, 235),
                QColor(253, 230, 138),
                '#D97706',
            )
        )
        cl.addStretch()
        root.addWidget(_scroll(ct))

    def detect_all(self):
        if not self._begin_detect_batch():
            return
        gen = _system_generation()
        targets = tuple(dict.fromkeys(BLOAT_APPS + THIRD_BLOAT_APPS))
        self.logger('⏳ 正在检测应用状态 (2 项)...')

        def _collect():
            if gen != _system_generation() or _pending_mutations() != 0:
                return None
            inv, err = ApplicationManager._appx_inventory(targets)
            return (inv, err)

        def _done(ok, result):
            applied = ok and result is not None and (gen == _system_generation()) and (_pending_mutations() == 0)
            if applied:
                inv, err = result
                if inv is None:
                    s1 = s2 = '检测失败'
                else:
                    present = set(inv['present'])
                    protected = set(inv['protected'])
                    m = [x for x in BLOAT_APPS if x in present]
                    t = [x for x in THIRD_BLOAT_APPS if x in present]
                    if not m:
                        s1 = '已清理'
                    elif set(m).issubset(protected):
                        s1 = f'系统保留 {len(m)} 项'
                    else:
                        s1 = f'发现 {len(m)} 项'
                    s2 = f'发现 {len(t)} 项' if t else '已清理'
                self.cards['ms_bloat'].badge.set_status(s1)
                self.cards['3rd_bloat'].badge.set_status(s2)
                fail = sum((x == '检测失败' for x in (s1, s2)))
                self.logger(f'✓ 应用状态检测完成: {2 - fail} 正常 / 0 部分 / 0 受限 / {fail} 失败')
            else:
                self.logger('  ℹ 应用检测结果因期间发生系统修改或刷新请求而作废')
            self._end_detect_batch(self.detect_all)
        self._run_object_async(_collect, _done)
