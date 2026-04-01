import json
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QFileInfo, QObject, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QFileDialog, QFileIconProvider, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

APP_NAME = "Windows 情景模式"
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "scene_config.json"
AUTOSTART_SCRIPT = "windowscene_autostart.cmd"
BG = "#f3f3f3"
PANEL = "#fbfbfb"
CARD = "#ffffff"
CARD_ALT = "#f9f9f9"
TEXT = "#1a1a1a"
SUBTLE = "#616161"
BORDER = "#e0e0e0"
ACCENT = "#0067c0"
ACCENT_HOVER = "#005a9e"
ACCENT_SOFT = "#e8f4fc"
SCENE_CARD_SIZE = 100
APP_CARD_W = 120
APP_CARD_H = 160
OPTION_GRID_SPACING = 10
DEFAULT_CONFIG = {
    "autostart_enabled": False,
    "launch_on_boot": True,
    "smart_scan_enabled": True,
    "scenes": {
        "游戏": {"keywords": ["steam", "epic", "battle", "game", "wegame", "riot"], "apps": []},
        "视频": {"keywords": ["potplayer", "vlc", "bilibili", "youtube", "netflix", "腾讯视频"], "apps": []},
        "音乐": {"keywords": ["spotify", "cloudmusic", "qqmusic", "musicbee", "foobar"], "apps": []},
        "阅读": {"keywords": ["calibre", "sumatrapdf", "zotero", "kindle", "pdf"], "apps": []},
        "上网": {"keywords": ["chrome", "edge", "firefox", "browser", "opera"], "apps": []},
        "编程": {"keywords": ["code", "pycharm", "cursor", "terminal", "git", "visual studio"], "apps": []},
        "工作": {"keywords": ["word", "excel", "powerpoint", "teams", "slack", "outlook", "钉钉"], "apps": []},
    },
}
SCENE_META = {
    "游戏": {"icon": "🎮", "subtitle": "性能优先，快速进入娱乐状态"},
    "视频": {"icon": "🎬", "subtitle": "播放器与在线视频一键就位"},
    "音乐": {"icon": "🎵", "subtitle": "打开你的听歌环境"},
    "阅读": {"icon": "📚", "subtitle": "文档、PDF 与阅读工具集中启动"},
    "上网": {"icon": "🌐", "subtitle": "浏览器与在线入口集中就位"},
    "编程": {"icon": "💻", "subtitle": "编辑器、终端与开发工具一起启动"},
    "工作": {"icon": "🗂", "subtitle": "办公协作与沟通应用整合在一个模式里"},
}
KNOWN_APPS = [
    {"name": "Chrome", "keywords": ["chrome"]}, {"name": "Edge", "keywords": ["msedge", "edge"]},
    {"name": "Firefox", "keywords": ["firefox"]}, {"name": "VS Code", "keywords": ["code"]},
    {"name": "Cursor", "keywords": ["cursor"]}, {"name": "PyCharm", "keywords": ["pycharm"]},
    {"name": "Steam", "keywords": ["steam"]}, {"name": "WeGame", "keywords": ["wegame"]},
    {"name": "Spotify", "keywords": ["spotify"]}, {"name": "网易云音乐", "keywords": ["cloudmusic"]},
    {"name": "QQ 音乐", "keywords": ["qqmusic"]}, {"name": "PotPlayer", "keywords": ["potplayer"]},
    {"name": "VLC", "keywords": ["vlc"]}, {"name": "SumatraPDF", "keywords": ["sumatrapdf"]},
    {"name": "Calibre", "keywords": ["calibre"]}, {"name": "Zotero", "keywords": ["zotero"]},
    {"name": "Word", "keywords": ["winword", "word"]}, {"name": "Excel", "keywords": ["excel"]},
    {"name": "PowerPoint", "keywords": ["powerpnt", "powerpoint"]}, {"name": "Teams", "keywords": ["teams"]},
    {"name": "Slack", "keywords": ["slack"]},
]


def deep_copy_default():
    return json.loads(json.dumps(DEFAULT_CONFIG, ensure_ascii=False))


def load_config():
    if not CONFIG_PATH.exists():
        save_config(deep_copy_default())
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = deep_copy_default()
        save_config(data)
    merged = deep_copy_default()
    merged.update({k: v for k, v in data.items() if k != "scenes"})
    for scene_name, scene_value in data.get("scenes", {}).items():
        merged["scenes"].setdefault(scene_name, {"keywords": [], "apps": []})
        merged["scenes"][scene_name].update(scene_value)
    return merged


def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_path(raw_path):
    return str(Path(raw_path).expanduser())


def get_startup_folder():
    appdata = os.environ.get("APPDATA")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" if appdata else None


