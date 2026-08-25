import argparse
import atexit
import ctypes
import json
import math
import os
import subprocess
import sys
import tkinter as tk
import winreg
from ctypes import wintypes
from pathlib import Path
from tkinter import messagebox


APP_NAME = "Desktop Fences Lite"
CONFIG_NAME = "desktop_fences_lite_v5_config.json"
CONFIG_VERSION = 5
STARTUP_VALUE_NAME = "Desktop Fences Lite v5"

DEFAULT_POSITIONS = {
    "browser_chat": [18, 18],
    "dev": [970, 300],
    "embedded": [560, 300],
    "ai_office": [18, 320],
    "download_mobile": [18, 600],
    "design": [560, 580],
    "folders": [560, 820],
    "documents": [970, 580],
    "entertainment": [970, 850],
    "learning": [18, 845],
    "unknown": [560, 1090],
}

CATEGORIES = [
    ("browser_chat", "浏览器与通讯", "#2d3238"),
    ("dev", "开发 IDE 与编程", "#4b4642"),
    ("embedded", "嵌入式电子与硬件", "#404647"),
    ("ai_office", "AI 办公与知识管理", "#59483f"),
    ("download_mobile", "下载网盘与手机管理", "#4a3d46"),
    ("design", "设计建模与创作", "#3f4c5a"),
    ("folders", "文件夹", "#3f4540"),
    ("documents", "文档与临时", "#3f4854"),
    ("entertainment", "娱乐游戏", "#4c3f4f"),
    ("learning", "学习教育与行业平台", "#4a4a4a"),
    ("unknown", "待确认", "#4a4a4a"),
]

DEFAULT_CONFIG = {
    "version": CONFIG_VERSION,
    "opacity": 0.91,
    "item_width": 92,
    "item_height": 82,
    "icon_size": 40,
    "margin": 12,
    "gap": 12,
    "hide_native_desktop_icons": True,
    "include_public_desktop": True,
    "auto_refresh_seconds": 5,
    "default_positions": DEFAULT_POSITIONS,
    "custom_positions": DEFAULT_POSITIONS,
    "category_overrides": {},
}

APP_KEYWORDS = {
    "embedded": [
        "axdl", "aicube", "balenaetcher", "ccs ", "code composer", "keil", "uvision",
        "mixly", "串口助手", "取字模", "嘉立创", "arduino", "bh560", "blackhawk",
        "maixvision", "mqttx", "stm32", "st-link", "vofa", "flymcu", "jlink", "j-link",
    ],
    "dev": [
        "cc switch", "cursor", "docker", "hbuilder", "visual studio code", "vscode", "trae",
        "微信开发者工具", "git bash", "git gui", "逗脑", "ide", "pycharm", "intellij",
        "android studio", "win文本编辑器", "notepad++", "modex-mh-agent", "putty", "vncviewer",
        "realvnc", "bitvise", "mobaxterm", "nomachine", "winscp", "xshell", "xftp",
        "wireshark", "vmware", "virtualbox", "openvpn", "clash", "vpn",
    ],
    "design": [
        "blender", "open design", "opendesign", "freecad", "solidworks", "rtx remix",
        "photoshop", "illustrator", "premiere", "audition", "figma", "autocad", "3ds max",
    ],
    "ai_office": [
        "豆包", "doubao", "mrite", "wps", "microsoft office", "xmind", "notion", "obsidian",
        "onenote", "word", "excel", "powerpoint", "有道", "kimi", "deepseek",
    ],
    "browser_chat": [
        "microsoft edge", "chrome", "firefox", "微信", "weixin", "wechat", "腾讯会议",
        "wemeet", "qq", "钉钉", "dingtalk", "zoom", "飞书", "lark", "telegram",
    ],
    "download_mobile": [
        "迅雷", "xunlei", "百度网盘", "baidunetdisk", "百度网盘同步空间", "夸克网盘",
        "quark", "手机助理", "honorsuite", "腾讯应用宝", "应用宝", "爱思助手", "i4tools",
        "115", "onedrive", "坚果云", "阿里云盘",
    ],
    "entertainment": [
        "steam", "epic games", "三角洲行动", "delta force", "无畏契约", "wegame", "哔哩哔哩",
        "bilibili", "网易云音乐", "cloudmusic", "qq音乐", "roblox", "minecraft", "game launcher",
    ],
    "learning": [
        "学习通", "chaoxing", "大国工匠", "greatcraftsman", "craic", "mooc", "雨课堂",
        "智慧树", "华数杯", "数学建模", "裁判软件",
    ],
}

