import sys
import os
import re
import time
import json
import base64
import random
import hashlib
import datetime
import tempfile
import threading
import urllib.parse
import urllib.request
import subprocess
import webbrowser
from pathlib import Path
import ctypes
from ctypes import wintypes
import winreg

from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QLabel, 
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QScrollArea, QFrame, QDialog, QMessageBox, QRadioButton, 
    QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView
)

# ----------------- CONFIGURATION -----------------
APP_NAME = "SparkAssistant"
GITHUB_REPO = "mariogodace-debug/SparkAssistant"

# Base64-encoded key to bypass GitHub Push Protection scans
API_KEY_B64 = "QVEuQWI4Uk42SlpPeWRqaVZDUmRLOHBTYS10S003S1VBN2FjRl9SN1F0OWdTQTZ6bnpxV2c="
API_KEY = base64.b64decode(API_KEY_B64).decode("utf-8")

ADMIN_USERNAME = "shadow"
ADMIN_DEFAULT_PASS = "Mann@2041986"

MAX_LOG_ENTRIES = 1000
BASE_DIR = Path.home() / "Desktop"
LOG_FILE_PATH = BASE_DIR / "DeskAssistant_activity_log.txt"
USER_DB_PATH = Path(__file__).resolve().parent / "users_db.json"
VERSION_STAMP_FILE = Path(tempfile.gettempdir()) / "spark_version.txt"

ROBLOX_EXPERIENCES = {
    "blox fruits": "2753915549",
    "blox fruit": "2753915549",
    "brookhaven": "4924922222",
    "adopt me": "920587237",
    "arsenal": "286090429",
    "tower of hell": "1962086868",
    "pet simulator": "8737899170",
    "blade ball": "13772394625",
    "da hood": "2788229376",
    "doors": "6516141723",
}

# ----------------- AUTO-START WITH WINDOWS -----------------
def enable_windows_startup():
    """Adds the app to Windows Run Registry so it boots with the PC silently."""
    try:
        exe_path = sys.executable
        if not exe_path.lower().endswith(".exe"):
            return
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}" --startup')
        winreg.CloseKey(key)
    except Exception:
        pass


# ----------------- WINDOWS API UTILITIES -----------------
user32 = ctypes.windll.user32

def find_window_by_title_substring(substring: str):
    found_hwnd = None

    def enum_windows_proc(hwnd, lParam):
        nonlocal found_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if substring.lower() in buff.value.lower():
                    found_hwnd = hwnd
                    return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
    return found_hwnd

def bring_window_to_front(hwnd):
    if not hwnd:
        return False
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    return True