def build_autostart_script():
    if getattr(sys, "frozen", False):
        launcher = Path(sys.executable)
        return f'@echo off\r\ncd /d "{BASE_DIR}"\r\nstart "" "{launcher}" --boot\r\n'

    pythonw = Path(sys.executable)
    if pythonw.name.lower() == "python.exe":
        pythonw = pythonw.with_name("pythonw.exe")
    return f'@echo off\r\ncd /d "{BASE_DIR}"\r\nstart "" "{pythonw}" "{BASE_DIR / "app.py"}" --boot\r\n'


def sync_autostart(config):
    startup_dir = get_startup_folder()
    if startup_dir is None:
        return False, "无法定位 Windows 启动目录。"
    startup_dir.mkdir(parents=True, exist_ok=True)
    target = startup_dir / AUTOSTART_SCRIPT
    if config.get("autostart_enabled"):
        target.write_text(build_autostart_script(), encoding="gbk", errors="ignore")
        return True, f"已写入开机启动脚本：{target}"
    if target.exists():
        target.unlink()
    return True, "已关闭开机自启动。"


def unique_app_entries(apps):
    seen, results = set(), []
    for app in apps:
        marker = (app.get("name", "").lower(), app.get("path", "").lower())
        if marker not in seen:
            seen.add(marker)
            results.append(app)
    return results