DOCUMENT_EXTENSIONS = {
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".md",
    ".rtf", ".csv", ".chm", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
    ".heic", ".svg", ".ico", ".json", ".xml", ".yaml", ".yml",
}
PACKAGE_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".msi",
}
SKIP_NAMES = {"desktop.ini", "thumbs.db", ".ds_store", "desktop boxes"}


def main() -> int:
    args = parse_args()
    enable_dpi_awareness()
    personal = resolve_personal_desktop(args.desktop)
    desktops = [personal]
    if not args.no_public_desktop:
        public = resolve_public_desktop()
        if public and public.resolve() != personal.resolve():
            desktops.append(public)

    missing = [str(path) for path in desktops if not path.exists()]
    if missing:
        messagebox.showerror(APP_NAME, "Desktop folder was not found:\n" + "\n".join(missing))
        return 1

    config_path = Path(args.config).expanduser() if args.config else script_dir() / CONFIG_NAME
    if args.enable_startup or args.disable_startup:
        try:
            set_startup_enabled(args.enable_startup)
            return 0
        except OSError as exc:
            print(f"Startup configuration failed: {exc}", file=sys.stderr)
            return 1
    config = load_config(config_path)
    if args.reset_layout:
        config["custom_positions"] = dict(config.get("default_positions", DEFAULT_POSITIONS))
        save_config(config_path, config)

    items = scan_desktops(desktops, config.get("category_overrides", {}))
    if args.inventory:
        print_inventory(items, desktops)
        return 0

    app = FenceApp(
        desktops=desktops,
        config=config,
        config_path=config_path,
        attach_desktop=False,
        safe_preview=args.self_test,
    )
    if args.self_test:
        return app.run_self_test()
    app.mainloop()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show categorized desktop fences without moving, renaming, or deleting files."
    )
    parser.add_argument("--desktop", help="Personal desktop folder to scan.")
    parser.add_argument("--config", help="Config JSON path.")
    parser.add_argument("--no-public-desktop", action="store_true", help="Do not scan the public desktop.")
    parser.add_argument("--no-desktop-attach", action="store_true", help="Keep panels as normal windows.")
    parser.add_argument("--reset-layout", action="store_true", help="Discard saved panel positions.")
    parser.add_argument("--inventory", action="store_true", help="Print all detected items and exit.")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--enable-startup", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--disable-startup", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_shell_folder(csidl: int):
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        result = ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
        path = Path(buffer.value)
        return path if result == 0 and path.exists() else None
    except Exception:
        return None


