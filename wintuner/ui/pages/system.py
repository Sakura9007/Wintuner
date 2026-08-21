"""系统设置页面。"""

from functools import partial
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from wintuner.core.constants import DEVICES_TO_MANAGE
from wintuner.core.workers import MixIn
from wintuner.system_settings import SystemSettingsManager
from wintuner.ui.styles import BG, BP, BD, BS
from wintuner.ui.widgets import (
    ACard,
    DashboardColumns,
    _detect_cards_batch,
    _gl,
    _make_toggle,
    _info_card,
    _page_header,
    _scroll,
    _sep,
    _tip,
    _toolbar,
    _warn_card,
    _ask,
)


class SystemPage(QWidget, MixIn):
    """常用系统与桌面体验设置页面。"""

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        MixIn._init_workers(self)
        self.logger = logger
        self.cards = {}
        self.setAutoFillBackground(False)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_page_header('系统设置', '电源、输入、设备、启动与桌面体验的统一性能工作区。', 'SYSTEM / PERFORMANCE'))
        root.addWidget(_toolbar([('刷新状态', BP, self.detect_all)]))
        ct = QWidget()
        ct.setAutoFillBackground(False)
        ct.setStyleSheet('background:transparent;')
        cl = DashboardColumns(ct)
        cl.addWidget(_gl('POWER PLAN'))
        cl.addWidget(_sep())
        # --- 电源与性能 -----------------------------------------------------
        pp_hp = ACard(
            '切换至高性能电源计划',
            '适合游戏和高负载场景',
            'pp_hp',
            '高性能',
            '',
            BP,
            BS,
            False,
            ('打开电源设置', SystemSettingsManager.open_power_settings),
            logger,
        )
        pp_hp.bind(SystemSettingsManager.set_high_performance, SystemSettingsManager.get_power_plan_status)
        self.cards['pp_hp'] = pp_hp
        cl.addWidget(pp_hp)
        pp_up = ACard(
            '切换至卓越性能电源计划',
            'Win10 1803+ 隐藏计划，最大化硬件性能',
            'pp_up',
            '卓越性能',
            '',
            BP,
            BS,
            False,
            ('打开电源设置', SystemSettingsManager.open_power_settings),
            logger,
        )
        pp_up.bind(
            SystemSettingsManager.set_ultimate_performance,
            SystemSettingsManager.get_power_plan_status,
        )
        self.cards['pp_up'] = pp_up
        cl.addWidget(pp_up)
        cl.addSpacing(3)
        _make_toggle(
            cl,
            'POWER THROTTLING',
            'power_throttling',
            '关闭 Power Throttling',
            '禁止 Windows 对符合条件的后台/节能工作负载应用系统级 Power Throttling',
            '台式游戏PC可选关闭: 更偏向性能与响应一致性；游戏本电池模式不建议关闭，会增加功耗、温度并降低续航',
            logger,
            SystemSettingsManager.disable_power_throttling,
            SystemSettingsManager.enable_power_throttling,
            SystemSettingsManager.get_power_throttling_status,
            self.cards,
            ot='关闭',
            ont='恢复默认',
            restore_snapshot=False,
        )
        cl.addWidget(_gl('HIDDEN POWER OPTIONS'))
        cl.addWidget(_sep())
        hp = ACard(
            '开放隐藏电源高级选项',
            '生效的异类策略 · 异类线程调度 · 短线程调度 · 性能提升模式',
            'hp',
            '一键开放',
            '',
            BP,
            BS,
            False,
            ('打开电源设置', SystemSettingsManager.open_power_settings),
            logger,
        )
        hp.bind(SystemSettingsManager.unlock_hidden_power, SystemSettingsManager.get_hidden_power_status)
        self.cards['hp'] = hp
        cl.addWidget(hp)
        cl.addSpacing(3)
        cl.addWidget(_gl('VISUAL EFFECTS'))
        cl.addWidget(_sep())
        vfx = ACard(
            '设置最佳性能 + 保留字体平滑与图标阴影',
            '高级系统设置 → 性能 → 调整为最佳性能，保留「平滑屏幕字体边缘」「桌面图标标签阴影」',
            'vfx',
            '一键设置',
            '',
            BP,
            BS,
            False,
            logger=logger,
        )
        vfx.bind(SystemSettingsManager.set_best_performance, SystemSettingsManager.get_visual_fx_status)
        self.cards['vfx'] = vfx
        cl.addWidget(vfx)
        cl.addSpacing(3)
        _make_toggle(
            cl,
            'MOUSE ACCELERATION',
            'mouse_accel',
            '关闭鼠标加速',
            '设置MouseSpeed/Threshold为0，实现严格线性1:1鼠标移动',
            '游戏玩家强烈建议关闭: FPS/TPS游戏中鼠标加速严重影响瞄准精度和肌肉记忆',
            logger,
            SystemSettingsManager.disable_mouse_accel,
            SystemSettingsManager.enable_mouse_accel,
            SystemSettingsManager.get_mouse_accel_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'STICKY KEYS',
            'sticky_keys',
            '关闭粘滞键快捷方式',
            '禁用连按5次Shift触发粘滞键、连按Num Lock触发切换键',
            '游戏玩家强烈建议关闭: 游戏中频繁按Shift误触粘滞键弹窗极其干扰',
            logger,
            SystemSettingsManager.disable_sticky_keys,
            SystemSettingsManager.enable_sticky_keys,
            SystemSettingsManager.get_sticky_keys_status,
            self.cards,
        )
        # --- 系统级开关与安全相关设置 ----------------------------------------------
        wc = _warn_card(
            '⚠',
            '强烈建议关闭 VBS 虚拟化安全 — Windows 最大的性能杀手，游戏帧率损失可达 5~25%',
            QColor(255, 251, 235),
            QColor(253, 230, 138),
            '#D97706',
            '#92400E',
        )
        system_level_cards = (
            {
                'id': 'VBS',
                'group': 'VIRTUALIZATION',
                'title': '关闭 VBS 虚拟化安全',
                'description': '关闭 Credential Guard / HVCI，需重启生效',
                'apply_text': '关闭',
                'restore_text': '',
                'apply_style': BD,
                'has_restore': False,
                'apply': SystemSettingsManager.disable_vbs,
                'restore': None,
                'detect': SystemSettingsManager.get_vbs_status,
                'pre_widgets': (wc,),
            },
            {
                'id': 'update',
                'group': 'WINDOWS UPDATE',
                'title': '暂停系统更新 (100 年)',
                'description': '写入100年暂停日期，并用自动更新策略提供长期兜底',
                'apply_text': '暂停更新',
                'restore_text': '',
                'apply_style': BP,
                'has_restore': False,
                'apply': SystemSettingsManager.pause_updates_100years,
                'restore': None,
                'detect': SystemSettingsManager.get_update_pause_status,
                'extra_button': ('打开设置', SystemSettingsManager.open_update_settings),
            },
            {
                'id': 'bitlocker',
                'group': 'BITLOCKER',
                'title': '关闭 BitLocker 磁盘加密',
                'description': '解密 Windows 系统驱动器，后台运行，期间请勿强制关机',
                'apply_text': '关闭',
                'restore_text': '',
                'apply_style': BD,
                'has_restore': False,
                'apply': SystemSettingsManager.disable_bitlocker,
                'restore': None,
                'detect': SystemSettingsManager.get_bitlocker_status,
                'extra_button': ('打开面板', SystemSettingsManager.open_bitlocker_settings),
                'confirm': self._bl_confirm,
            },
            {
                'id': 'delivery',
                'group': 'DELIVERY OPTIMIZATION',
                'title': '关闭传递优化',
                'description': '禁用P2P更新分发给其他PC (DODownloadMode=0)',
                'apply_text': '关闭',
                'restore_text': '恢复',
                'apply_style': BD,
                'has_restore': True,
                'apply': SystemSettingsManager.disable_delivery_opt,
                'restore': SystemSettingsManager.enable_delivery_opt,
                'detect': SystemSettingsManager.get_delivery_opt_status,
            },
            {
                'id': 'privacy',
                'group': 'PRIVACY',
                'title': '关闭隐私常规项',
                'description': '广告ID · 语言列表访问 · 应用启动追踪 · 设置建议内容推广',
                'apply_text': '关闭',
                'restore_text': '恢复',
                'apply_style': BD,
                'has_restore': True,
                'apply': SystemSettingsManager.disable_privacy_general,
                'restore': SystemSettingsManager.enable_privacy_general,
                'detect': SystemSettingsManager.get_privacy_status,
            },
        )

        for spec in system_level_cards:
            cl.addWidget(_gl(spec['group']))
            cl.addWidget(_sep())

            for widget in spec.get('pre_widgets', ()):
                cl.addWidget(widget)

            card = ACard(
                spec['title'],
                spec['description'],
                spec['id'],
                spec['apply_text'],
                spec['restore_text'],
                spec['apply_style'],
                BS,
                spec['has_restore'],
                spec.get('extra_button'),
                logger,
            )
            card.bind(
                spec['apply'],
                spec['detect'],
                spec['restore'],
                cfn=spec.get('confirm'),
            )
            self.cards[spec['id']] = card
            cl.addWidget(card)
            cl.addSpacing(3)
        cl.addWidget(_tip('游戏玩家建议关闭传递优化: 减少上传带宽占用，降低网络延迟'))
        # --- 启动、后台应用与桌面体验 ----------------------------------------------
        _make_toggle(
            cl,
            'FAST STARTUP (HIBERNATE)',
            'fast_boot',
            '关闭快速启动',
            '禁用HiberbootEnabled，让系统真正完全关机',
            '游戏玩家建议关闭: 真正关机可清空内存/驱动状态，避免长时间累积的性能衰退和驱动异常',
            logger,
            SystemSettingsManager.disable_fast_boot,
            SystemSettingsManager.enable_fast_boot,
            SystemSettingsManager.get_fast_boot_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'STARTUP SPEED',
            'startup_delay',
            '加快Windows启动速度',
            '消除登录后应用程序启动延迟 (StartupDelayInMSec=0)',
            '游戏玩家建议关闭延迟: 缩短开机到可用的等待时间',
            logger,
            SystemSettingsManager.disable_fast_startup_delay,
            SystemSettingsManager.enable_fast_startup_delay,
            SystemSettingsManager.get_fast_startup_delay_status,
            self.cards,
            ot='应用',
        )
        _make_toggle(
            cl,
            'AUTO UPDATE APPS',
            'auto_update_apps',
            '关闭系统启动时自动更新应用',
            '阻止Windows在启动时自动下载/更新Store应用',
            '游戏玩家建议关闭: 减少开机时后台IO和CPU占用',
            logger,
            SystemSettingsManager.disable_auto_update_apps,
            SystemSettingsManager.enable_auto_update_apps,
            SystemSettingsManager.get_auto_update_apps_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'UWP BACKGROUND APPS',
            'uwp_bg',
            '关闭UWP应用后台运行',
            '阻止Microsoft Store应用在后台运行，减少ACPI唤醒',
            '游戏玩家强烈建议关闭: 大量UWP后台应用抢占CPU/内存资源，直接影响游戏帧率稳定性',
            logger,
            SystemSettingsManager.disable_uwp_background,
            SystemSettingsManager.enable_uwp_background,
            SystemSettingsManager.get_uwp_background_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'OFFLINE MAPS',
            'offline_maps',
            '关闭离线地图自动更新',
            '禁用Windows离线地图的后台自动下载',
            '游戏玩家建议关闭: 减少不必要的后台网络和磁盘活动',
            logger,
            SystemSettingsManager.disable_offline_maps,
            SystemSettingsManager.enable_offline_maps,
            SystemSettingsManager.get_offline_maps_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'STORE BACKGROUND UPDATES',
            'store_bg_update',
            '关闭Microsoft Store后台自动更新',
            '通过组策略禁用Store应用的后台自动更新',
            '游戏玩家建议关闭: 防止Store在游戏时后台更新应用抢占带宽和IO',
            logger,
            SystemSettingsManager.disable_store_auto_update,
            SystemSettingsManager.enable_store_auto_update,
            SystemSettingsManager.get_store_auto_update_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'EDGE STARTUP',
            'edge_startup',
            '关闭Edge启动加速和后台运行',
            '移除Windows启动时Edge的后台自动启动和预加载',
            '游戏玩家建议关闭: Edge后台预加载会常驻占用200-400MB内存',
            logger,
            SystemSettingsManager.disable_edge_startup,
            SystemSettingsManager.enable_edge_startup,
            SystemSettingsManager.get_edge_startup_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'INDEXING SERVICE',
            'indexing',
            '关闭Windows索引服务',
            '停止WSearch文件索引器服务，降低后台磁盘负载',
            '游戏玩家建议关闭: 索引器会导致SSD随机写入增加，可能引起游戏微卡顿',
            logger,
            SystemSettingsManager.disable_indexing,
            SystemSettingsManager.enable_indexing,
            SystemSettingsManager.get_indexing_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'WIDGETS',
            'widgets',
            '关闭Win11小部件面板',
            '禁用Win11小部件面板和资讯与兴趣',
            '游戏玩家建议关闭: 小部件常驻后台占用资源，且会不定时刷新网络数据',
            logger,
            SystemSettingsManager.disable_widgets,
            SystemSettingsManager.enable_widgets,
            SystemSettingsManager.get_widgets_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'CLOUD SYNC',
            'cloud_sync',
            '关闭云同步',
            '禁止通过OneDrive同步主题、密码和设置',
            '游戏玩家建议关闭: 减少后台同步的网络和磁盘占用',
            logger,
            SystemSettingsManager.disable_cloud_sync,
            SystemSettingsManager.enable_cloud_sync,
            SystemSettingsManager.get_cloud_sync_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'MS ACCOUNT SYNC',
            'ms_sync',
            '关闭Microsoft账户同步',
            '禁用系统设置同步和MobSync.exe进程',
            '游戏玩家建议关闭: 减少后台同步进程',
            logger,
            SystemSettingsManager.disable_ms_sync,
            SystemSettingsManager.enable_ms_sync,
            SystemSettingsManager.get_ms_sync_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'PRINTER SERVICE',
            'printer_svc',
            '关闭打印机服务',
            '停止Print Spooler服务 (如不使用打印机)',
            '游戏玩家建议关闭: 不使用打印机时关闭可减少一个后台服务和潜在攻击面',
            logger,
            SystemSettingsManager.disable_printer_device,
            SystemSettingsManager.enable_printer_device,
            SystemSettingsManager.get_printer_device_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'TRANSPARENCY',
            'transparency',
            '关闭透明效果',
            '禁用窗口、任务栏透明特效，降低GPU合成开销',
            '游戏玩家建议关闭: 减少DWM合成器GPU占用，旧显卡效果更明显',
            logger,
            SystemSettingsManager.disable_transparency,
            SystemSettingsManager.enable_transparency,
            SystemSettingsManager.get_transparency_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'ANIMATIONS',
            'animation',
            '关闭动画和视觉特效',
            '禁用窗口最小化/最大化动画、任务栏动画',
            '游戏玩家建议关闭: 减少UI渲染开销，窗口切换更快',
            logger,
            SystemSettingsManager.disable_animation,
            SystemSettingsManager.enable_animation,
            SystemSettingsManager.get_animation_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'WIN10 CONTEXT MENU',
            'context_menu',
            '还原Win10经典右键菜单',
            '绕过Win11的「显示更多选项」折叠菜单，一步到位显示全部选项',
            '游戏玩家建议开启: Win10右键菜单响应更快，Mod管理更方便',
            logger,
            SystemSettingsManager.disable_context_menu,
            SystemSettingsManager.enable_context_menu,
            SystemSettingsManager.get_context_menu_status,
            self.cards,
            ot='还原',
        )
        _make_toggle(
            cl,
            'TASKBAR ALIGNMENT',
            'taskbar_align',
            '任务栏图标左对齐',
            '将Win11居中的任务栏图标改回Win10风格的左对齐',
            None,
            logger,
            SystemSettingsManager.disable_taskbar_center,
            SystemSettingsManager.enable_taskbar_center,
            SystemSettingsManager.get_taskbar_align_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'TASKVIEW BUTTON',
            'taskview',
            '隐藏任务视图按钮',
            '移除任务栏上的任务视图/虚拟桌面入口按钮',
            '游戏玩家可选: 减少误触，纯游戏机不需要虚拟桌面',
            logger,
            SystemSettingsManager.disable_taskview,
            SystemSettingsManager.enable_taskview,
            SystemSettingsManager.get_taskview_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'CHAT ICON',
            'chat_icon',
            '隐藏Chat图标',
            '移除任务栏上的Chat/Meet Now图标',
            '游戏玩家建议隐藏: 减少不必要的任务栏占用',
            logger,
            SystemSettingsManager.disable_chat_icon,
            SystemSettingsManager.enable_chat_icon,
            SystemSettingsManager.get_chat_icon_status,
            self.cards,
        )
        # --- 任务栏与资源管理器 -------------------------------------------------
        cl.addWidget(_gl('END TASK'))
        cl.addWidget(_sep())
        et = ACard(
            '启用任务栏右键「结束任务」',
            '右键点击任务栏应用图标可直接强制结束进程 (Build 22631+)',
            'end_task',
            '启用',
            '关闭',
            BS,
            BD,
            True,
            logger=logger,
        )
        et.bind(
            SystemSettingsManager.enable_end_task,
            SystemSettingsManager.get_end_task_status,
            SystemSettingsManager.disable_end_task,
            restore_snapshot=False,
        )
        self.cards['end_task'] = et
        cl.addWidget(et)
        cl.addWidget(_tip('游戏玩家强烈建议启用: 游戏卡死时可直接右键任务栏结束进程，无需打开任务管理器'))
        cl.addSpacing(3)
        cl.addWidget(_gl('FILE EXPLORER'))
        cl.addWidget(_sep())
        fe1 = ACard(
            '显示已知文件扩展名',
            'Windows默认隐藏.exe/.dll等扩展名，存在安全风险',
            'file_ext',
            '显示',
            '隐藏',
            BS,
            BD,
            True,
            logger=logger,
        )
        fe1.status_overrides = {'已显示': 'on', '已隐藏': 'w'}
        fe1.bind(
            SystemSettingsManager.show_file_ext,
            SystemSettingsManager.get_file_ext_status,
            SystemSettingsManager.hide_file_ext,
            restore_snapshot=False,
        )
        self.cards['file_ext'] = fe1
        cl.addWidget(fe1)
        cl.addWidget(_tip('游戏玩家建议显示: 安装Mod时能分清.dll和.dll.txt，避免下载伪装文件'))
        cl.addSpacing(3)
        fe2 = ACard(
            '显示隐藏的文件和文件夹',
            '在资源管理器中显示系统和用户隐藏的项目',
            'hidden_files',
            '显示',
            '隐藏',
            BS,
            BD,
            True,
            logger=logger,
        )
        fe2.status_overrides = {'已显示': 'on', '已隐藏': 'w'}
        fe2.bind(
            SystemSettingsManager.show_hidden_files,
            SystemSettingsManager.get_hidden_files_status,
            SystemSettingsManager.hide_hidden_files,
            restore_snapshot=False,
        )
        self.cards['hidden_files'] = fe2
        cl.addWidget(fe2)
        cl.addSpacing(3)
        fe3 = ACard(
            '文件资源管理器打开到「此电脑」',
            'Win11默认打开到主页，改为直接显示所有磁盘驱动器',
            'explorer_to',
            '此电脑',
            '主页',
            BP,
            BG,
            True,
            logger=logger,
        )
        fe3.bind(
            SystemSettingsManager.set_explorer_thispc,
            SystemSettingsManager.get_explorer_thispc_status,
            SystemSettingsManager.set_explorer_home,
            restore_snapshot=False,
        )
        self.cards['explorer_to'] = fe3
        cl.addWidget(fe3)
        cl.addWidget(_tip('游戏玩家建议改为此电脑: 快速访问游戏安装的磁盘分区'))
        cl.addSpacing(3)
        cl.addWidget(_gl('DEVICE MANAGER'))
        cl.addWidget(_sep())
        for fn, hw in DEVICES_TO_MANAGE:
            cid = f'dev_{hw}'
            card = ACard(f'关闭 {fn}', f'硬件 ID: {hw}', cid, '禁用', '恢复', BD, BS, True, logger=logger)
            card.bind(
                partial(SystemSettingsManager.disable_device, hw),
                partial(SystemSettingsManager.get_device_status_detect, hw),
                partial(SystemSettingsManager.enable_device, hw),
            )
            self.cards[cid] = card
            cl.addWidget(card)
            cl.addSpacing(3)
        cl.addWidget(_gl('REMINDERS · 需手动操作'))
        cl.addWidget(_sep())
        cl.addWidget(
            _info_card('ℹ', 'Microsoft Edge 浏览器设置', ['请手动操作: Edge → 设置 → 系统和性能 → 系统', '  ① 关闭「关闭 Microsoft Edge 后继续运行后台扩展和应用」', '  ② 关闭「启用增强」'], QColor(239, 246, 255), QColor(191, 219, 254), '#2563EB'),
        )
        cl.addSpacing(3)
        cl.addWidget(
            _info_card('ℹ', '网卡全双工设置', ['请手动操作: 设备管理器 → 网络适配器 → 右键属性 → 高级', '  找到「Speed & Duplex」或「连接速度和双工模式」', '  将其设置为对应速率的「全双工」(如 1.0 Gbps Full Duplex)'], QColor(239, 246, 255), QColor(191, 219, 254), '#2563EB'),
        )
        cl.addStretch()
        root.addWidget(_scroll(ct))

    def _bl_confirm(self):
        return _ask(self, '确认关闭 BitLocker', '确定关闭 BitLocker?\n解密在后台运行，期间请勿强制关机。')

    def detect_all(self):
        _detect_cards_batch(self.cards.values(), self.logger, '系统设置', self)
