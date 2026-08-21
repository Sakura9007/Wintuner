"""高级设置页面。"""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QWidget
from wintuner.core.workers import MixIn
from wintuner.advanced_settings import AdvancedSettingsManager
from wintuner.ui.styles import BG, BP, BD, BS, BCR
from wintuner.ui.widgets import (
    ACard,
    DashboardColumns,
    MESSAGE_QSS,
    _ask,
    _detect_cards_batch,
    _gl,
    _make_toggle,
    _page_header,
    _scroll,
    _sep,
    _toolbar,
    _warn_card,
)


class AdvancedPage(QWidget, MixIn):
    """安全、隐私、遥测与高级策略页面。"""

    def __init__(self, logger, parent=None):
        super().__init__(parent)
        MixIn._init_workers(self)
        self.logger = logger
        self.cards = {}
        self.setAutoFillBackground(False)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(_page_header('高级设置', '安全策略、遥测、隐私与底层系统行为集中管理；高风险项保留确认流程。', 'ADVANCED / POLICY'))
        root.addWidget(_toolbar([('刷新状态', BP, self.detect_all)]))
        ct = QWidget()
        ct.setAutoFillBackground(False)
        ct.setStyleSheet('background:transparent;')
        cl = DashboardColumns(ct)
        # --- 安全与防护 -----------------------------------------------------
        cl.addWidget(_gl('FIREWALL'))
        cl.addWidget(_sep())
        fw = ACard(
            'Windows 防火墙',
            '关闭 Windows Defender 防火墙；恢复时按修改前的各配置文件状态精确还原',
            'firewall',
            '关闭',
            '恢复',
            BD,
            BS,
            True,
            logger=logger,
        )
        fw.bind(
            AdvancedSettingsManager.disable_firewall,
            AdvancedSettingsManager.get_firewall_status,
            AdvancedSettingsManager.enable_firewall,
            cfn=self._fw_confirm,
        )
        self.cards['firewall'] = fw
        cl.addWidget(fw)
        cl.addSpacing(3)
        cl.addWidget(_gl('WINDOWS DEFENDER'))
        cl.addWidget(_sep())
        cl.addWidget(
            _warn_card('⛔', '危险操作 · 现代 Windows 10/11 客户端无法可靠卸载 Defender 系统组件；此操作会持久禁用其实时防护。执行前必须先关闭「篡改保护」', QColor(254, 242, 242), QColor(252, 165, 165), '#DC2626', '#DC2626'),
        )
        dfc = ACard(
            '强制禁用 Windows Defender',
            'PowerShell + 当前有效策略 + 计划任务 + 状态验证 (三次确认)',
            'defender',
            '⛔ 强制禁用',
            '',
            BCR,
            BG,
            False,
            logger=logger,
        )
        dfc.bind(
            AdvancedSettingsManager.remove_defender,
            AdvancedSettingsManager.get_defender_status,
            cfn=self._def_confirm,
        )
        self.cards['defender'] = dfc
        cl.addWidget(dfc)
        cl.addSpacing(3)
        cl.addWidget(_gl('BCD BOOT TIMER'))
        cl.addWidget(_sep())
        bcd = ACard(
            '禁用动态时钟 + 启用平台时钟',
            'bcdedit /set disabledynamictick yes  ·  bcdedit /set useplatformtick yes',
            'bcdedit',
            '应用',
            '还原',
            BP,
            BG,
            True,
            logger=logger,
        )
        bcd.bind(
            AdvancedSettingsManager.set_bcdedit_timers,
            AdvancedSettingsManager.get_bcdedit_status,
            AdvancedSettingsManager.reset_bcdedit_timers,
        )
        self.cards['bcdedit'] = bcd
        cl.addWidget(bcd)
        cl.addSpacing(3)
        cl.addWidget(_gl('MEMORY'))
        cl.addWidget(_sep())
        mc = ACard(
            '关闭内存压缩',
            'Disable-MMAgent -MemoryCompression (需重启生效)',
            'memcompress',
            '关闭',
            '恢复',
            BD,
            BS,
            True,
            logger=logger,
        )
        mc.bind(
            AdvancedSettingsManager.disable_memory_compression,
            AdvancedSettingsManager.get_memory_compression_status,
            AdvancedSettingsManager.enable_memory_compression,
        )
        self.cards['memcompress'] = mc
        cl.addWidget(mc)
        cl.addSpacing(3)
        _make_toggle(
            cl,
            'SECURITY NOTIFICATIONS',
            'sec_notif',
            '关闭安全通知',
            '禁用安全和维护通知，消除启动文件时的多余警告',
            '游戏玩家建议关闭: 减少弹窗干扰，尤其是全屏游戏时的通知打断',
            logger,
            AdvancedSettingsManager.disable_security_notif,
            AdvancedSettingsManager.enable_security_notif,
            AdvancedSettingsManager.get_security_notif_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'SMARTSCREEN',
            'smartscreen',
            '关闭SmartScreen过滤器',
            '禁用SmartScreen，停止对链接和下载的云检查',
            '游戏玩家可选关闭: 减少首次启动游戏/Mod时的云检查延迟，但会降低安全性',
            logger,
            AdvancedSettingsManager.disable_smartscreen,
            AdvancedSettingsManager.enable_smartscreen,
            AdvancedSettingsManager.get_smartscreen_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'WPBT',
            'wpbt',
            '关闭Windows平台二进制表',
            '禁止从UEFI WPBT执行OEM二进制文件',
            '游戏玩家建议关闭: 阻止OEM厂商通过固件注入后台软件，减少启动时不必要的负载',
            logger,
            AdvancedSettingsManager.disable_wpbt,
            AdvancedSettingsManager.enable_wpbt,
            AdvancedSettingsManager.get_wpbt_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'AMSI',
            'amsi',
            '关闭AMSI接口',
            '禁用反恶意软件扫描接口，防止脚本被防病毒检查',
            '游戏玩家谨慎关闭: 可减少脚本执行时的扫描开销，但会降低恶意脚本防护能力',
            logger,
            AdvancedSettingsManager.disable_amsi,
            AdvancedSettingsManager.enable_amsi,
            AdvancedSettingsManager.get_amsi_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'CODE INTEGRITY',
            'code_integrity',
            '关闭代码完整性',
            '停止驱动信誉过滤器和易受攻击模块黑名单(W11)',
            '游戏玩家可选关闭: 某些反作弊驱动可能与HVCI冲突，关闭后可解决部分游戏启动问题',
            logger,
            AdvancedSettingsManager.disable_code_integrity,
            AdvancedSettingsManager.enable_code_integrity,
            AdvancedSettingsManager.get_code_integrity_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'UAC',
            'uac',
            '关闭用户账户控制',
            '移除Windows 11中的UAC提示 (需重启)',
            '游戏玩家可选关闭: 减少权限弹窗，但大幅降低系统安全性，建议保留',
            logger,
            AdvancedSettingsManager.disable_uac,
            AdvancedSettingsManager.enable_uac,
            AdvancedSettingsManager.get_uac_status,
            self.cards,
        )
        sw = _warn_card(
            '⚠',
            'AMD Ryzen 5000+用户请勿关闭Spectre V2! 英特尔CPU可安全关闭，帧率通常不受影响',
            QColor(254, 243, 199, 200),
            QColor(253, 224, 71, 200),
            '#D97706',
            '#92400E',
        )
        _make_toggle(
            cl,
            'SPECTRE V2 MITIGATION',
            'spectre',
            '关闭Spectre V2缓解',
            '禁用Spectre V2补丁，可能提升CPU性能 (需重启)',
            'Intel游戏玩家建议关闭: 可获得约2-5%的性能提升。AMD Ryzen 5000+务必保持开启!',
            logger,
            AdvancedSettingsManager.disable_spectre,
            AdvancedSettingsManager.enable_spectre,
            AdvancedSettingsManager.get_spectre_status,
            self.cards,
            pre_widgets=[sw],
        )
        _make_toggle(
            cl,
            'XBOX GAME BAR',
            'xbox_gamebar',
            '移除Xbox Game Bar',
            '禁用Game DVR/后台录制并移除Game Bar覆盖层',
            '游戏玩家强烈建议关闭: Game Bar覆盖层和后台录制会显著降低帧率(约3-8%)和增加输入延迟',
            logger,
            AdvancedSettingsManager.disable_xbox_gamebar,
            AdvancedSettingsManager.enable_xbox_gamebar,
            AdvancedSettingsManager.get_xbox_gamebar_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'COPILOT',
            'copilot',
            '关闭Windows Copilot',
            '禁用内置AI Copilot和其本地数据分析',
            '游戏玩家建议关闭: Copilot后台进程占用内存和CPU资源',
            logger,
            AdvancedSettingsManager.disable_copilot,
            AdvancedSettingsManager.enable_copilot,
            AdvancedSettingsManager.get_copilot_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'WINDOWS RECALL',
            'recall',
            '关闭Windows Recall快照',
            '禁用AI屏幕截图分析(DisableAIDataAnalysis=1)，防止隐私泄露',
            '游戏玩家强烈建议关闭: Recall持续截屏分析，严重消耗CPU/磁盘/内存，且存在隐私风险',
            logger,
            AdvancedSettingsManager.disable_recall,
            AdvancedSettingsManager.enable_recall,
            AdvancedSettingsManager.get_recall_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'AI FABRIC SERVICE',
            'ai_svc',
            '关闭AI Fabric服务自启',
            '仅在系统真实安装 WSAIFabricSvc 时操作；未安装或仅存在旧版残留注册表键时显示为未安装',
            '支持该服务的系统可选关闭；不支持的系统会安全跳过，不再产生检测失败或幽灵服务项',
            logger,
            AdvancedSettingsManager.disable_ai_svc,
            AdvancedSettingsManager.enable_ai_svc,
            AdvancedSettingsManager.get_ai_svc_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'EDGE AI FEATURES',
            'edge_ai',
            '关闭Edge AI功能',
            '通过组策略禁用Edge的Copilot侧边栏、AI页面分析等功能',
            '游戏玩家建议关闭: Edge AI功能增加浏览器内存占用和网络请求',
            logger,
            AdvancedSettingsManager.disable_edge_ai,
            AdvancedSettingsManager.enable_edge_ai,
            AdvancedSettingsManager.get_edge_ai_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'PAINT AI',
            'paint_ai',
            '关闭Paint AI功能',
            '通过策略禁用画图中的AI图像生成和编辑工具',
            '游戏玩家建议关闭: 不使用AI绘画功能时减少后台AI模型加载',
            logger,
            AdvancedSettingsManager.disable_paint_ai,
            AdvancedSettingsManager.enable_paint_ai,
            AdvancedSettingsManager.get_paint_ai_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'NOTEPAD AI',
            'notepad_ai',
            '关闭记事本AI功能',
            '通过策略禁用记事本的AI写作建议功能',
            '游戏玩家可选: 影响很小，但可减少不必要的AI功能加载',
            logger,
            AdvancedSettingsManager.disable_notepad_ai,
            AdvancedSettingsManager.enable_notepad_ai,
            AdvancedSettingsManager.get_notepad_ai_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'ACTIVITY HISTORY',
            'activity_hist',
            '关闭活动历史记录',
            '禁用PublishUserActivities，停止记录应用使用历史',
            '游戏玩家建议关闭: 减少后台活动数据收集和上传',
            logger,
            AdvancedSettingsManager.disable_activity_history,
            AdvancedSettingsManager.enable_activity_history,
            AdvancedSettingsManager.get_activity_history_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'TAILORED EXPERIENCES',
            'tailored_exp',
            '关闭个性化体验',
            '禁用诊断数据驱动的个性化体验+输入个性化+联系人收集',
            '游戏玩家建议关闭: 减少微软基于使用数据推送的个性化广告和建议',
            logger,
            AdvancedSettingsManager.disable_tailored_exp,
            AdvancedSettingsManager.enable_tailored_exp,
            AdvancedSettingsManager.get_tailored_exp_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'LOCATION SERVICES',
            'location',
            '关闭Windows位置服务',
            '禁用系统位置服务和应用位置访问权限',
            '游戏玩家建议关闭: 游戏PC通常不需要定位服务，关闭可减少后台GPS/WiFi扫描',
            logger,
            AdvancedSettingsManager.disable_location,
            AdvancedSettingsManager.enable_location,
            AdvancedSettingsManager.get_location_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'FIND MY DEVICE',
            'findmydevice',
            '关闭「查找我的设备」',
            '停止定期向微软上报设备位置的Find My Device功能',
            '游戏玩家建议关闭: 台式游戏PC不需要设备追踪，减少后台网络通信',
            logger,
            AdvancedSettingsManager.disable_findmydevice,
            AdvancedSettingsManager.enable_findmydevice,
            AdvancedSettingsManager.get_findmydevice_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'LOCKSCREEN TIPS',
            'lockscreen_tips',
            '关闭锁屏提示和广告',
            '禁用锁屏界面的趣味知识、Windows聚焦广告',
            '游戏玩家建议关闭: 消除锁屏界面的干扰信息，加快解锁流程',
            logger,
            AdvancedSettingsManager.disable_lockscreen_tips,
            AdvancedSettingsManager.enable_lockscreen_tips,
            AdvancedSettingsManager.get_lockscreen_tips_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'DESKTOP SPOTLIGHT',
            'desktop_spotlight',
            '关闭桌面Spotlight',
            '禁用Windows Spotlight桌面壁纸和提示',
            '游戏玩家建议关闭: 减少后台壁纸下载的网络和磁盘活动',
            logger,
            AdvancedSettingsManager.disable_desktop_spotlight,
            AdvancedSettingsManager.enable_desktop_spotlight,
            AdvancedSettingsManager.get_desktop_spotlight_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'UPDATE AUTO-RESTART',
            'update_restart',
            '阻止更新时自动重启',
            '登录期间阻止Windows因更新自动重启电脑',
            '游戏玩家强烈建议关闭: 防止游戏中途被系统强制重启更新',
            logger,
            AdvancedSettingsManager.disable_update_restart,
            AdvancedSettingsManager.enable_update_restart,
            AdvancedSettingsManager.get_update_restart_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'DEFER UPDATES',
            'early_update',
            '延迟接收新更新',
            '功能更新延迟30天、质量更新延迟7天，避免成为首批测试用户',
            '游戏玩家建议开启: 新更新可能引入游戏兼容性问题，延迟可等别人先踩坑',
            logger,
            AdvancedSettingsManager.disable_early_update,
            AdvancedSettingsManager.enable_early_update,
            AdvancedSettingsManager.get_early_update_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'TELEMETRY SERVICES',
            'tele_svc',
            '关闭遥测服务',
            '暂停DiagTrack/diagsvc/dmwappushservice主要诊断数据收集服务',
            '游戏玩家强烈建议关闭: 这些服务在后台持续收集数据，关闭可减少CPU和磁盘IO',
            logger,
            AdvancedSettingsManager.disable_telemetry_svc,
            AdvancedSettingsManager.enable_telemetry_svc,
            AdvancedSettingsManager.get_telemetry_svc_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'DATA COLLECTION POLICY',
            'data_collect',
            '关闭数据收集遥测策略',
            '强制设置诊断级别为无数据 (AllowTelemetry=0)',
            '游戏玩家强烈建议关闭: 从策略层面彻底禁止Windows诊断数据上传',
            logger,
            AdvancedSettingsManager.disable_data_collection,
            AdvancedSettingsManager.enable_data_collection,
            AdvancedSettingsManager.get_data_collection_status,
            self.cards,
        )
        _make_toggle(
            cl,
            '.NET TELEMETRY',
            'dotnet_tele',
            '关闭.NET远程监控',
            '设置DOTNET_CLI_TELEMETRY_OPTOUT=1环境变量',
            '游戏玩家建议关闭: 减少.NET应用的遥测网络请求',
            logger,
            AdvancedSettingsManager.disable_dotnet_telemetry,
            AdvancedSettingsManager.enable_dotnet_telemetry,
            AdvancedSettingsManager.get_dotnet_telemetry_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'POWERSHELL TELEMETRY',
            'ps_tele',
            '关闭PowerShell远程监控',
            '设置POWERSHELL_TELEMETRY_OPTOUT=1环境变量',
            '游戏玩家建议关闭: 减少PowerShell遥测数据发送',
            logger,
            AdvancedSettingsManager.disable_ps_telemetry,
            AdvancedSettingsManager.enable_ps_telemetry,
            AdvancedSettingsManager.get_ps_telemetry_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'DIAGNOSTIC EVENTS',
            'diag_events',
            '关闭电源效率诊断任务',
            '禁用 Power Efficiency Diagnostics\\AnalyzeSystem 计划任务，不再修改受保护的 Diagnostics 注册表键',
            '游戏玩家可选关闭: 避免后台电源效率分析任务；若 Windows 将任务设为受保护状态则会安全跳过',
            logger,
            AdvancedSettingsManager.disable_diag_events,
            AdvancedSettingsManager.enable_diag_events,
            AdvancedSettingsManager.get_diag_events_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'COMPAT INVENTORY',
            'compat_tel',
            '关闭兼容性清单收集器',
            '使用 Windows AppCompat 的 DisableInventory 策略关闭 Inventory Collector，不再强行修改受保护的 CompatTelRunner 计划任务',
            '游戏玩家可选关闭: 这是新版 Windows 上更稳定的兼容性清单收集控制；Application Telemetry 由下方 AIT ENABLE 单独管理',
            logger,
            AdvancedSettingsManager.disable_compat_telrunner,
            AdvancedSettingsManager.enable_compat_telrunner,
            AdvancedSettingsManager.get_compat_telrunner_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'CEIP DATA UPDATER',
            'ceip_updater',
            '关闭CEIP数据更新器',
            '停止ProgramDataUpdater任务',
            '游戏玩家建议关闭: 减少后台统计数据收集任务',
            logger,
            AdvancedSettingsManager.disable_ceip_updater,
            AdvancedSettingsManager.enable_ceip_updater,
            AdvancedSettingsManager.get_ceip_updater_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'AIT AGENT',
            'aitagent',
            '关闭应用影响遥测代理',
            '移除AitAgent应用启动统计任务',
            '游戏玩家建议关闭: 减少应用启动时的后台监控',
            logger,
            AdvancedSettingsManager.disable_aitagent,
            AdvancedSettingsManager.enable_aitagent,
            AdvancedSettingsManager.get_aitagent_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'CEIP TASKS',
            'ceip_tasks',
            '关闭CEIP任务',
            '停用Consolidator/KernelCeipTask/UsbCeip等任务',
            '游戏玩家建议关闭: 所有非Insider电脑均建议禁用，减少后台数据采集',
            logger,
            AdvancedSettingsManager.disable_ceip_tasks,
            AdvancedSettingsManager.enable_ceip_tasks,
            AdvancedSettingsManager.get_ceip_tasks_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'CEIP / SQM',
            'ceip_sqm',
            '关闭CEIP/SQM',
            '设置CEIPEnable=0，完全停止SQM数据收集',
            '游戏玩家建议关闭: 从注册表层面关闭客户体验改进计划',
            logger,
            AdvancedSettingsManager.disable_ceip_sqm,
            AdvancedSettingsManager.enable_ceip_sqm,
            AdvancedSettingsManager.get_ceip_sqm_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'AIT ENABLE',
            'ait_enable',
            '关闭应用影响遥测',
            '设置AITEnable=0，禁用应用影响统计数据收集',
            '游戏玩家建议关闭: 与AitAgent配合，从策略层面禁止应用影响追踪',
            logger,
            AdvancedSettingsManager.disable_ait_enable,
            AdvancedSettingsManager.enable_ait_enable,
            AdvancedSettingsManager.get_ait_enable_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'LICENSE TELEMETRY',
            'license_tele',
            '关闭许可证遥测',
            '禁止生成激活票 (NoGenTicket=1)',
            '游戏玩家建议关闭: 减少许可证验证的后台网络通信',
            logger,
            AdvancedSettingsManager.disable_license_telemetry,
            AdvancedSettingsManager.enable_license_telemetry,
            AdvancedSettingsManager.get_license_telemetry_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'SEARCH DATA COLLECTION',
            'search_data',
            '关闭搜索数据收集',
            '移除开始菜单网页结果和Bing搜索统计',
            '游戏玩家建议关闭: 禁用Bing搜索可加速开始菜单响应和减少网络请求',
            logger,
            AdvancedSettingsManager.disable_search_data,
            AdvancedSettingsManager.enable_search_data,
            AdvancedSettingsManager.get_search_data_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'TARGETED ADS',
            'targeted_ads',
            '关闭定向广告和营销',
            '关闭个性化提示、开始菜单广告和静默安装赞助应用',
            '游戏玩家强烈建议关闭: 阻止Windows静默安装Candy Crush等赞助应用，节省磁盘空间和网络带宽',
            logger,
            AdvancedSettingsManager.disable_targeted_ads,
            AdvancedSettingsManager.enable_targeted_ads,
            AdvancedSettingsManager.get_targeted_ads_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'INPUT FEEDBACK',
            'input_fb',
            '关闭输入反馈遥测',
            '停止在输入文本时发送遥测数据',
            '游戏玩家建议关闭: 减少每次键盘输入时的遥测数据发送',
            logger,
            AdvancedSettingsManager.disable_input_feedback,
            AdvancedSettingsManager.enable_input_feedback,
            AdvancedSettingsManager.get_input_feedback_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'FEEDBACK & DIAGNOSTICS',
            'feedback_diag',
            '关闭Windows反馈和诊断',
            '禁用体验分享和DmClient任务',
            '游戏玩家建议关闭: 阻止Windows后台收集使用体验数据',
            logger,
            AdvancedSettingsManager.disable_feedback_diag,
            AdvancedSettingsManager.enable_feedback_diag,
            AdvancedSettingsManager.get_feedback_diag_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'CLOUD SPEECH',
            'cloud_speech',
            '关闭云语音识别',
            '禁用在线语音识别功能',
            '游戏玩家建议关闭: 除非使用语音输入，否则关闭可减少后台服务',
            logger,
            AdvancedSettingsManager.disable_cloud_speech,
            AdvancedSettingsManager.enable_cloud_speech,
            AdvancedSettingsManager.get_cloud_speech_status,
            self.cards,
        )
        _make_toggle(
            cl,
            'WINDOWS ERROR REPORTING',
            'wer',
            '关闭Windows错误报告',
            '禁用WER服务和错误报告策略',
            '游戏玩家建议关闭: 游戏崩溃时不再发送错误报告，减少崩溃后的卡顿等待',
            logger,
            AdvancedSettingsManager.disable_wer,
            AdvancedSettingsManager.enable_wer,
            AdvancedSettingsManager.get_wer_status,
            self.cards,
        )
        cl.addSpacing(3)
        cl.addWidget(_gl('SYNAPTICS WORM CLEANER'))
        cl.addWidget(_sep())
        cl.addWidget(
            _warn_card('🔍', 'Synaptics 蠕虫通过感染 Office 文档和 USB 传播，会伪装为触控板驱动驻留系统。清理前建议先断网。', QColor(254, 243, 199, 200), QColor(253, 224, 71, 200), '#92400E', '#92400E'),
        )
        worm_scan = ACard(
            '扫描 Synaptics 蠕虫',
            '扫描进程、文件系统、注册表自启动项，检测蠕虫感染痕迹',
            'worm_scan',
            '全盘扫描',
            '',
            BP,
            BS,
            False,
            logger=logger,
        )
        worm_scan.bind(AdvancedSettingsManager.scan_synaptics, AdvancedSettingsManager.get_synaptics_status)
        self.cards['worm_scan'] = worm_scan
        cl.addWidget(worm_scan)
        worm_clean = ACard(
            '一键清理 Synaptics 蠕虫',
            '验证数字签名 → 精确终止可疑进程 → 删除可疑文件 → 清除匹配的自启动项',
            'worm_clean',
            '一键清理',
            '',
            BCR,
            BS,
            False,
            logger=logger,
        )
        worm_clean._gfn = AdvancedSettingsManager.get_synaptics_status
        self.cards['worm_clean'] = worm_clean
        cl.addWidget(worm_clean)
        worm_clean.bo.clicked.connect(self._worm_click)
        cl.addStretch()
        root.addWidget(_scroll(ct))

    def _fw_confirm(self):
        return _ask(self, '确认', '确定要关闭系统防火墙?')

    def _worm_click(self):
        box = QMessageBox(self)
        box.setWindowTitle('⚠ Synaptics 蠕虫清理')
        box.setText(
            '即将执行保守型蠕虫清理:\n\n  1. 验证候选文件数字签名\n  2. 仅终止路径与可疑文件完全匹配的进程\n  3. 仅删除未通过签名验证的可疑文件\n  4. 仅清除指向这些可疑文件的自启动项\n\n不会递归删除整个 Synaptics 目录，也不会处理无法确认的文件。\n建议清理前先断开网络连接。\n\n是否继续?',
        )
        box.setIcon(QMessageBox.Icon.Warning)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.setStyleSheet(MESSAGE_QSS)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.logger('▶ 执行: worm_clean')
            wc = self.cards['worm_clean']
            wc.bo.setEnabled(False)
            wc._run_action('worm_clean', 'apply_once', AdvancedSettingsManager.clean_synaptics, wc._done)

    def _def_confirm(self):
        confirmations = (
            (
                '⚠  第 1/3 次警告',
                '即将强制禁用 Windows Defender 实时防护!\n\n'
                '请确保已安装并启用可信的第三方杀毒。\n\n是否继续?',
                QMessageBox.Icon.Warning,
            ),
            (
                '⛔  第 2/3 次确认',
                '请再次确认:\n\n'
                '• 必须先手动关闭「篡改保护」\n'
                '• Windows 安全中心界面仍可能保留，这是正常现象\n'
                '• 完全生效后建议重启并重新检测\n\n是否继续?',
                QMessageBox.Icon.Critical,
            ),
            (
                '⛔  第 3/3 次最终确认',
                '最终确认!\n\n'
                '即将: 禁用实时/行为/脚本扫描 → 写入 Defender 实时保护策略 → '
                '禁用 Defender 计划任务 → 强制刷新组策略 → 验证实际状态\n\n'
                '点击 Yes 执行。',
                QMessageBox.Icon.Critical,
            ),
        )

        for index, (title, text, icon) in enumerate(confirmations, start=1):
            box = QMessageBox(self)
            box.setWindowTitle(title)
            box.setText(text)
            box.setIcon(icon)
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            box.setDefaultButton(QMessageBox.StandardButton.No)
            box.setStyleSheet(
                'QMessageBox{background:#FFFFFF;}'
                'QMessageBox QLabel{color:#111827;font-size:13px;}'
                'QMessageBox QPushButton{'
                'background:#F3F4F6;color:#374151;border:1px solid #E5E7EB;'
                'border-radius:5px;padding:5px 16px;min-width:64px;'
                '}'
                'QMessageBox QPushButton:hover{background:#E5E7EB;}'
            )
            if box.exec() != QMessageBox.StandardButton.Yes:
                self.logger(f'  ℹ 用户取消 (第 {index} 次)')
                return False

        return True

    def detect_all(self):
        _detect_cards_batch(self.cards.values(), self.logger, '高级设置', self)