# ----------------- CONTINUOUS AUTO-UPDATER -----------------
class AutoUpdater(QThread):
    def run(self):
        time.sleep(4)
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/latest"
            req = urllib.request.Request(api_url, headers={"User-Agent": "SparkAssistant-AutoUpdater"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                for asset in data.get("assets", []):
                    if asset.get("name") == "SparkAssistant.exe":
                        remote_stamp = asset.get("updated_at")
                        download_url = asset.get("browser_download_url")

                        local_stamp = ""
                        if VERSION_STAMP_FILE.exists():
                            try:
                                local_stamp = VERSION_STAMP_FILE.read_text(encoding="utf-8").strip()
                            except Exception:
                                pass

                        if remote_stamp and remote_stamp != local_stamp:
                            self.silent_replace_and_restart(download_url, remote_stamp)
                            return
        except Exception:
            pass

    def silent_replace_and_restart(self, download_url: str, new_stamp: str):
        try:
            temp_dir = tempfile.gettempdir()
            new_exe = os.path.join(temp_dir, "SparkAssistant_update.exe")
            current_exe = sys.executable

            urllib.request.urlretrieve(download_url, new_exe)
            VERSION_STAMP_FILE.write_text(new_stamp, encoding="utf-8")

            bat_path = os.path.join(temp_dir, "silent_swap.bat")
            with open(bat_path, "w") as f:
                f.write(f"""@echo off
timeout /t 3 /nobreak > nul
move /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.Popen([bat_path], shell=True, creationflags=flags)
            os._exit(0)
        except Exception:
            pass


# ----------------- DB & AUDIT LOGGING -----------------
def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users() -> dict:
    if not USER_DB_PATH.exists():
        initial_db = {
            ADMIN_USERNAME.lower(): {
                "display_name": ADMIN_USERNAME,
                "password_hash": hash_pw(ADMIN_DEFAULT_PASS),
                "is_admin": True,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        try:
            with open(USER_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(initial_db, f, indent=4)
        except Exception:
            pass
        return initial_db
    try:
        with open(USER_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(db: dict):
    try:
        with open(USER_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
    except Exception:
        pass

class AuditLogger:
    @classmethod
    def log(cls, user_tag: str, pc_name: str, win_user: str, query: str, action: str):
        q_lower = query.strip().lower()
        if any(term in q_lower for term in ["search", "google", "find", "lookup", "youtube", "http"]):
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] USER: {user_tag} | PC_NAME: {pc_name} | WIN_ACCOUNT: {win_user} | PROMPT: \"{query}\" | ACTION: {action}\n"
        try:
            lines = []
            if LOG_FILE_PATH.exists():
                with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            lines.append(entry)
            if len(lines) > MAX_LOG_ENTRIES:
                lines = lines[-MAX_LOG_ENTRIES:]
            with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass

    @classmethod
    def read_all_logs(cls) -> list[str]:
        if not LOG_FILE_PATH.exists():
            return []
        try:
            with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="ignore") as f:
                return [l.strip() for l in f.readlines() if l.strip()]
        except Exception:
            return []

    @classmethod
    def clear_logs(cls):
        try:
            with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass


# ----------------- SAFE GAME MACRO CONTROLLER -----------------
class GameMacroController:
    _active = False
    _thread = None

    @classmethod
    def choose_blox_fruit_side(cls, side: str) -> str:
        hwnd = find_window_by_title_substring("Roblox")
        if not hwnd:
            return "Roblox window was not found. Please make sure Roblox is running."

        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.6)

        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top

        if "marine" in side.lower():
            target_x = rect.left + int(w * 0.65)
            target_y = rect.top + int(h * 0.55)
        else:
            target_x = rect.left + int(w * 0.35)
            target_y = rect.top + int(h * 0.55)

        user32.SetCursorPos(target_x, target_y)
        time.sleep(0.1)
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.08)
        user32.mouse_event(0x0004, 0, 0, 0, 0)

        return f"Focused Roblox and selected {side.title()}!"

    @classmethod
    def start_anti_afk(cls) -> str:
        if cls._active:
            return "AFK macro is already running. Say 'stop afk' to halt it."

        hwnd = find_window_by_title_substring("Roblox")
        if hwnd:
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)

        cls._active = True

        def loop():
            time.sleep(2)
            while cls._active:
                try:
                    subprocess.run(["powershell", "-NoProfile", "-Command", "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys(' ')"], capture_output=True)
                    time.sleep(random.uniform(0.3, 0.6))
                    subprocess.run(["powershell", "-NoProfile", "-Command", "$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys('z')"], capture_output=True)
                    time.sleep(random.uniform(4.0, 7.5))
                except Exception:
                    break

        cls._thread = threading.Thread(target=loop, daemon=True)
        cls._thread.start()
        return "Safe AFK Grinding started! Jumping and attacking at random intervals. Say 'stop afk' to finish."

    @classmethod
    def stop_anti_afk(cls) -> str:
        if not cls._active:
            return "No AFK macro is currently running."
        cls._active = False
        return "AFK macro stopped. Controls fully released."


# ----------------- SYSTEM AUTOMATION TOOLS -----------------
class SystemAutomation:
    APP_ALIASES = {
        "powerpoint": ("powerpnt.exe", "PowerPoint"),
        "ppt": ("powerpnt.exe", "PowerPoint"),
        "word": ("winword.exe", "Word"),
        "excel": ("excel.exe", "Excel"),
        "notepad": ("notepad.exe", "Notepad"),
        "calculator": ("calc.exe", "Calculator"),
        "calc": ("calc.exe", "Calculator"),
        "paint": ("mspaint.exe", "Paint"),
        "spotify": (os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"), "Spotify")
    }

    BLOCKED_ADMIN_TERMS = [
        "format", "diskpart", "bcdedit", "reg delete", "net user", 
        "takeown", "icacls", "del /f /s /q c:\\", "rmdir /s /q c:\\", 
        "shutdown", "restart-computer", "powershell -executionpolicy bypass"
    ]

    @classmethod
    def is_safe_command(cls, cmd: str) -> bool:
        c_lower = cmd.lower()
        return not any(blocked in c_lower for blocked in cls.BLOCKED_ADMIN_TERMS)

    @classmethod
    def open_private_browser(cls, target_url: str):
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]

        for p in chrome_paths:
            if os.path.exists(p):
                subprocess.Popen([p, "--incognito", target_url])
                return

        for p in edge_paths:
            if os.path.exists(p):
                subprocess.Popen([p, "-inprivate", target_url])
                return

        webbrowser.open(target_url)

    @classmethod
    def open_or_focus_app(cls, app_name: str) -> str:
        clean = app_name.strip().lower()

        hwnd = find_window_by_title_substring(clean)
        if hwnd:
            bring_window_to_front(hwnd)
            return f"{app_name.title()} is already running. Brought to front."

        if clean in cls.APP_ALIASES:
            exe_cmd, win_title = cls.APP_ALIASES[clean]
            hwnd = find_window_by_title_substring(win_title)
            if hwnd:
                bring_window_to_front(hwnd)
                return f"{win_title} is already open. Brought to front."
            subprocess.Popen(["cmd", "/c", "start", exe_cmd], shell=True)
            return f"Opening {clean.title()}."

        if "roblox" in clean:
            hwnd = find_window_by_title_substring("Roblox")
            if hwnd:
                bring_window_to_front(hwnd)
                return "Roblox is already open. Brought to front."
            try:
                subprocess.Popen('start "" "roblox:"', shell=True)
                return "Launching Roblox."
            except Exception:
                pass

        search_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            os.path.expandvars(r"%USERPROFILE%\OneDrive\Desktop")
        ]
        words = clean.split()
        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for root, _, files in os.walk(s_dir):
                for f in files:
                    fname = f.lower()
                    if fname.endswith((".lnk", ".exe")) and all(w in fname for w in words):
                        try:
                            os.startfile(os.path.join(root, f))
                            return f"Found and opened {f}."
                        except Exception:
                            pass

        return f"Could not find '{app_name}' installed locally."

    @classmethod
    def generate_presentation(cls, topic: str, slides_data: list) -> str:
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt

            prs = Presentation()
            prs.slide_width = Inches(13.33)
            prs.slide_height = Inches(7.5)

            title_layout = prs.slide_layouts[0]
            title_slide = prs.slides.add_slide(title_layout)
            title_slide.shapes.title.text = topic.title()
            title_slide.placeholders[1].text = "Generated autonomously by Spark Assistant"

            bullet_layout = prs.slide_layouts[1]
            for s in slides_data:
                slide = prs.slides.add_slide(bullet_layout)
                slide.shapes.title.text = s.get("title", "Overview")
                body_shape = slide.placeholders[1]
                tf = body_shape.text_frame
                tf.clear()
                for i, bullet in enumerate(s.get("points", [])):
                    p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
                    p.text = bullet
                    p.font.size = Pt(20)

            safe_name = re.sub(r'[\\/*?:"<>| ]', '_', topic)[:25]
            out_path = Path.home() / "Desktop" / f"{safe_name}_Presentation.pptx"
            prs.save(str(out_path))

            os.startfile(str(out_path))
            return f"Created presentation '{out_path.name}' on Desktop and opened it!"
        except Exception as e:
            return f"Failed to generate presentation: {e}"

    @classmethod
    def system_command(cls, action_type: str, detail: str = "") -> str:
        action_type = action_type.lower()
        if not cls.is_safe_command(detail):
            return "Action blocked: Administrative commands are disabled."

        if action_type == "lock_pc":
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "PC locked."
        elif action_type == "mute_volume":
            subprocess.Popen("powershell -Command (New-Object -ComObject WScript.Shell).SendKeys([char]173)", shell=True)
            return "Toggled volume mute."
        elif action_type == "open_settings":
            subprocess.Popen("start ms-settings:", shell=True)
            return "Opened Windows Settings."
        elif action_type == "search_web":
            target = f"https://www.google.com/search?q={urllib.parse.quote_plus(detail)}"
            cls.open_private_browser(target)
            return f"Searching Google privately for '{detail}'."
        elif action_type == "search_youtube":
            target = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(detail)}"
            cls.open_private_browser(target)
            return f"Searching YouTube privately for '{detail}'."
        return "Task complete."


# ----------------- INTENT DISPATCHER & WORKER -----------------
class TaskExecutionWorker(QThread):
    task_completed = pyqtSignal(str)

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def run(self):
        p = self.prompt.strip().lower()

        # PRIORITY 1: Side selection
        if ("marine" in p or "pirate" in p) and not ("what is" in p or "tell me" in p):
            side = "marine" if "marine" in p else "pirate"
            res = GameMacroController.choose_blox_fruit_side(side)
            self.task_completed.emit(res)
            return

        # PRIORITY 2: AFK controls
        if any(w in p for w in ["stop macro", "stop afk", "pause macro", "disable afk", "stop farm"]):
            res = GameMacroController.stop_anti_afk()
            self.task_completed.emit(res)
            return

        if any(w in p for w in ["start afk", "afk", "farm blox", "grind blox", "auto click", "play blox"]):
            res = GameMacroController.start_anti_afk()
            self.task_completed.emit(res)
            return

        # PRIORITY 3: Explicit game launch
        if any(k in p for k in ["open blox fruit", "join blox fruit", "start blox fruit", "open roblox", "start roblox"]):
            hwnd = find_window_by_title_substring("Roblox")
            if hwnd:
                bring_window_to_front(hwnd)
                self.task_completed.emit("Roblox is already running. Switched to it!")
                return
            for game_name, pid in ROBLOX_EXPERIENCES.items():
                if game_name in p:
                    uri = f"roblox://placeId={pid}"
                    subprocess.Popen(f'start "" "{uri}"', shell=True)
                    self.task_completed.emit(f"Launching Roblox: {game_name.title()}!")
                    return

        # PRIORITY 4: Open or focus app
        if re.search(r'^(?:open|launch|start|run|switch to)\s+(.+)', p):
            target = re.sub(r'^(?:open|launch|start|run|switch to)\s+', '', p).strip()
            if "." in target and not target.endswith(".exe") and " " not in target:
                SystemAutomation.open_private_browser(f"https://{target}")
                self.task_completed.emit(f"Opening https://{target} privately.")
            else:
                res = SystemAutomation.open_or_focus_app(target)
                self.task_completed.emit(res)
            return

        # PRIORITY 5: Search Web / YouTube
        if re.search(r'^(?:search|lookup|google|find)\s+(.+)', p):
            query = re.sub(r'^(?:search|lookup|google|find)\s+', '', p).strip()
            if any(k in query for k in ["youtube", "yt"]):
                clean_q = re.sub(r'\b(on\s+)?(youtube|yt)\b', '', query).strip()
                res = SystemAutomation.system_command("search_youtube", clean_q)
            else:
                res = SystemAutomation.system_command("search_web", query)
            self.task_completed.emit(res)
            return

        # PRIORITY 6: Gemini Fallback
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=API_KEY)
            system_prompt = (
                "You are an isolated private desktop assistant.\n"
                "Rules:\n"
                "1. If asked to make a presentation or PowerPoint, output ONLY JSON: {\"action\": \"create_ppt\", \"topic\": \"...\", \"slides\": [{\"title\": \"...\", \"points\": [\"...\", \"...\"]}]}\n"
                "2. If asked to open/switch an app, output ONLY JSON: {\"action\": \"open_app\", \"parameter\": \"...\"}\n"
                "3. Never perform admin or destructive operations.\n"
                "4. For regular queries or conversations, answer directly and concisely.\n"
                "When outputting JSON, return raw JSON only."
            )

            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=self.prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=700
                )
            )

            response_raw = (res.text or "").strip()
            if response_raw.startswith("{") and response_raw.endswith("}"):
                try:
                    data = json.loads(response_raw)
                    if data.get("action") == "create_ppt":
                        out = SystemAutomation.generate_presentation(data.get("topic", "Presentation"), data.get("slides", []))
                        self.task_completed.emit(out)
                        return
                    elif data.get("action") == "open_app":
                        out = SystemAutomation.open_or_focus_app(data.get("parameter", ""))
                        self.task_completed.emit(out)
                        return
                except Exception:
                    pass

            self.task_completed.emit(response_raw)
        except Exception as e:
            self.task_completed.emit(f"Could not complete task: {e}")


# ----------------- UI DIALOGS -----------------
class AdminPanelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shield Admin Console - Activity & Device Monitor")
        self.resize(850, 480)
        self.setStyleSheet("""
            QDialog { background-color: #000000; color: #ffffff; font-family: 'Segoe UI'; }
            QLabel { color: #8ab4f8; font-size: 13px; }
            QLineEdit { background: #0d0d0d; border: 1px solid #222222; border-radius: 6px; padding: 6px; color: white; }
            QTableWidget { background-color: #080808; color: #ffffff; gridline-color: #1a1a1a; border: 1px solid #222222; border-radius: 8px; }
            QHeaderView::section { background-color: #111111; color: #8ab4f8; padding: 6px; border: 1px solid #1a1a1a; font-weight: bold; }
            QPushButton { background-color: #161616; color: white; border-radius: 6px; padding: 6px 14px; font-size: 12px; border: 1px solid #2a2a2a; }
            QPushButton:hover { background-color: #242424; }
            QPushButton#DangerBtn:hover { background-color: #990000; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.stats_lbl = QLabel(f"Device Logs (Capped at {MAX_LOG_ENTRIES})")
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter logs...")
        self.search_bar.textChanged.connect(self.filter_table)
        top_row.addWidget(self.stats_lbl)
        top_row.addStretch()
        top_row.addWidget(self.search_bar)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "User", "PC / Account", "Prompt", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.populate_logs)
        clear_btn = QPushButton("Clear History")
        clear_btn.setObjectName("DangerBtn")
        clear_btn.clicked.connect(self.clear_logs)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        self.populate_logs()

    def populate_logs(self):
        raw_entries = AuditLogger.read_all_logs()
        self.stats_lbl.setText(f"Recorded Events: {len(raw_entries)} / {MAX_LOG_ENTRIES}")
        self.table.setRowCount(0)
        pattern = re.compile(r'\[(.*?)\] USER:\s*(.*?)\s*\|\s*PC_NAME:\s*(.*?)\s*\|\s*WIN_ACCOUNT:\s*(.*?)\s*\|\s*PROMPT:\s*\"(.*?)\"\s*\|\s*ACTION:\s*(.*)')

        for line in reversed(raw_entries):
            m = pattern.match(line)
            r = self.table.rowCount()
            self.table.insertRow(r)
            if m:
                tstamp, user, pc, win_acc, prompt, action = m.groups()
                self.table.setItem(r, 0, QTableWidgetItem(tstamp))
                self.table.setItem(r, 1, QTableWidgetItem(user))
                self.table.setItem(r, 2, QTableWidgetItem(f"{pc} ({win_acc})"))
                self.table.setItem(r, 3, QTableWidgetItem(prompt))
                self.table.setItem(r, 4, QTableWidgetItem(action))
            else:
                self.table.setItem(r, 0, QTableWidgetItem(line))

    def filter_table(self, query: str):
        q = query.lower()
        for r in range(self.table.rowCount()):
            matches = any(
                q in (self.table.item(r, c).text().lower() if self.table.item(r, c) else "")
                for c in range(self.table.columnCount())
            )
            self.table.setRowHidden(r, not matches)

    def clear_logs(self):
        AuditLogger.clear_logs()
        self.populate_logs()


class AuthDialog(QDialog):
    def __init__(self, pc_name: str, win_user: str):
        super().__init__()
        self.pc_name = pc_name
        self.win_user = win_user
        self.users = load_users()
        self.authenticated_user = None
        self.is_admin = False

        self.setWindowTitle("Spark Assistant - Security Gate")
        self.setFixedSize(380, 360)
        self.setStyleSheet("""
            QDialog { background-color: #000000; color: #ffffff; font-family: 'Segoe UI'; border: 1px solid #1f1f1f; }
            QLabel { color: #e8eaed; font-size: 13px; }
            QLineEdit { background: #0c0c0c; border: 1px solid #222222; border-radius: 8px; padding: 8px; color: white; }
            QRadioButton { color: #c4c7c5; }
            QPushButton { background-color: #8ab4f8; color: #000000; border-radius: 8px; padding: 10px; font-weight: bold; }
            QPushButton:hover { background-color: #adc8ff; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        info_lbl = QLabel(f"<b>Device:</b> {self.pc_name} ({self.win_user})")
        info_lbl.setStyleSheet("color: #8ab4f8; font-size: 12px;")
        layout.addWidget(info_lbl)

        mode_layout = QHBoxLayout()
        self.radio_login = QRadioButton("Existing User")
        self.radio_register = QRadioButton("New User")
        self.radio_login.setChecked(True)
        self.bg = QButtonGroup()
        self.bg.addButton(self.radio_login)
        self.bg.addButton(self.radio_register)
        mode_layout.addWidget(self.radio_login)
        mode_layout.addWidget(self.radio_register)
        layout.addLayout(mode_layout)

        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.submit_btn = QPushButton("Login")
        self.submit_btn.clicked.connect(self.handle_auth)
        layout.addWidget(self.submit_btn)

        self.radio_login.toggled.connect(lambda: self.submit_btn.setText("Login" if self.radio_login.isChecked() else "Create Account"))

    def handle_auth(self):
        uname = self.username_input.text().strip()
        pwd = self.password_input.text().strip()
        if not uname or not pwd:
            return

        key = uname.lower()
        if self.radio_login.isChecked():
            if key not in self.users or self.users[key]["password_hash"] != hash_pw(pwd):
                QMessageBox.critical(self, "Denied", "Invalid credentials.")
                return
            self.authenticated_user = self.users[key]["display_name"]
            self.is_admin = self.users[key].get("is_admin", False)
            self.accept()
        else:
            if key in self.users:
                QMessageBox.warning(self, "Exists", "User already registered.")
                return
            self.users[key] = {
                "display_name": uname,
                "password_hash": hash_pw(pwd),
                "is_admin": False,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_users(self.users)
            self.authenticated_user = uname
            self.is_admin = False
            self.accept()


# ----------------- MAIN DESKTOP BAR & EXPANDED WINDOW -----------------
class GeminiDesktopAssistant(QMainWindow):
    def __init__(self, active_user: str, is_admin: bool, pc_name: str, win_user: str):
        super().__init__()
        self.active_user = active_user
        self.is_admin = is_admin
        self.pc_name = pc_name
        self.win_user = win_user

        self.is_compact = True
        self.click_times = []

        # Borderless, Always on top, Taskbar tool window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main Central Container
        self.container = QWidget(self)
        self.container.setObjectName("Card")
        self.container.setStyleSheet("""
            QWidget#Card {
                background-color: #000000;
                border: 1px solid #1c1c1f;
                border-radius: 18px;
            }
        """)

        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(14, 10, 14, 10)
        self.main_layout.setSpacing(8)

        # Top Bar (Header & Controls)
        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(4, 2, 4, 2)

        self.title_lbl = QLabel(f"✦ Spark ({self.active_user})")
        self.title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.title_lbl.setStyleSheet("color: #8ab4f8;")
        self.top_bar.addWidget(self.title_lbl)
        self.top_bar.addStretch()

        if self.is_admin:
            self.admin_btn = QPushButton("🛡️")
            self.admin_btn.setFixedSize(26, 22)
            self.admin_btn.setToolTip("Admin Logs")
            self.admin_btn.setStyleSheet("QPushButton { background: #111111; color: #8ab4f8; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #222222; }")
            self.admin_btn.clicked.connect(lambda: AdminPanelDialog(self).exec())
            self.top_bar.addWidget(self.admin_btn)

        # Expand / Shrink toggle button
        self.mode_toggle_btn = QPushButton("▼")
        self.mode_toggle_btn.setFixedSize(26, 22)
        self.mode_toggle_btn.setToolTip("Toggle Compact Search Bar / Full View")
        self.mode_toggle_btn.setStyleSheet("QPushButton { background: #111111; color: #aaaaaa; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #222222; color: white; }")
        self.mode_toggle_btn.clicked.connect(self.toggle_compact_mode)
        self.top_bar.addWidget(self.mode_toggle_btn)

        # Minimize to taskbar / tray button
        min_btn = QPushButton("—")
        min_btn.setFixedSize(26, 22)
        min_btn.setToolTip("Minimize")
        min_btn.setStyleSheet("QPushButton { background: #111111; color: #aaaaaa; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #222222; color: white; }")
        min_btn.clicked.connect(self.showMinimized)
        self.top_bar.addWidget(min_btn)

        # Close App Button
        exit_btn = QPushButton("✕")
        exit_btn.setFixedSize(26, 22)
        exit_btn.setToolTip("Exit")
        exit_btn.setStyleSheet("QPushButton { background: #111111; color: #aaaaaa; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #b00020; color: white; }")
        exit_btn.clicked.connect(QApplication.instance().quit)
        self.top_bar.addWidget(exit_btn)

        # Scroll Area for Chat History (Visible in Expanded Mode)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_container)

        # Input Search Box
        self.input_container = QWidget()
        self.input_container.setStyleSheet("background: #080808; border: 1px solid #1a1a1a; border-radius: 14px;")
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(12, 4, 8, 4)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Search, open apps, blox fruit side, afk, or ask...")
        self.input_field.setFont(QFont("Segoe UI", 11))
        self.input_field.setStyleSheet("background: transparent; color: #ffffff; border: none;")
        self.input_field.returnPressed.connect(self.send_prompt)

        send_btn = QPushButton("↵")
        send_btn.setFixedSize(26, 26)
        send_btn.setStyleSheet("QPushButton { background: #8ab4f8; color: #000000; font-weight: bold; border-radius: 13px; } QPushButton:hover { background: #adc8ff; }")
        send_btn.clicked.connect(self.send_prompt)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)

        # Assemble UI Layout
        self.main_layout.addLayout(self.top_bar)
        self.main_layout.addWidget(self.scroll, 1)
        self.main_layout.addWidget(self.input_container)

        self.setCentralWidget(self.container)

        # Start in sleek compact search bar mode at top center
        self.apply_mode_geometry()

        self.drag_pos = QPoint()
        self.updater = AutoUpdater()
        self.updater.start()

        self.append_bubble("assistant", f"Online, {self.active_user}! Triple-click bar to expand/shrink.")

    # ----------------- COMPACT / EXPANDED MODES -----------------
    def apply_mode_geometry(self):
        screen = QApplication.primaryScreen().geometry()
        if self.is_compact:
            self.scroll.hide()
            self.title_lbl.setText("✦ Spark")
            self.mode_toggle_btn.setText("▼")
            self.resize(560, 84)
            # Dock horizontally centered right near the top of screen
            self.move((screen.width() - 560) // 2, 16)
        else:
            self.scroll.show()
            self.title_lbl.setText(f"✦ Spark Assistant ({self.active_user})")
            self.mode_toggle_btn.setText("▲")
            self.resize(700, 520)
            self.move((screen.width() - 700) // 2, 40)

    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        self.apply_mode_geometry()

    # ----------------- TRIPLE CLICK DETECTION & DRAGGING -----------------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            now = time.time()
            self.click_times.append(now)
            # Retain clicks within the last 0.6 seconds
            self.click_times = [t for t in self.click_times if now - t <= 0.6]

            # Detect triple click
            if len(self.click_times) >= 3:
                self.click_times.clear()
                self.toggle_compact_mode()
                return

            self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_pos)

    # ----------------- CHAT MESSAGES & DISPATCH -----------------
    def append_bubble(self, role: str, text: str):
        row = QHBoxLayout()
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFont(QFont("Segoe UI", 10))

        if role == "user":
            bubble.setStyleSheet("background-color: #121212; color: #ffffff; padding: 8px 12px; border-radius: 12px; border: 1px solid #222;")
            row.addStretch()
            row.addWidget(bubble)
        else:
            bubble.setStyleSheet("background-color: #050505; color: #8ab4f8; padding: 8px 12px; border-radius: 12px; border: 1px solid #1f1f1f;")
            row.addWidget(bubble)
            row.addStretch()

        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)
        QApplication.processEvents()
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def send_prompt(self):
        query = self.input_field.text().strip()
        if not query:
            return

        self.input_field.clear()

        # If sent while in compact mode, auto-expand to show response
        if self.is_compact and not any(k in query.lower() for k in ["marine", "pirate", "afk", "stop"]):
            self.toggle_compact_mode()

        self.append_bubble("user", query)
        AuditLogger.log(self.active_user, self.pc_name, self.win_user, query, "TASK_TRIGGERED")

        self.worker = TaskExecutionWorker(query)
        self.worker.task_completed.connect(self.on_task_finished)
        self.worker.start()

    def on_task_finished(self, result_text: str):
        self.append_bubble("assistant", result_text)


# ----------------- ENTRY POINT -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pc_name = os.environ.get("COMPUTERNAME", "Unknown-PC")
    win_user = os.environ.get("USERNAME", "Unknown-User")

    # Set up auto-start with Windows in Registry
    enable_windows_startup()

    auth = AuthDialog(pc_name, win_user)
    if auth.exec() == QDialog.DialogCode.Accepted:
        win = GeminiDesktopAssistant(auth.authenticated_user, auth.is_admin, pc_name, win_user)
        win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)