def resolve_personal_desktop(value=None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    shell_path = get_shell_folder(0x0000)
    if shell_path:
        return shell_path.resolve()
    return (Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop").resolve()


def resolve_public_desktop():
    shell_path = get_shell_folder(0x0019)
    if shell_path:
        return shell_path.resolve()
    public = os.environ.get("PUBLIC")
    return (Path(public) / "Desktop").resolve() if public else None


def load_config(path: Path) -> dict:
    loaded = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8-sig") as file:
                loaded = json.load(file)
        except (OSError, ValueError):
            loaded = {}

    config = dict(DEFAULT_CONFIG)
    if loaded.get("version") == CONFIG_VERSION:
        config.update(loaded)
    save_config(path, config)
    return config


def save_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


class DesktopItem:
    def __init__(self, path: Path, category: str, source: str):
        self.path = path
        self.category = category
        self.source = source
        self.name = display_name(path)


def scan_desktops(desktops, overrides=None):
    overrides = overrides or {}
    items = []
    seen = set()
    for source_index, desktop in enumerate(desktops):
        source = "personal" if source_index == 0 else "public"
        try:
            paths = list(desktop.iterdir())
        except OSError:
            continue
        for path in paths:
            if should_skip(path):
                continue
            dedupe_key = path.name.casefold()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            override = overrides.get(path.name.casefold())
            valid_keys = {key for key, _title, _color in CATEGORIES}
            category = override if override in valid_keys else classify(path)
            items.append(DesktopItem(path, category, source))
    order = {key: index for index, (key, _title, _color) in enumerate(CATEGORIES)}
    items.sort(key=lambda item: (order.get(item.category, 999), item.name.casefold()))
    return items


def should_skip(path: Path) -> bool:
    return path.name.casefold() in SKIP_NAMES


def classify(path: Path) -> str:
    name = display_name(path).casefold()
    full_name = path.name.casefold()
    suffix = path.suffix.casefold()

    if path.is_dir():
        return "folders"

    haystack = f"{name} {full_name}"
    for category in (
        "embedded", "dev", "design", "ai_office", "download_mobile",
        "learning", "entertainment", "browser_chat",
    ):
        if any(keyword.casefold() in haystack for keyword in APP_KEYWORDS[category]):
            return category

    if suffix in DOCUMENT_EXTENSIONS:
        return "documents"
    if suffix in PACKAGE_EXTENSIONS or suffix == ".exe":
        return "documents"
    if suffix in {".lnk", ".url", ".appref-ms"}:
        return "unknown"
    return "documents" if suffix else "unknown"


def display_name(path: Path) -> str:
    name = path.name
    for suffix in (".lnk", ".url", ".appref-ms"):
        if name.casefold().endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name.replace(" - 快捷方式", "")


def group_items(items):
    grouped = {key: [] for key, _title, _color in CATEGORIES}
    for item in items:
        grouped.setdefault(item.category, []).append(item)
    return grouped


def print_inventory(items, desktops):
    print("Scanned desktop folders:")
    for desktop in desktops:
        print(f"  {desktop}")
    print(f"Detected items: {len(items)}\n")
    grouped = group_items(items)
    for key, title, _color in CATEGORIES:
        category_items = grouped.get(key, [])
        if not category_items:
            continue
        print(f"[{title}] {len(category_items)}")
        for item in category_items:
            print(f"  {item.name} [{item.source}]")
        print()


class FenceApp:
    def __init__(self, desktops, config, config_path, attach_desktop, safe_preview=False):
        self.desktops = desktops
        self.config = config
        self.config_path = config_path
        self.attach_desktop = attach_desktop
        self.safe_preview = safe_preview
        self.root = tk.Tk()
        self.root.withdraw()
        self.windows = []
        self.images = []
        self.canvases = []
        self.drag_state = None
        self.items_signature = None
        self.closing = False
        self.desktop_listview = find_desktop_listview()
        self.native_icons_hidden = False
        self.original_hide_icons_value = read_hide_icons_setting()
        self.single_instance_mutex = create_single_instance_mutex()
        if not self.single_instance_mutex:
            messagebox.showinfo(APP_NAME, "桌面分区程序已经在运行。")
            self.root.destroy()
            raise SystemExit(0)

        self.root.bind_all("<Escape>", lambda _event: self.close())
        self.root.bind_all("<F5>", lambda _event: self.refresh(force=True))
        self.root.bind_all("<Control-s>", lambda _event: self.save_layout())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        atexit.register(self.restore_native_desktop_icons)

        if not self.safe_preview:
            self.config["hide_native_desktop_icons"] = True
            self.restore_hide_icons_for_startup()
            self.save_layout()
        self.refresh(force=True)
        if not self.safe_preview:
            self.root.after(150, self.hide_native_icons_if_ready)
        self.schedule_auto_refresh()

    def mainloop(self):
        self.root.mainloop()

    def run_self_test(self):
        self.root.update_idletasks()
        left, top, right, bottom = get_work_area(self.root)
        failures = []
        geometries = []
        for window in self.windows:
            geometry = (window.winfo_x(), window.winfo_y(), window.winfo_width(), window.winfo_height())
            geometries.append(geometry)
            x, y, width, height = geometry
            if x < left or y < top or x + width > right or y + height > bottom:
                failures.append(f"panel outside work area: {geometry}")
        item_count = len(self.items_signature or ())
        if item_count != len(self.images):
            failures.append(f"real icons loaded: {len(self.images)}/{item_count}")
        print(f"items={item_count}")
        print(f"panels={len(self.windows)}")
        print(f"real_icons={len(self.images)}")
        print(f"native_desktop_listview={self.desktop_listview}")
        print(f"work_area={left},{top},{right},{bottom}")
        for geometry in geometries:
            print(f"panel={geometry[0]},{geometry[1]},{geometry[2]},{geometry[3]}")
        for failure in failures:
            print(f"FAIL: {failure}")
        self.close()
        return 1 if failures else 0

    def refresh(self, force=False):
        items = scan_desktops(self.desktops, self.config.get("category_overrides", {}))
        signature = tuple((str(item.path), item.category) for item in items)
        if not force and signature == self.items_signature:
            return
        self.items_signature = signature

        # Keep a recoverable state while rebuilding the copied icon layer.
        self.restore_native_desktop_icons()
        for window in self.windows:
            try:
                window.destroy()
            except tk.TclError:
                pass
        self.windows.clear()
        self.images.clear()
        self.canvases.clear()

        grouped = group_items(items)
        categories = [entry for entry in CATEGORIES if grouped.get(entry[0])]
        rects = self.calculate_layout(categories, grouped)
        for category, rect in zip(categories, rects):
            self.create_fence(category, grouped[category[0]], rect)
        if not self.safe_preview:
            self.root.after(120, self.hide_native_icons_if_ready)

    def hide_native_icons_if_ready(self):
        if self.closing or not self.windows:
            return
        if len(self.images) != len(self.items_signature or ()):
            self.restore_native_desktop_icons()
            return
        try:
            if not self.desktop_listview:
                set_hide_icons_setting(True)
            else:
                ctypes.windll.user32.ShowWindow(self.desktop_listview, 0)
            self.native_icons_hidden = True
            self.config["hide_native_desktop_icons"] = True
            self.save_layout()
        except Exception as exc:
            self.abort_without_hiding(
                "无法安全隐藏 Windows 原桌面图标，已关闭分区以避免重复显示。\n\n"
                f"原因：{exc}"
            )

    def abort_without_hiding(self, reason):
        self.restore_native_desktop_icons()
        for window in self.windows:
            try:
                window.destroy()
            except tk.TclError:
                pass
        self.windows.clear()
        self.images.clear()
        if not self.closing:
            messagebox.showerror(APP_NAME, reason)
            self.close()

    def calculate_layout(self, categories, grouped):
        left, top, right, bottom = get_work_area(self.root)
        screen_width = max(800, right - left)
        screen_height = max(600, bottom - top)
        margin = int(self.config.get("margin", 12))
        gap = int(self.config.get("gap", 12))

        columns = 4 if screen_width >= 1450 else 3 if screen_width >= 1050 else 2
        panel_width = (screen_width - margin * 2 - gap * (columns - 1)) // columns
        item_width = max(76, int(self.config.get("item_width", 92)))
        item_height = max(70, int(self.config.get("item_height", 82)))
        item_columns = max(2, (panel_width - 22) // item_width)
        max_panel_height = max(250, min(370, int(screen_height * 0.36)))

        column_bottoms = [top + margin] * columns
        rects = []
        custom = self.config.get("custom_positions", {})
        for key, _title, _color in categories:
            count = len(grouped[key])
            rows = max(1, math.ceil(count / item_columns))
            height = min(max_panel_height, 42 + rows * item_height + 12)
            height = max(138, height)
            if key in custom:
                x, y = custom[key]
                x = max(left, min(int(x), right - panel_width))
                y = max(top, min(int(y), bottom - height))
                column = min(range(columns), key=lambda idx: abs((left + margin + idx * (panel_width + gap)) - x))
                column_bottoms[column] = max(column_bottoms[column], y + height + gap)
            else:
                column = min(range(columns), key=lambda idx: column_bottoms[idx])
                x = left + margin + column * (panel_width + gap)
                y = column_bottoms[column]
                if y + height > bottom - margin:
                    height = max(138, bottom - margin - y)
                column_bottoms[column] = y + height + gap
            rects.append((x, y, panel_width, height))
        return rects

    def create_fence(self, category, items, rect):
        key, title, color = category
        x, y, width, height = rect
        opacity = min(1.0, max(0.55, float(self.config.get("opacity", 0.91))))

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.configure(bg=color)
        win.attributes("-alpha", opacity)
        win.attributes("-topmost", False)
        set_tool_window_style(win)

        outer = tk.Frame(win, bg=color, highlightthickness=1, highlightbackground="#7d858b")
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg=color, height=34, cursor="fleur")
        header.pack(fill="x")
        header.pack_propagate(False)
        label = tk.Label(
            header,
            text=f"{title}  {len(items)}",
            bg=color,
            fg="#f3f5f7",
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="center",
        )
        label.pack(fill="both", expand=True, padx=32)

        for widget in (header, label):
            widget.bind("<ButtonPress-1>", lambda event, w=win, k=key: self.start_drag(event, w, k))
            widget.bind("<B1-Motion>", lambda event, w=win, k=key: self.drag(event, w, k))
            widget.bind("<ButtonRelease-1>", lambda _event: self.stop_drag())
            widget.bind("<Button-3>", lambda event: self.show_menu(event))

        content = tk.Frame(outer, bg=color)
        content.pack(fill="both", expand=True, padx=(8, 3), pady=(0, 7))
        canvas = tk.Canvas(content, bg=color, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(content, orient="vertical", command=canvas.yview, width=11)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=color)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>", lambda event, c=canvas, item_id=body_id: c.itemconfigure(item_id, width=event.width))
        body.bind("<Configure>", lambda _event, c=canvas, s=scrollbar: self.update_scroll(c, s))
        self.populate_items(body, items, color, width - 25)
        self.bind_mousewheel(canvas, body)

        self.windows.append(win)
        self.canvases.append(canvas)

    def populate_items(self, parent, items, color, available_width):
        item_width = max(76, int(self.config.get("item_width", 92)))
        item_height = max(70, int(self.config.get("item_height", 82)))
        icon_size = max(28, min(56, int(self.config.get("icon_size", 40))))
        columns = max(2, available_width // item_width)

        for column in range(columns):
            parent.grid_columnconfigure(column, weight=1, minsize=item_width)

        for index, item in enumerate(items):
            row, column = divmod(index, columns)
            tile = tk.Frame(parent, width=item_width, height=item_height, bg=color, cursor="hand2")
            tile.grid(row=row, column=column, padx=2, pady=3, sticky="n")
            tile.grid_propagate(False)

            image = load_shell_icon(item.path, color, icon_size, self.root)
            icon = tk.Label(tile, image=image, bg=color, cursor="hand2") if image else tk.Label(
                tile, text=fallback_symbol(item.category), bg=color, fg="#ffffff",
                font=("Segoe UI", 11, "bold"), cursor="hand2",
            )
            if image:
                self.images.append(image)
            icon.pack(pady=(1, 0))

            label = tk.Label(
                tile,
                text=short_name(item.name),
                bg=color,
                fg="#f0f2f3",
                font=("Microsoft YaHei UI", 8),
                wraplength=item_width - 6,
                justify="center",
                cursor="hand2",
            )
            label.pack(fill="both", expand=True, padx=1)
            for widget in (tile, icon, label):
                widget.bind("<Double-Button-1>", lambda _event, path=item.path: open_path(path))
                widget.bind("<Button-3>", lambda event, desktop_item=item: self.show_item_menu(event, desktop_item))

    def update_scroll(self, canvas, scrollbar):
        canvas.configure(scrollregion=canvas.bbox("all"))
        bbox = canvas.bbox("all")
        if bbox and bbox[3] > canvas.winfo_height() + 2:
            if not scrollbar.winfo_ismapped():
                scrollbar.pack(side="right", fill="y")
        elif scrollbar.winfo_ismapped():
            scrollbar.pack_forget()

    def bind_mousewheel(self, canvas, body):
        def scroll(event):
            delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta, "units")
            return "break"

        def bind_tree(widget):
            widget.bind("<MouseWheel>", scroll)
            for child in widget.winfo_children():
                bind_tree(child)

        canvas.bind("<MouseWheel>", scroll)
        bind_tree(body)

    def start_drag(self, event, window, key):
        self.drag_state = {
            "window": window,
            "key": key,
            "offset_x": event.x_root - window.winfo_x(),
            "offset_y": event.y_root - window.winfo_y(),
        }

    def drag(self, event, window, key):
        if not self.drag_state or self.drag_state["key"] != key:
            return
        left, top, right, bottom = get_work_area(self.root)
        x = max(left, min(event.x_root - self.drag_state["offset_x"], right - window.winfo_width()))
        y = max(top, min(event.y_root - self.drag_state["offset_y"], bottom - window.winfo_height()))
        window.geometry(f"+{x}+{y}")
        self.config.setdefault("custom_positions", {})[key] = [x, y]

    def stop_drag(self):
        if self.drag_state:
            self.save_layout()
        self.drag_state = None

    def show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=False, font=("Microsoft YaHei UI", 9))
        menu.add_command(label="刷新全部桌面项目", command=lambda: self.refresh(force=True))
        menu.add_command(label="恢复自动排版", command=self.reset_layout)
        menu.add_command(label="将当前布局设为默认", command=self.make_current_layout_default)
        if is_startup_enabled():
            menu.add_command(label="关闭开机自动启动", command=lambda: self.set_startup(False))
        else:
            menu.add_command(label="开启开机自动启动", command=lambda: self.set_startup(True))
        menu.add_separator()
        menu.add_command(label="退出", command=self.close)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def show_item_menu(self, event, item):
        menu = tk.Menu(self.root, tearoff=False, font=("Microsoft YaHei UI", 9))
        menu.add_command(label="打开", command=lambda: open_path(item.path))
        category_menu = tk.Menu(menu, tearoff=False, font=("Microsoft YaHei UI", 9))
        for key, title, _color in CATEGORIES:
            category_menu.add_command(
                label=title,
                command=lambda category=key, desktop_item=item: self.set_item_category(desktop_item, category),
            )
        menu.add_cascade(label="移动到分类（不移动文件）", menu=category_menu)
        menu.add_command(label="恢复自动分类", command=lambda: self.clear_item_category(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def set_item_category(self, item, category):
        self.config.setdefault("category_overrides", {})[item.path.name.casefold()] = category
        self.save_layout()
        self.refresh(force=True)

    def clear_item_category(self, item):
        self.config.setdefault("category_overrides", {}).pop(item.path.name.casefold(), None)
        self.save_layout()
        self.refresh(force=True)

    def reset_layout(self):
        self.config["custom_positions"] = dict(self.config.get("default_positions", DEFAULT_POSITIONS))
        self.save_layout()
        self.refresh(force=True)

    def make_current_layout_default(self):
        self.config["default_positions"] = dict(self.config.get("custom_positions", {}))
        self.save_layout()
        messagebox.showinfo(APP_NAME, "当前分区位置已设为默认布局。")

    def set_startup(self, enabled):
        try:
            set_startup_enabled(enabled)
            messagebox.showinfo(APP_NAME, "已开启开机自动启动。" if enabled else "已关闭开机自动启动。")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"修改开机启动失败：\n{exc}")

    def set_native_desktop_icons(self, visible):
        if not self.desktop_listview:
            self.desktop_listview = find_desktop_listview()
        if self.desktop_listview:
            ctypes.windll.user32.ShowWindow(self.desktop_listview, 5 if visible else 0)
            self.native_icons_hidden = not visible
        self.config["hide_native_desktop_icons"] = not visible
        self.save_layout()

    def restore_native_desktop_icons(self):
        if self.native_icons_hidden:
            try:
                if self.desktop_listview:
                    ctypes.windll.user32.ShowWindow(self.desktop_listview, 5)
                else:
                    restore_hide_icons_setting(self.original_hide_icons_value)
            except Exception:
                pass
            self.native_icons_hidden = False

    def restore_hide_icons_for_startup(self):
        try:
            if self.desktop_listview:
                ctypes.windll.user32.ShowWindow(self.desktop_listview, 5)
            else:
                set_hide_icons_setting(False)
        except Exception:
            pass

    def schedule_auto_refresh(self):
        seconds = max(2, int(self.config.get("auto_refresh_seconds", 5)))
        self.root.after(seconds * 1000, self.auto_refresh)

    def auto_refresh(self):
        if self.closing:
            return
        self.refresh(force=False)
        self.schedule_auto_refresh()

    def save_layout(self):
        save_config(self.config_path, self.config)

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.restore_native_desktop_icons()
        self.save_layout()
        self.root.destroy()


def short_name(name: str) -> str:
    if len(name) <= 16:
        return name
    return name[:14] + "..."


def fallback_symbol(category: str) -> str:
    return {
        "embedded": "HW", "dev": "DEV", "design": "ART",
        "ai_office": "AI", "browser_chat": "WEB", "download_mobile": "DL",
        "entertainment": "PLAY", "learning": "EDU", "system_tools": "SYS",
        "folders": "DIR", "documents": "DOC", "unknown": "APP",
    }.get(category, "APP")


def open_path(path: Path) -> None:
    try:
        os.startfile(str(path))
    except Exception as exc:
        messagebox.showerror(APP_NAME, f"无法打开：\n{path}\n\n{exc}")


def get_work_area(root):
    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    rect = RECT()
    if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
        return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def enable_dpi_awareness():
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def is_desktop_foreground(panel_handles=None):
    if os.name != "nt":
        return True
    try:
        user32 = ctypes.windll.user32
        foreground = user32.GetForegroundWindow()
        if not foreground:
            return True
        if panel_handles and foreground in panel_handles:
            return True
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(foreground, class_name, len(class_name))
        return class_name.value in {
            "Progman", "WorkerW", "SHELLDLL_DefView", "SysListView32", "Shell_TrayWnd",
            "TrayNotifyWnd", "NotifyIconOverflowWindow",
        }
    except Exception:
        return True


def create_single_instance_mutex():
    if os.name != "nt":
        return True
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel32.CreateMutexW(None, False, "Local\\DesktopFencesLiteV4")
    kernel32.GetLastError.restype = wintypes.DWORD
    if not handle or kernel32.GetLastError() == 183:
        if handle:
            kernel32.CloseHandle(handle)
        return None
    return handle


def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    return f'"{Path(sys.executable).resolve()}" "{Path(__file__).resolve()}"'


def is_startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
        return True
    except OSError:
        return False


def set_startup_enabled(enabled):
    access = winreg.KEY_SET_VALUE
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        access,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            except FileNotFoundError:
                pass


def read_hide_icons_setting():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
        ) as key:
            value, _kind = winreg.QueryValueEx(key, "HideIcons")
            return int(value)
    except OSError:
        return None


def notify_shell_desktop_changed():
    try:
        shell32 = ctypes.windll.shell32
        shell32.SHChangeNotify.argtypes = [wintypes.LONG, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p]
        shell32.SHChangeNotify.restype = None
        shell32.SHChangeNotify(0x08000000, 0x1000, None, None)  # SHCNE_ASSOCCHANGED / SHCNF_IDLIST
    except Exception:
        pass


def set_hide_icons_setting(hidden):
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
    ) as key:
        winreg.SetValueEx(key, "HideIcons", 0, winreg.REG_DWORD, 1 if hidden else 0)
    notify_shell_desktop_changed()


