"""跨模块共享的 Windows 服务、注册表、计划任务和应用常量。"""

import winreg
WR = 10
SERVICES_LIST = [
    ('diagsvc', 'Diagnostic Execution Service', '诊断执行服务'),
    ('DPS', 'Diagnostic Policy Service', '诊断策略服务'),
    ('WdiServiceHost', 'Diagnostic Service Host', '诊断服务主机'),
    ('WdiSystemHost', 'Diagnostic System Host', '诊断系统主机'),
    ('whesvc', 'Windows Health and Optimized Experiences', 'Windows 健康状况与优化体验'),
    ('SysMain', 'SysMain', 'SysMain (Superfetch)'),
    ('PrintNotify', 'Printer Extensions and Notifications', '打印机扩展和通知'),
    ('PrintDeviceConfigurationService', 'Print Device Configuration Service', '打印设备配置服务'),
    ('SEMgrSvc', 'Payments and NFC/SE Manager', '付款和 NFC/SE 管理器'),
    ('XboxGipSvc', 'Xbox Accessory Management Service', 'Xbox Accessory Management'),
    ('XblAuthManager', 'Xbox Live Auth Manager', 'Xbox Live 身份验证管理器'),
    ('XboxNetApiSvc', 'Xbox Live Networking Service', 'Xbox Live 网络服务'),
    ('XblGameSave', 'Xbox Live Game Save', 'Xbox Live 游戏保存'),
    ('RetailDemo', 'Retail Demo Service', '零售演示服务'),
    ('MicrosoftEdgeElevationService', 'Microsoft Edge Elevation Service', 'Edge Elevation Service'),
    ('edgeupdate', 'Microsoft Edge Update Service', 'Edge Update (edgeupdate)'),
    ('edgeupdatem', 'Microsoft Edge Update Service', 'Edge Update (edgeupdatem)'),
]
EDGE_STOP_GREEN_SERVICES = {'MicrosoftEdgeElevationService', 'edgeupdate', 'edgeupdatem'}
PRIVACY_GENERAL_ITEMS = [
    (winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo', 'Enabled', 0, 1, '广告 ID 个性化'),
    (winreg.HKEY_CURRENT_USER, 'Control Panel\\International\\User Profile', 'HttpAcceptLanguageOptOut', 1, 0, '网站语言列表访问'),
    (winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'Start_TrackProcs', 0, 1, '应用启动跟踪'),
    (winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager', 'SubscribedContent-338393Enabled', 0, 1, 'Windows 使用技巧气泡通知'),
    (winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager', 'SubscribedContent-353694Enabled', 0, 1, '设置应用内 Microsoft 推广横幅'),
    (winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager', 'SubscribedContent-353696Enabled', 0, 1, '设置主页推荐卡片 (OneDrive/M365)'),
]
DEVICES_TO_MANAGE = [
    ('系统计时器', 'PNP0100'),
    ('UMBus Root Bus Enumerator', 'UMBUS'),
    ('高精度事件计时器 (HPET)', 'PNP0103'),
]
PP_SUB = '54533251-82be-4824-96c1-47b60b740d00'
HIDDEN_POWER = [
    ('7f2f5cfa-f10c-4823-b5e1-e93ae85f46b5', '生效的异类策略'),
    ('93b8b6dc-0698-4d1c-9ee4-0644e900c85d', '异类线程调度策略'),
    ('bae08b81-2d5e-4688-ad6a-13243356654b', '短线程调度策略'),
    ('be337238-0d82-4146-a960-4f3749d470c7', '性能提升模式'),
]
BLOAT_APPS = (
    'Clipchamp.Clipchamp',
    'Microsoft.549981C3F5F10',
    'Microsoft.BingNews',
    'Microsoft.BingWeather',
    'Microsoft.Getstarted',
    'Microsoft.MicrosoftOfficeHub',
    'Microsoft.MicrosoftSolitaireCollection',
    'Microsoft.MicrosoftStickyNotes',
    'Microsoft.People',
    'Microsoft.PowerAutomateDesktop',
    'Microsoft.Todos',
    'Microsoft.WindowsAlarms',
    'Microsoft.WindowsFeedbackHub',
    'Microsoft.WindowsMaps',
    'Microsoft.WindowsSoundRecorder',
    'Microsoft.ZuneVideo',
    'MicrosoftCorporationII.MicrosoftFamily',
    'MicrosoftCorporationII.QuickAssist',
    'MicrosoftTeams',
    'MSTeams',
    'Microsoft.MicrosoftJournal',
    'Microsoft.News',
    'Microsoft.SkypeApp',
    'Microsoft.Office.OneNote',
    'Microsoft.3DBuilder',
    'Microsoft.Microsoft3DViewer',
    'Microsoft.Print3D',
    'Microsoft.MixedReality.Portal',
    'Microsoft.BingFinance',
    'Microsoft.BingSports',
    'Microsoft.BingTranslator',
)
THIRD_BLOAT_APPS = (
    'king.com.CandyCrushSaga',
    'king.com.CandyCrushSodaSaga',
    'king.com.BubbleWitch3Saga',
    'SpotifyAB.SpotifyMusic',
    'Disney',
    'Facebook',
    'Instagram',
    'TikTok',
    'Twitter',
    'Netflix',
    'AmazonVideo.PrimeVideo',
    'Amazon.com.Amazon',
    'Duolingo-LearnLanguagesforFree',
    'Flipboard',
    'PicsArt-PhotoStudio',
    'Plex',
    'Shazam',
    'Viber',
    'WinZipUniversal',
    'AdobeSystemsIncorporated.AdobePhotoshopExpress',
    'LinkedInforWindows',
    'HULULLLC.HULUPLUS',
)
APP_EXP_TASK_PATH = '\\Microsoft\\Windows\\Application Experience' + '\\'
CEIP_TASK_PATH = '\\Microsoft\\Windows\\Customer Experience Improvement Program' + '\\'
FEEDBACK_TASK_PATH = '\\Microsoft\\Windows\\Feedback\\Siuf' + '\\'
POWER_DIAG_TASK_PATH = '\\Microsoft\\Windows\\Power Efficiency Diagnostics' + '\\'
SETTING_SYNC_TASK_PATH = '\\Microsoft\\Windows\\SettingSync' + '\\'