def unique_app_names(apps):
    seen, results = set(), []
    for app in apps:
        name = app.get("name", "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        results.append(app)
    return results


def detect_candidate_locations():
    env = os.environ
    locations = [
        Path(env.get("ProgramData", "C:/ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path(env.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "Desktop", Path("C:/Program Files"), Path("C:/Program Files (x86)"),
        Path(env.get("LOCALAPPDATA", "")) / "Programs",
    ]
    return [path for path in locations if str(path).strip() and path.exists()]


def scan_for_apps(limit=300):
    results, count = [], 0
    for location in detect_candidate_locations():
        try:
            for path in location.rglob("*"):
                if count >= limit:
                    return results
                if path.suffix.lower() not in {".lnk", ".exe"}:
                    continue
                lowered = path.name.lower()
                for known in KNOWN_APPS:
                    if any(keyword in lowered for keyword in known["keywords"]):
                        results.append({"name": known["name"], "path": str(path), "source": "智能识别"})
                        count += 1
                        break
        except (PermissionError, OSError):
            continue
    return unique_app_entries(results)


def recommend_apps_for_scene(scene_name, config, scanned_apps):
    scene = config["scenes"].get(scene_name, {})
    keywords = [word.lower() for word in scene.get("keywords", [])]
    recommendations = [{**app, "source": "预设配置"} for app in scene.get("apps", [])]
    for app in scanned_apps:
        lowered = f"{app.get('name', '')} {app.get('path', '')}".lower()
        if any(keyword in lowered for keyword in keywords):
            recommendations.append(app)
    return unique_app_names(unique_app_entries(recommendations))


def open_target(path):
    os.startfile(path)


def app_icon_pixmap(path, size=40):
    provider = QFileIconProvider()
    try:
        file_icon = provider.icon(QFileInfo(path))
        if not file_icon.isNull():
            pixmap = file_icon.pixmap(size, size)
            if not pixmap.isNull():
                return pixmap
    except Exception:
        pass
    try:
        icon = QIcon(path)
        if not icon.isNull():
            pixmap = icon.pixmap(size, size)
            if not pixmap.isNull():
                return pixmap
    except Exception:
        pass
    return QPixmap()


def apply_shadow(widget):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(14)
    shadow.setOffset(0, 2)
    shadow.setColor(QColor(0, 0, 0, 16))
    widget.setGraphicsEffect(shadow)


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class ClickableCard(QFrame):
    clicked = Signal()

    def __init__(self, selected=False, parent=None):
        super().__init__(parent)
        self.selected = selected
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setObjectName("card")
        self.setProperty("selected", selected)
        apply_shadow(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected):
        self.selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

class SceneCard(ClickableCard):
    def __init__(self, scene_name, selected=False, parent=None):
        super().__init__(selected=selected, parent=parent)
        meta = SCENE_META.get(scene_name, {"icon": "⬜", "subtitle": ""})
        self.setFixedSize(SCENE_CARD_SIZE, SCENE_CARD_SIZE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(4)
        icon = QLabel(meta["icon"])
        icon.setObjectName("sceneIcon")
        icon.setAlignment(Qt.AlignCenter)
        title = QLabel(scene_name)
        title.setObjectName("sceneTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addStretch(1)


class AppCard(ClickableCard):
    def __init__(self, app, selected=False, parent=None):
        super().__init__(selected=selected, parent=parent)
        self.app = app
        self.setFixedSize(APP_CARD_W, APP_CARD_H)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(3)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setPixmap(app_icon_pixmap(app["path"], 48))
        self.icon_label.setScaledContents(True)
        self.icon_label.setAlignment(Qt.AlignCenter)
        title = QLabel(app["name"])
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        source = QLabel(app.get("source", "推荐"))
        source.setObjectName("source")
        source.setAlignment(Qt.AlignCenter)
        path_label = QLabel(Path(app["path"]).name)
        path_label.setObjectName("appPath")
        path_label.setWordWrap(True)
        path_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(title)
        layout.addWidget(source)
        layout.addWidget(path_label)
        layout.addStretch(1)
        self.marker = QLabel("✓" if selected else "")
        self.marker.setObjectName("marker")
        self.marker.setFixedSize(18, 18)
        self.marker.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.marker, 0, Qt.AlignRight | Qt.AlignBottom)
        self.update_marker()

    def set_selected(self, selected):
        super().set_selected(selected)
        self.update_marker()

    def update_marker(self):
        self.marker.setText("✓" if self.selected else "")
        if self.selected:
            self.marker.setStyleSheet(
                f"background: {ACCENT}; color: white; border: none; border-radius: 6px;"
            )
        else:
            self.marker.setStyleSheet(
                f"background: transparent; color: transparent; border: 1px solid {BORDER}; border-radius: 6px;"
            )


class FlowGrid(QWidget):
    def __init__(self, columns=3, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(OPTION_GRID_SPACING)
        self.grid.setVerticalSpacing(OPTION_GRID_SPACING)

    def set_widgets(self, widgets):
        clear_layout(self.grid)
        for index, widget in enumerate(widgets):
            row, col = divmod(index, self.columns)
            self.grid.addWidget(widget, row, col)
        for col in range(self.columns):
            self.grid.setColumnStretch(col, 1)
        if widgets:
            total_rows = (len(widgets) + self.columns - 1) // self.columns
            self.grid.setRowStretch(total_rows, 1)

    def set_columns(self, columns):
        self.columns = max(1, columns)


class ScannerBridge(QObject):
    started = Signal()
    finished = Signal(list)


class ConfigDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("情景配置")
        self.resize(1080, 760)
        self.setModal(True)
        self.setStyleSheet(window.app_stylesheet())
        shell = QVBoxLayout(self)
        shell.setContentsMargins(18, 18, 18, 18)
        shell.setSpacing(14)
        title = QLabel("管理情景配置")
        title.setObjectName("heroTitle")
        body = QLabel("为每个情景管理应用列表和识别关键词。")
        body.setObjectName("heroBody")
        shell.addWidget(title)
        shell.addWidget(body)
        content = QHBoxLayout()
        content.setSpacing(14)
        shell.addLayout(content, 1)
        left_panel = self.window.create_panel()
        right_panel = self.window.create_panel()
        content.addWidget(left_panel, 0)
        content.addWidget(right_panel, 1)
        left_layout = left_panel.layout()
        left_layout.addWidget(self.window.section_label("选择要编辑的情景"))
        for scene_name in self.window.scene_names():
            button = QPushButton(f"{SCENE_META.get(scene_name, {}).get('icon', '⬜')}  {scene_name}")
            button.clicked.connect(lambda _=False, name=scene_name: self.switch_scene(name))
            left_layout.addWidget(button)
        left_layout.addStretch(1)
        right_layout = right_panel.layout()
        right_layout.addWidget(self.window.section_label("智能识别关键词"))
        self.keyword_edit = QLineEdit()
        right_layout.addWidget(self.keyword_edit)
        actions = QHBoxLayout()
        for text, handler in (("添加应用", self.add_app), ("保存当前情景", self.save_scene), ("刷新推荐", self.refresh_cards)):
            button = QPushButton(text)
            button.clicked.connect(handler)
            actions.addWidget(button)
        actions.addStretch(1)
        right_layout.addLayout(actions)
        right_layout.addSpacing(8)
        right_layout.addWidget(self.window.section_label("已配置应用"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.apps_host = QWidget()
        self.apps_layout = QVBoxLayout(self.apps_host)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(10)
        scroll.setWidget(self.apps_host)
        right_layout.addWidget(scroll, 1)
        self.refresh_cards()

    def switch_scene(self, scene_name):
        self.window.select_scene(scene_name)
        self.refresh_cards()

    def refresh_cards(self):
        self.keyword_edit.setText(", ".join(self.window.current_scene().get("keywords", [])))
        clear_layout(self.apps_layout)
        apps = self.window.current_scene().get("apps", [])
        if not apps:
            self.apps_layout.addWidget(self.window.empty_card("这个情景还没有手动配置应用", "点击上方“添加应用”，把 .exe 或 .lnk 加进来。"))
            self.apps_layout.addStretch(1)
            return
        for app in apps:
            row = self.window.create_soft_card()
            layout = row.layout()
            title = QLabel(app["name"])
            title.setObjectName("appTitle")
            path_label = QLabel(app["path"])
            path_label.setObjectName("appPath")
            path_label.setWordWrap(True)
            remove_button = QPushButton("移除")
            remove_button.clicked.connect(lambda _=False, item=app: self.remove_app(item))
            layout.addWidget(title)
            layout.addWidget(path_label)
            layout.addWidget(remove_button, alignment=Qt.AlignRight)
            self.apps_layout.addWidget(row)
        self.apps_layout.addStretch(1)

    def add_app(self):
        scene_name = self.window.current_scene_name
        file_path, _ = QFileDialog.getOpenFileName(self, "选择应用或快捷方式", str(BASE_DIR), "应用或快捷方式 (*.exe *.lnk);;所有文件 (*.*)")
        if not file_path:
            return
        app_name = Path(file_path).stem
        self.window.config["scenes"][scene_name]["apps"].append({"name": app_name, "path": normalize_path(file_path)})
        self.window.config["scenes"][scene_name]["apps"] = unique_app_entries(self.window.config["scenes"][scene_name]["apps"])
        save_config(self.window.config)
        self.window.refresh_all()
        self.refresh_cards()
        self.window.set_status(f"已添加应用：{app_name}")

    def save_scene(self):
        keywords = [item.strip() for item in self.keyword_edit.text().split(",") if item.strip()]
        self.window.config["scenes"][self.window.current_scene_name]["keywords"] = keywords
        save_config(self.window.config)
        self.window.refresh_all()
        self.refresh_cards()
        self.window.set_status(f"已保存情景：{self.window.current_scene_name}")

    def remove_app(self, app):
        apps = self.window.config["scenes"][self.window.current_scene_name]["apps"]
        self.window.config["scenes"][self.window.current_scene_name]["apps"] = [item for item in apps if item != app]
        save_config(self.window.config)
        self.window.refresh_all()
        self.refresh_cards()
        self.window.set_status(f"已移除应用：{app['name']}")


class QuickLaunchDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.cards = []
        self.setModal(True)
        self.resize(1040, 720)
        self.setWindowTitle(f"{window.current_scene_name} 应用选择")
        self.setStyleSheet(window.app_stylesheet())
        shell = QVBoxLayout(self)
        shell.setContentsMargins(18, 18, 18, 18)
        shell.setSpacing(14)
        title = QLabel(f"{SCENE_META.get(window.current_scene_name, {}).get('icon', '⬜')}  {window.current_scene_name} 模式")
        title.setObjectName("heroTitle")
        body = QLabel("勾选需要启动的应用，然后点击启动按钮。")
        body.setObjectName("heroBody")
        shell.addWidget(title)
        shell.addWidget(body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        self.grid = FlowGrid(columns=3)
        host_layout.addWidget(self.grid)
        scroll.setWidget(host)
        shell.addWidget(scroll, 1)
        actions = QHBoxLayout()
        launch_button = QPushButton("启动这个情景")
        launch_button.setObjectName("primaryButton")
        launch_button.clicked.connect(self.launch_now)
        config_button = QPushButton("打开完整配置窗口")
        config_button.clicked.connect(self.open_config)
        skip_button = QPushButton("本次忽略")
        skip_button.clicked.connect(self.reject)
        actions.addWidget(launch_button)
        actions.addWidget(config_button)
        actions.addStretch(1)
        actions.addWidget(skip_button)
        shell.addLayout(actions)
        self.refresh_cards()

    def refresh_cards(self):
        recommendations = recommend_apps_for_scene(self.window.current_scene_name, self.window.config, self.window.scanned_apps)
        self.cards = []
        if not recommendations:
            self.grid.set_widgets([self.window.empty_card("这个情景还没有可启动的应用", "你可以先打开完整配置窗口，为这个情景补充应用。")])
            return
        widgets = []
        for app in recommendations:
            card = AppCard(app, selected=app.get("source") == "预设配置")
            card.clicked.connect(lambda current=card: current.set_selected(not current.selected))
            self.cards.append(card)
            widgets.append(card)
        self.grid.set_widgets(widgets)

    def launch_now(self):
        chosen = [card.app for card in self.cards if card.selected]
        if not chosen:
            QMessageBox.information(self, APP_NAME, "当前没有勾选任何应用。")
            return
        launched, failed = [], []
        for app in chosen:
            try:
                open_target(app["path"])
                launched.append(app["name"])
            except OSError as exc:
                failed.append(f"{app['name']} ({exc})")
        lines = [f"已启动 {self.window.current_scene_name} 情景"]
        if launched:
            lines.append("已启动：" + "、".join(launched))
        if failed:
            lines.append("启动失败：" + "；".join(failed))
        QMessageBox.information(self, APP_NAME, "\n".join(lines))
        self.window.showNormal()
        self.window.raise_()
        self.accept()

    def open_config(self):
        self.accept()
        self.window.open_config_window()

class BootDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setModal(True)
        self.resize(960, 660)
        self.setWindowTitle("本次开机做什么")
        self.setStyleSheet(window.app_stylesheet())
        shell = QVBoxLayout(self)
        shell.setContentsMargins(18, 18, 18, 18)
        shell.setSpacing(14)
        title = QLabel("本次开机准备做什么？")
        title.setObjectName("heroTitle")
        body = QLabel("选择一个情景模式，快速启动相关应用。")
        body.setObjectName("heroBody")
        shell.addWidget(title)
        shell.addWidget(body)
        grid = FlowGrid(columns=3)
        cards = []
        for scene_name in self.window.scene_names():
            card = SceneCard(scene_name)
            card.clicked.connect(lambda name=scene_name: self.choose_scene(name))
            cards.append(card)
        grid.set_widgets(cards)
        shell.addWidget(grid, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        skip = QPushButton("本次忽略")
        skip.clicked.connect(self.reject)
        footer.addWidget(skip)
        shell.addLayout(footer)

    def choose_scene(self, scene_name):
        self.window.select_scene(scene_name)
        self.accept()
        self.window.open_quick_launch()


class MainWindow(QMainWindow):
    def __init__(self, boot_mode=False):
        super().__init__()
        self.boot_mode = boot_mode
        self.config = load_config()
        self.scanned_apps = []
        self.current_scene_name = self.scene_names()[0]
        self.app_cards = {}
        self.scanner_bridge = ScannerBridge()
        self.scanner_bridge.started.connect(lambda: self.set_status("正在智能识别常用应用..."))
        self.scanner_bridge.finished.connect(self.on_scan_finished)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(BASE_DIR / "app_icon.ico")))
        self.resize(1260, 840)
        self.setMinimumSize(1120, 760)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(self.app_stylesheet())
        self.build_ui()
        self.refresh_all()
        if self.config.get("smart_scan_enabled"):
            self.start_scan_in_background()
        if self.boot_mode and self.config.get("launch_on_boot", True):
            self.hide()
            QApplication.instance().processEvents()
            self.open_boot_dialog()

    def app_stylesheet(self):
        return f"""
        QWidget {{ background: {BG}; color: {TEXT}; font-family: 'Segoe UI Variable', 'Segoe UI', 'Microsoft YaHei UI'; font-size: 10pt; }}
        QLabel#heroTitle {{ font-size: 22pt; font-weight: 600; color: {TEXT}; }}
        QLabel#heroBody, QLabel#sceneSubtitle, QLabel#appPath, QLabel#source, QLabel#statusText, QLabel#sideSubtitle, QLabel#rightMeta {{ color: {SUBTLE}; background: transparent; }}
        QLabel#sectionLabel {{ font-size: 11pt; font-weight: 600; color: {TEXT}; }}
        QLabel#sideTitle {{ font-size: 16pt; font-weight: 600; }}
        QLabel#sideStat {{ font-size: 10.5pt; font-weight: 600; color: {TEXT}; }}
        QLabel#sceneTitle, QLabel#appTitle {{ font-size: 9.5pt; font-weight: 600; }}
        QLabel#sceneIcon {{ font-size: 26pt; }}
        QLabel#sceneSubtitle, QLabel#appPath, QLabel#source {{ font-size: 8.5pt; }}
        QLabel#focusIcon {{ font-size: 36pt; }}
        QLabel#marker {{
            font-size: 7pt;
            font-weight: 700;
            color: white;
            background: {ACCENT};
            border: none;
            border-radius: 6px;
            min-width: 18px;
            max-width: 18px;
            min-height: 18px;
            max-height: 18px;
            qproperty-alignment: AlignCenter;
        }}
        QFrame#panel {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; }}
        QFrame#softCard {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; }}
        QFrame#card {{ background: {CARD}; border: 1.5px solid {BORDER}; border-radius: 8px; }}
        QFrame#card:hover {{ border-color: #c4c4c4; background: {CARD_ALT}; }}
        QFrame#card[selected='true'] {{ background: {ACCENT_SOFT}; border: 1.5px solid {ACCENT}; }}
        QWidget#scrollHost, QScrollArea#appsScroll, QWidget#sceneHost {{ background: transparent; }}
        QPushButton {{ background: {CARD_ALT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px; padding: 9px 16px; font-size: 10pt; min-height: 32px; }}
        QPushButton:hover {{ border-color: #c4c4c4; background: {CARD}; }}
        QPushButton:pressed {{ background: #e8e8e8; border-color: #b3b3b3; }}
        QPushButton#primaryButton {{ background: {ACCENT}; color: white; border: none; font-weight: 600; border-radius: 6px; padding: 10px 16px; min-height: 36px; }}
        QPushButton#primaryButton:hover {{ background: {ACCENT_HOVER}; }}
        QPushButton#primaryButton:pressed {{ background: #004c8c; }}
        QPushButton#actionCard {{ background: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px; font-size: 9pt; }}
        QPushButton#actionCard:hover {{ border-color: #c4c4c4; background: {CARD_ALT}; }}
        QPushButton#actionCard:pressed {{ background: #e8e8e8; border-color: #b3b3b3; }}
        QCheckBox {{ color: {TEXT}; spacing: 8px; }}
        QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; }}
        QCheckBox::indicator:unchecked {{ border: 1.5px solid #8a8a8a; background: {CARD}; }}
        QCheckBox::indicator:checked {{ border: 1.5px solid {ACCENT}; background: {ACCENT}; }}
        QCheckBox::indicator:unchecked:hover {{ border-color: #6a6a6a; }}
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ background: transparent; width: 6px; margin: 4px 0; border-radius: 3px; }}
        QScrollBar::handle:vertical {{ background: #c4c4c4; min-height: 30px; border-radius: 3px; }}
        QScrollBar::handle:vertical:hover {{ background: #a0a0a0; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; height: 0px; }}
        QScrollBar:horizontal {{ background: transparent; height: 6px; margin: 0; border-radius: 3px; }}
        QScrollBar::handle:horizontal {{ background: #c4c4c4; min-width: 30px; border-radius: 3px; }}
        QScrollBar::handle:horizontal:hover {{ background: #a0a0a0; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal, QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; width: 0px; }}
        QLineEdit {{ background: {CARD}; border: 1.5px solid {BORDER}; border-radius: 6px; padding: 9px 12px; font-size: 10pt; }}
        QLineEdit:focus {{ border-color: {ACCENT}; }}
        QWidget#windowFrame {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
        QWidget#titleDragArea {{ background: transparent; }}
        QLabel#appIcon {{ font-size: 22pt; background: transparent; }}
        QPushButton#titleBtn {{ background: transparent; color: {TEXT}; border: none; border-radius: 4px; font-size: 12pt; padding: 0; }}
        QPushButton#titleBtn:hover {{ background: rgba(0,0,0,0.05); }}
        QPushButton#titleBtn:pressed {{ background: rgba(0,0,0,0.08); }}
        QPushButton#titleCloseBtn {{ background: transparent; color: {TEXT}; border: none; border-radius: 4px; font-size: 12pt; padding: 0; }}
        QPushButton#titleCloseBtn:hover {{ background: #c42b1c; color: white; }}
        QPushButton#titleCloseBtn:pressed {{ background: #b22a1a; color: white; }}
        QWidget#contentWrapper {{ background: transparent; }}
        """

    def scene_names(self):
        return list(self.config["scenes"].keys())

    def current_scene(self):
        return self.config["scenes"][self.current_scene_name]

    def build_ui(self):
        central = QWidget()
        central.setObjectName("windowFrame")
        self.setCentralWidget(central)
        shell = QVBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        content_wrapper = QWidget()
        content_wrapper.setObjectName("contentWrapper")
        content_shell = QVBoxLayout(content_wrapper)
        content_shell.setContentsMargins(18, 14, 18, 18)
        content_shell.setSpacing(14)
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_title_col = QVBoxLayout()
        header_title_col.setSpacing(2)
        self._drag_widget = QWidget()
        self._drag_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._drag_widget.setObjectName("titleDragArea")
        app_icon_label = QLabel("🪟")
        app_icon_label.setObjectName("appIcon")
        app_icon_label.setAlignment(Qt.AlignCenter)
        app_icon_label.setFixedSize(36, 36)
        title = QLabel("Windows 情景模式")
        title.setObjectName("heroTitle")
        header_title_col.addWidget(title)
        header_title_col.addStretch(1)
        header_row.addWidget(app_icon_label)
        header_row.addLayout(header_title_col)
        header_row.addWidget(self._drag_widget, 1)
        btn_size = 46
        for text, obj_name, handler in (("─", "titleBtn", self.showMinimized), ("⬜", "titleBtn", self.toggle_maximize), ("✕", "titleCloseBtn", self.close)):
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
            btn.setFixedSize(btn_size, 32)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(handler)
            header_row.addWidget(btn)
        self._drag_pos = None
        self._drag_widget.mousePressEvent = self._title_mouse_press
        self._drag_widget.mouseMoveEvent = self._title_mouse_move
        self._drag_widget.mouseReleaseEvent = self._title_mouse_release
        content_shell.addLayout(header_row)
        body = QLabel("选择一个情景，快速启动你需要的一组应用。")
        body.setObjectName("heroBody")
        content_shell.addWidget(body)
        content = QHBoxLayout()
        content.setSpacing(14)
        content_shell.addLayout(content, 1)
        left_panel = self.create_panel()
        right_panel = self.create_panel()
        content.addWidget(left_panel, 1)
        right_panel.setFixedWidth(340)
        content.addWidget(right_panel)
        left_layout = left_panel.layout()
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(12)

        scene_surface = self.create_soft_card()
        scene_surface.layout().setContentsMargins(12, 10, 12, 10)
        scene_surface.layout().setSpacing(12)
        scene_surface.layout().addWidget(self.section_label("情景模式"))
        scene_host = QWidget()
        scene_host.setObjectName("sceneHost")
        scene_host_layout = QVBoxLayout(scene_host)
        scene_host_layout.setContentsMargins(2, 2, 2, 2)
        self.scene_grid = FlowGrid(columns=max(1, len(self.scene_names())))
        scene_host_layout.addWidget(self.scene_grid)
        scene_surface.layout().addWidget(scene_host, 1)
        left_layout.addWidget(scene_surface, 0)

        apps_surface = self.create_soft_card()
        apps_surface.layout().setContentsMargins(12, 12, 12, 12)
        apps_scroll = QScrollArea()
        apps_scroll.setWidgetResizable(True)
        apps_scroll.setFrameShape(QFrame.NoFrame)
        apps_scroll.setObjectName("appsScroll")
        apps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        apps_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        host = QWidget()
        host.setObjectName("scrollHost")
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(2, 2, 2, 2)
        self.apps_grid = FlowGrid(columns=6)
        host_layout.addWidget(self.apps_grid)
        apps_scroll.setWidget(host)
        apps_surface.layout().addWidget(apps_scroll, 1)
        left_layout.addWidget(self.section_label("推荐应用"))
        left_layout.addWidget(apps_surface, 1)

        right_layout = right_panel.layout()
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        focus_card = self.create_soft_card()
        focus_card.layout().setContentsMargins(16, 16, 16, 16)
        focus_card.layout().setSpacing(10)
        focus_card.layout().addWidget(self.section_label("当前模式"))
        focus_row = QHBoxLayout()
        focus_row.setSpacing(12)
        self.focus_icon = QLabel("")
        self.focus_icon.setObjectName("focusIcon")
        self.focus_icon.setAlignment(Qt.AlignCenter)
        self.focus_icon.setFixedSize(56, 56)
        focus_text_col = QVBoxLayout()
        focus_text_col.setSpacing(4)
        self.side_title = QLabel("")
        self.side_title.setObjectName("sideTitle")
        self.side_subtitle = QLabel("")
        self.side_subtitle.setObjectName("sideSubtitle")
        self.side_subtitle.setWordWrap(True)
        focus_text_col.addWidget(self.side_title)
        focus_text_col.addWidget(self.side_subtitle)
        focus_row.addWidget(self.focus_icon)
        focus_row.addLayout(focus_text_col, 1)
        focus_card.layout().addLayout(focus_row)
        right_layout.addWidget(focus_card)

        metrics_card = self.create_soft_card()
        metrics_card.layout().setContentsMargins(16, 16, 16, 16)
        metrics_card.layout().setSpacing(10)
        metrics_card.layout().addWidget(self.section_label("模式信息"))
        self.side_stats = QLabel("")
        self.side_stats.setObjectName("sideStat")
        self.side_stats.setWordWrap(True)
        self.side_meta = QLabel("")
        self.side_meta.setObjectName("rightMeta")
        self.side_meta.setWordWrap(True)
        metrics_card.layout().addWidget(self.side_stats)
        metrics_card.layout().addWidget(self.side_meta)
        right_layout.addWidget(metrics_card)

        action_card = self.create_soft_card()
        action_card.layout().setContentsMargins(16, 16, 16, 16)
        action_card.layout().setSpacing(10)
        action_card.layout().addWidget(self.section_label("快捷操作"))
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        for icon, text, handler in (("▶", "一键启动", self.launch_selected_scene), ("🔄", "刷新推荐", self.refresh_recommendations), ("⚙", "情景配置", self.open_config_window)):
            btn = QPushButton(f"{icon}\n{text}")
            btn.setObjectName("actionCard")
            btn.setFixedSize(80, 80)
            btn.clicked.connect(handler)
            actions_row.addWidget(btn)
        actions_row.addStretch(1)
        action_card.layout().addLayout(actions_row)
        right_layout.addWidget(action_card)

        settings = self.create_soft_card()
        settings.layout().setContentsMargins(16, 16, 16, 16)
        settings_layout = settings.layout()
        settings_layout.setSpacing(10)
        settings_layout.addWidget(self.section_label("系统设置"))
        self.autostart_checkbox = QCheckBox("开机自动启动本程序")
        self.smart_scan_checkbox = QCheckBox("启动时自动智能识别应用")
        self.launch_on_boot_checkbox = QCheckBox("开机后自动弹出情景窗口")
        for checkbox in (self.autostart_checkbox, self.smart_scan_checkbox, self.launch_on_boot_checkbox):
            checkbox.stateChanged.connect(self.save_system_settings)
            settings_layout.addWidget(checkbox)
        right_layout.addWidget(settings)

        status_card = self.create_soft_card()
        status_card.layout().setContentsMargins(16, 16, 16, 16)
        status_card.layout().setSpacing(8)
        status_card.layout().addWidget(self.section_label("状态"))
        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)
        status_card.layout().addWidget(self.status_label)
        right_layout.addWidget(status_card)
        right_layout.addStretch(1)
        shell.addWidget(content_wrapper, 1)

    def _title_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _title_mouse_move(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _title_mouse_release(self, _event):
        self._drag_pos = None

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def create_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        return panel

    def create_soft_card(self):
        card = QFrame()
        card.setObjectName("softCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        return card

    def empty_card(self, title_text, subtitle_text):
        card = self.create_soft_card()
        title = QLabel(title_text)
        title.setObjectName("appTitle")
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("appPath")
        subtitle.setWordWrap(True)
        card.layout().addWidget(title)
        card.layout().addWidget(subtitle)
        return card

    def section_label(self, text):
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def set_status(self, text):
        self.status_label.setText(text)

    def refresh_all(self):
        self.refresh_scene_cards()
        self.refresh_side_panel()
        self.refresh_recommendations()
        defaults = {"autostart_enabled": False, "smart_scan_enabled": True, "launch_on_boot": True}
        for checkbox, key in ((self.autostart_checkbox, "autostart_enabled"), (self.smart_scan_checkbox, "smart_scan_enabled"), (self.launch_on_boot_checkbox, "launch_on_boot")):
            checkbox.blockSignals(True)
            checkbox.setChecked(self.config.get(key, defaults[key]))
            checkbox.blockSignals(False)

    def select_scene(self, scene_name):
        self.current_scene_name = scene_name
        self.refresh_all()

    def refresh_scene_cards(self):
        cards = []
        self.scene_grid.set_columns(max(1, len(self.scene_names())))
        for scene_name in self.scene_names():
            card = SceneCard(scene_name, selected=scene_name == self.current_scene_name)
            card.clicked.connect(lambda name=scene_name: self.select_scene(name))
            cards.append(card)
        self.scene_grid.set_widgets(cards)

    def refresh_side_panel(self):
        meta = SCENE_META.get(self.current_scene_name, {"subtitle": ""})
        recommendations = recommend_apps_for_scene(self.current_scene_name, self.config, self.scanned_apps)
        self.focus_icon.setText(meta.get("icon", "⬜"))
        self.side_title.setText(f"{self.current_scene_name} 模式")
        self.side_subtitle.setText(meta["subtitle"])
        self.side_stats.setText(
            f"已配置应用 {len(self.current_scene().get('apps', []))} 个\n"
            f"智能推荐 {len(recommendations)} 个\n"
            f"识别关键词 {len(self.current_scene().get('keywords', []))} 个"
        )
        self.side_meta.setText("点击情景卡片切换模式，勾选应用后一键启动。")

    def refresh_recommendations(self):
        recommendations = recommend_apps_for_scene(self.current_scene_name, self.config, self.scanned_apps)
        self.app_cards = {}
        cards = []
        if not recommendations:
            cards.append(self.empty_card("当前没有推荐应用", "先到完整配置窗口里添加应用，或保留智能识别开关。"))
            self.apps_grid.set_widgets(cards)
            self.set_status("当前情景没有推荐应用")
            return
        for app in recommendations:
            card = AppCard(app, selected=app.get("source") == "预设配置")
            card.clicked.connect(lambda current=card: current.set_selected(not current.selected))
            self.app_cards[f"{app['name']}|{app['path']}"] = card
            cards.append(card)
        self.apps_grid.set_widgets(cards)
        self.set_status(f"已加载 {len(recommendations)} 个推荐应用")

    def launch_selected_scene(self):
        selected_apps = [card.app for card in self.app_cards.values() if card.selected]
        if not selected_apps:
            QMessageBox.information(self, APP_NAME, "当前没有勾选任何应用。")
            return
        launched, failed = [], []
        for app in selected_apps:
            try:
                open_target(app["path"])
                launched.append(app["name"])
            except OSError as exc:
                failed.append(f"{app['name']} ({exc})")
        lines = [f"已执行 {self.current_scene_name} 情景"]
        if launched:
            lines.append("已启动：" + "、".join(launched))
        if failed:
            lines.append("启动失败：" + "；".join(failed))
        QMessageBox.information(self, APP_NAME, "\n".join(lines))
        self.set_status(f"情景已执行：{self.current_scene_name}")

    def save_system_settings(self):
        self.config["autostart_enabled"] = self.autostart_checkbox.isChecked()
        self.config["smart_scan_enabled"] = self.smart_scan_checkbox.isChecked()
        self.config["launch_on_boot"] = self.launch_on_boot_checkbox.isChecked()
        save_config(self.config)
        ok, msg = sync_autostart(self.config)
        self.set_status(msg if ok else f"保存失败：{msg}")

    def open_config_window(self):
        ConfigDialog(self).exec()

    def open_quick_launch(self):
        QuickLaunchDialog(self).exec()

    def open_boot_dialog(self):
        if BootDialog(self).exec() == QDialog.Rejected:
            self.close()

    def start_scan_in_background(self):
        def runner():
            self.scanner_bridge.started.emit()
            self.scanner_bridge.finished.emit(scan_for_apps())
        threading.Thread(target=runner, daemon=True).start()

    def on_scan_finished(self, scanned):
        self.scanned_apps = scanned
        self.refresh_all()
        self.set_status(f"智能识别完成，找到 {len(scanned)} 个候选应用")


def main(boot_mode=False):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow(boot_mode=boot_mode)
    if not boot_mode:
        window.show()
    sys.exit(app.exec())