def restore_hide_icons_setting(original):
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
    ) as key:
        if original is None:
            try:
                winreg.DeleteValue(key, "HideIcons")
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(key, "HideIcons", 0, winreg.REG_DWORD, int(original))
    notify_shell_desktop_changed()


def configure_user32():
    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowExW.restype = wintypes.HWND
    user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.SetParent.restype = wintypes.HWND
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                           wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
                                           ctypes.POINTER(wintypes.DWORD)]
    user32.SendMessageTimeoutW.restype = wintypes.LPARAM
    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.EnumChildWindows.argtypes = [wintypes.HWND, ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumChildWindows.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    return user32


def set_tool_window_style(window):
    try:
        window.update_idletasks()
        user32 = configure_user32()
        hwnd = wintypes.HWND(window.winfo_id())
        style = user32.GetWindowLongPtrW(hwnd, -20)
        style |= 0x00000080 | 0x08000000  # WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        style &= ~0x00040000  # WS_EX_APPWINDOW
        user32.SetWindowLongPtrW(hwnd, -20, style)
    except Exception:
        pass


def find_desktop_listview():
    user32 = configure_user32()
    progman = user32.FindWindowW("Progman", None)
    # Windows 10/11 can place the desktop ListView below a WorkerW and at
    # different nesting depths. Ask Explorer to create its worker layer first.
    if progman:
        try:
            user32.SendMessageTimeoutW(
                progman, 0x052C, 0, 0, 0x0000, 1000, ctypes.byref(wintypes.DWORD())
            )
        except Exception:
            pass

    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    matches = []

    def class_name(hwnd):
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value

    @callback_type
    def enum_children(hwnd, _lparam):
        name = class_name(hwnd)
        if name == "SysListView32":
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, len(title))
            if title.value == "FolderView" or user32.IsWindowVisible(hwnd):
                matches.append(hwnd)
                return True
        user32.EnumChildWindows(hwnd, enum_children, 0)
        return True

    @callback_type
    def enum_top(hwnd, _lparam):
        name = class_name(hwnd)
        if name in {"Progman", "WorkerW"}:
            user32.EnumChildWindows(hwnd, enum_children, 0)
        return True

    user32.EnumWindows(enum_top, 0)
    return matches[0] if matches else 0


def attach_window_to_desktop(window):
    try:
        window.update_idletasks()
        user32 = configure_user32()
        hwnd = wintypes.HWND(window.winfo_id())
        progman = user32.FindWindowW("Progman", None)
        if progman:
            user32.SetParent(hwnd, progman)
            set_tool_window_style(window)
            return user32.GetParent(hwnd) == progman
    except Exception:
        pass
    return False


def parse_hex_color(color):
    value = color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def load_shell_icon(path: Path, background: str, size: int, root):
    if os.name != "nt":
        return None
    try:
        class SHFILEINFOW(ctypes.Structure):
            _fields_ = [
                ("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int),
                ("dwAttributes", wintypes.DWORD), ("szDisplayName", wintypes.WCHAR * 260),
                ("szTypeName", wintypes.WCHAR * 80),
            ]

        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        shell32.SHGetFileInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                                           wintypes.UINT, wintypes.UINT]
        shell32.SHGetFileInfoW.restype = ctypes.c_size_t
        user32.GetDC.argtypes = [wintypes.HWND]
        user32.GetDC.restype = wintypes.HDC
        user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        user32.ReleaseDC.restype = ctypes.c_int
        user32.FillRect.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.HBRUSH]
        user32.FillRect.restype = ctypes.c_int
        user32.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON,
                                      ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.HBRUSH,
                                      wintypes.UINT]
        user32.DrawIconEx.restype = wintypes.BOOL
        user32.DestroyIcon.argtypes = [wintypes.HICON]
        user32.DestroyIcon.restype = wintypes.BOOL
        gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
        gdi32.CreateCompatibleDC.restype = wintypes.HDC
        gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                           ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE,
                                           wintypes.DWORD]
        gdi32.CreateDIBSection.restype = wintypes.HBITMAP
        gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        gdi32.SelectObject.restype = wintypes.HGDIOBJ
        gdi32.CreateSolidBrush.argtypes = [wintypes.DWORD]
        gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
        gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        gdi32.DeleteObject.restype = wintypes.BOOL
        gdi32.DeleteDC.argtypes = [wintypes.HDC]
        gdi32.DeleteDC.restype = wintypes.BOOL
        info = SHFILEINFOW()
        flags = 0x000000100 | 0x000000000
        if not shell32.SHGetFileInfoW(str(path), 0, ctypes.byref(info), ctypes.sizeof(info), flags):
            return None

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = size
        bmi.bmiHeader.biHeight = -size
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        screen_dc = user32.GetDC(0)
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        bits = ctypes.c_void_p()
        bitmap = gdi32.CreateDIBSection(memory_dc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
        red, green, blue = parse_hex_color(background)
        brush = gdi32.CreateSolidBrush(red | (green << 8) | (blue << 16))

        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                        ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

        rect = RECT(0, 0, size, size)
        user32.FillRect(memory_dc, ctypes.byref(rect), brush)
        user32.DrawIconEx(memory_dc, 0, 0, info.hIcon, size, size, 0, None, 0x0003)
        raw = ctypes.string_at(bits, size * size * 4)
        rgb = bytearray(size * size * 3)
        for pixel in range(size * size):
            source = pixel * 4
            target = pixel * 3
            rgb[target:target + 3] = raw[source + 2:source + 3] + raw[source + 1:source + 2] + raw[source:source + 1]
        ppm = f"P6\n{size} {size}\n255\n".encode("ascii") + bytes(rgb)
        image = tk.PhotoImage(master=root, data=ppm, format="PPM")

        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteObject(brush)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(0, screen_dc)
        user32.DestroyIcon(info.hIcon)
        return image
    except Exception as exc:
        if os.environ.get("DESKTOP_FENCES_DEBUG"):
            print(f"Icon load failed for {path}: {exc}", file=sys.stderr)
        return None


if __name__ == "__main__":
    raise SystemExit(main())
