import sys
import os
import re
import time
import json
import glob
import hashlib
import datetime
import tempfile
import urllib.parse
import urllib.request
import subprocess
import webbrowser
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QLabel, 
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QScrollArea, QFrame, QDialog, QMessageBox, QRadioButton, 
    QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView
)

# ----------------- CONFIGURATION -----------------
GITHUB_REPO = "mariogodace-debug/SparkAssistant"
API_KEY = "AQ.Ab8RN6IR7b7XE7Yu7_CLErL7iiMv47BdQkMeew_J7NXfND1JcQ"

ADMIN_USERNAME = "shadow"
ADMIN_DEFAULT_PASS = "Mann@2041986"

MAX_LOG_ENTRIES = 1000
BASE_DIR = Path.home() / "Desktop"
LOG_FILE_PATH = BASE_DIR / "DeskAssistant_activity_log.txt"
USER_DB_PATH = Path(__file__).resolve().parent / "users_db.json"
VERSION_STAMP_FILE = Path(tempfile.gettempdir()) / "spark_version.txt"

CONTACTS = {
    "mom": "+910000000000",
    "dad": "+910000000000",
}

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

# ----------------- CONTINUOUS ZERO-TOUCH AUTO-UPDATER -----------------
class AutoUpdater(QThread):
    def run(self):
        time.sleep(3)
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/latest"
            req = urllib.request.Request(api_url, headers={"User-Agent": "SparkAssistant-ContinuousUpdater"})
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
            bat_content = f"""@echo off
timeout /t 1 /nobreak > nul
move /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat_content)

            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.Popen([bat_path], shell=True, creationflags=flags)
            os._exit(0)
        except Exception:
            pass


# ----------------- DB & LOGGING -----------------
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


# ----------------- SYSTEM AUTOMATION TOOLS -----------------
class SystemAutomation:
    APP_ALIASES = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "code": ["code"],
        "vscode": ["code"],
        "cmd": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "spotify": [os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")]
    }

    @classmethod
    def join_roblox_game(cls, experience_name_or_id: str) -> str:
        clean = experience_name_or_id.strip().lower()
        place_id = ROBLOX_EXPERIENCES.get(clean)
        
        if not place_id:
            for k, v in ROBLOX_EXPERIENCES.items():
                if k in clean:
                    place_id = v
                    break

        if not place_id:
            if clean.isdigit():
                place_id = clean
            else:
                search_url = f"https://www.roblox.com/discover/?Keyword={urllib.parse.quote_plus(clean)}"
                webbrowser.open(search_url)
                return f"Opening Roblox Discover search for '{experience_name_or_id}'."

        uri = f"roblox://placeId={place_id}"
        subprocess.Popen(f'start "" "{uri}"', shell=True)
        return f"Launching Roblox and joining {experience_name_or_id.title()} (Place ID: {place_id})!"

    @classmethod
    def open_app(cls, app_name: str) -> str:
        clean = app_name.strip().lower()

        # WhatsApp
        if "what" in clean and ("app" in clean or "sap" in clean):
            try:
                subprocess.Popen(["cmd", "/c", "start", "whatsapp:"], shell=True)
                return "Opening WhatsApp!"
            except Exception:
                webbrowser.open("https://web.whatsapp.com")
                return "Opening WhatsApp Web."

        # Plain Roblox Player launch
        if "roblox" in clean:
            roblox_local = os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions")
            if os.path.exists(roblox_local):
                exes = glob.glob(os.path.join(roblox_local, "**", "*.exe"), recursive=True)
                for exe in exes:
                    if "robloxplayer" in os.path.basename(exe).lower():
                        try:
                            subprocess.Popen([exe], shell=True)
                            return "Launching Roblox Player!"
                        except Exception:
                            pass

            pf_paths = [
                os.path.expandvars(r"%ProgramFiles(x86)%\Roblox\Versions"),
                os.path.expandvars(r"%ProgramFiles%\Roblox\Versions")
            ]
            for p_dir in pf_paths:
                if os.path.exists(p_dir):
                    exes = glob.glob(os.path.join(p_dir, "**", "*.exe"), recursive=True)
                    for exe in exes:
                        if "robloxplayer" in os.path.basename(exe).lower():
                            try:
                                subprocess.Popen([exe], shell=True)
                                return "Launching Roblox Player!"
                            except Exception:
                                pass

            for proto in ["roblox-player:", "roblox:"]:
                try:
                    subprocess.Popen(f'start "" "{proto}"', shell=True)
                    return "Launching Roblox Player!"
                except Exception:
                    pass

        # Check aliases
        if clean in cls.APP_ALIASES:
            for path in cls.APP_ALIASES[clean]:
                if os.path.exists(path) or not os.path.isabs(path):
                    try:
                        subprocess.Popen([path], shell=True)
                        return f"Opening {clean.title()}!"
                    except Exception:
                        pass

        # Search Start Menu & Desktop
        search_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            os.path.expandvars(r"%USERPROFILE%\OneDrive\Desktop")
        ]
        query_keywords = [w for w in clean.replace("-", " ").replace("_", " ").split() if w not in ["player", "game", "app"]]
        if not query_keywords:
            query_keywords = clean.split()

        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for root, _, files in os.walk(s_dir):
                for f in files:
                    fname = f.lower()
                    if fname.endswith((".lnk", ".exe", ".url")) and all(k in fname for k in query_keywords):
                        try:
                            os.startfile(os.path.join(root, f))
                            return f"Found and launched {f}!"
                        except Exception:
                            pass

        # Silent Microsoft Store App Check
        try:
            ps_cmd = f"Get-AppxPackage | Where-Object {{ $_.Name -like '*{query_keywords[0]}*' }} | Select-Object -ExpandProperty PackageFamilyName -First 1"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=3)
            pfn = res.stdout.strip()
            if pfn:
                subprocess.Popen(["powershell", "-NoProfile", "-Command", f"Start-Process 'shell:AppsFolder\\{pfn}!App'"], shell=True)
                return f"Launching {app_name.title()}!"
        except Exception:
            pass

        return f"Could not find '{app_name}' installed on this PC."

    @classmethod
    def system_command(cls, action_type: str, detail: str = "") -> str:
        action_type = action_type.lower()
        if action_type == "lock_pc":
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "PC locked."
        elif action_type == "mute_volume":
            subprocess.Popen("powershell -Command (New-Object -ComObject WScript.Shell).SendKeys([char]173)", shell=True)
            return "Toggled volume mute."
        elif action_type == "open_settings":
            subprocess.Popen("start ms-settings:", shell=True)
            return "Opened Windows Settings."
        elif action_type == "open_url":
            target = detail if detail.startswith("http") else f"https://{detail}"
            webbrowser.open(target)
            return f"Navigating to {target}."
        elif action_type == "search_web":
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(detail)}")
            return f"Searching Google for '{detail}'."
        elif action_type == "search_youtube":
            webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(detail)}")
            return f"Searching YouTube for '{detail}'."
        return "Task finished."


# ----------------- TASK EXECUTION & GEMINI WORKER -----------------
class TaskExecutionWorker(QThread):
    task_completed = pyqtSignal(str)

    def __init__(self, prompt: str, conversation_history: list):
        super().__init__()
        self.prompt = prompt
        self.history = conversation_history

    def run(self):
        p = self.prompt.strip().lower()

        # Roblox experiences
        if "roblox" in p or any(g in p for g in ROBLOX_EXPERIENCES):
            for game_name in ROBLOX_EXPERIENCES:
                if game_name in p:
                    res = SystemAutomation.join_roblox_game(game_name)
                    self.task_completed.emit(res)
                    return

        # App / Launch / Play shortcuts
        if re.search(r'^(?:open|opn|opne|start|strat|launch|play|run)\s+(.+)', p):
            target = re.sub(r'^(?:open|opn|opne|start|strat|launch|play|run)\s+', '', p).strip()
            if "." in target and not target.endswith(".exe") and " " not in target:
                res = SystemAutomation.system_command("open_url", target)
            else:
                res = SystemAutomation.open_app(target)
            self.task_completed.emit(res)
            return

        # Web & YouTube search shortcuts
        if re.search(r'^(?:search|seach|serch|google|gogle|lookup|find)\s+(.+)', p):
            query = re.sub(r'^(?:search|seach|serch|google|gogle|lookup|find)\s+', '', p).strip()
            if any(k in query for k in ["youtube", "yt", "utube"]):
                clean_q = re.sub(r'\b(on\s+)?(youtube|yt|utube)\b', '', query).strip()
                res = SystemAutomation.system_command("search_youtube", clean_q)
            else:
                res = SystemAutomation.system_command("search_web", query)
            self.task_completed.emit(res)
            return

        if re.search(r'(?:(?:open\s+)?(?:yt|youtube|utube)\s+(?:and\s+)?(?:search|seach|serch)\s+|(?:search|seach|serch)\s+(?:on\s+)?(?:yt|youtube|utube)\s+(?:for\s+)?|youtube\s+search\s+)(.+)', p):
            query = re.search(r'(?:(?:open\s+)?(?:yt|youtube|utube)\s+(?:and\s+)?(?:search|seach|serch)\s+|(?:search|seach|serch)\s+(?:on\s+)?(?:yt|youtube|utube)\s+(?:for\s+)?|youtube\s+search\s+)(.+)', p).group(1).strip()
            res = SystemAutomation.system_command("search_youtube", query)
            self.task_completed.emit(res)
            return

        # Gemini NLP Dispatcher for all multi-step and flexible commands
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=API_KEY)
            system_prompt = (
                "You are an OS desktop action controller. Decide whether the user wants to execute a computer task "
                "or just converse. If the user wants to do a computer task (apps, games, sound, settings, search, websites), "
                "respond ONLY with a JSON object: {\"action\": \"join_roblox\"|\"open_app\"|\"system_action\"|\"none\", \"parameter\": \"...\"}. "
                "If it is general conversation, reply naturally in clear, brief text without JSON."
            )

            formatted = []
            for item in self.history[-2:]:
                formatted.append(f"{item['role'].capitalize()}: {item['text']}")
            formatted.append(f"User: {self.prompt}")

            res = client.models.generate_content(
                model="gemini-3.8-flash",
                contents="\n".join(formatted),
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=220
                )
            )

            response_raw = (res.text or "").strip()

            if response_raw.startswith("{") and response_raw.endswith("}"):
                try:
                    action_data = json.loads(response_raw)
                    act = action_data.get("action")
                    param = action_data.get("parameter", "")

                    if act == "join_roblox":
                        out = SystemAutomation.join_roblox_game(param)
                        self.task_completed.emit(out)
                        return
                    elif act == "open_app":
                        out = SystemAutomation.open_app(param)
                        self.task_completed.emit(out)
                        return
                    elif act == "system_action":
                        out = SystemAutomation.system_command(param)
                        self.task_completed.emit(out)
                        return
                except Exception:
                    pass

            self.task_completed.emit(response_raw)
        except Exception as e:
            self.task_completed.emit(f"Could not complete task: {e}")


# ----------------- UI WINDOWS -----------------
class AdminPanelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shield Admin Console - Activity & Device Monitor")
        self.resize(850, 480)
        self.setStyleSheet("""
            QDialog { background-color: #121316; color: #e8eaed; font-family: 'Segoe UI'; }
            QLabel { color: #a8c7fa; font-size: 13px; }
            QLineEdit { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px; color: white; }
            QTableWidget { background-color: #1a1b20; color: #e8eaed; gridline-color: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; }
            QHeaderView::section { background-color: #24262c; color: #8ab4f8; padding: 6px; border: 1px solid rgba(255, 255, 255, 0.05); font-weight: bold; }
            QPushButton { background-color: #2b303c; color: white; border-radius: 6px; padding: 6px 14px; font-size: 12px; border: 1px solid rgba(255, 255, 255, 0.15); }
            QPushButton:hover { background-color: #3b4252; }
            QPushButton#DangerBtn:hover { background-color: #d93025; }
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
            QDialog { background-color: #17181c; color: #e8eaed; font-family: 'Segoe UI'; }
            QLabel { color: #e8eaed; font-size: 13px; }
            QLineEdit { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 8px; color: white; }
            QRadioButton { color: #c4c7c5; }
            QPushButton { background-color: #8ab4f8; color: #131314; border-radius: 8px; padding: 10px; font-weight: bold; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        info_lbl = QLabel(f"<b>Device:</b> {self.pc_name} ({self.win_user})")
        info_lbl.setStyleSheet("color: #a8c7fa; font-size: 12px;")
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


class GeminiDesktopAssistant(QMainWindow):
    def __init__(self, active_user: str, is_admin: bool, pc_name: str, win_user: str):
        super().__init__()
        self.active_user = active_user
        self.is_admin = is_admin
        self.pc_name = pc_name
        self.win_user = win_user

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(700, 520)

        self.conversation = []

        container = QWidget(self)
        container.setObjectName("Card")
        container.setStyleSheet("QWidget#Card { background-color: rgba(23, 24, 28, 245); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 20px; }")

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 16, 20, 18)
        main_layout.setSpacing(12)

        top_bar = QHBoxLayout()
        title = QLabel(f"✦ {'Admin Mode (' + self.active_user + ')' if self.is_admin else 'User: ' + self.active_user}")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #a8c7fa;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        if self.is_admin:
            admin_btn = QPushButton("🛡️ Admin Panel")
            admin_btn.setFixedSize(110, 26)
            admin_btn.setStyleSheet("QPushButton { background: rgba(138, 180, 248, 0.15); color: #8ab4f8; border-radius: 12px; font-size: 11px; font-weight: bold; }")
            admin_btn.clicked.connect(lambda: AdminPanelDialog(self).exec())
            top_bar.addWidget(admin_btn)

        exit_btn = QPushButton("✕")
        exit_btn.setFixedSize(28, 24)
        exit_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); color: #b0b0b8; border-radius: 12px; } QPushButton:hover { background: #ff453a; color: white; }")
        exit_btn.clicked.connect(QApplication.instance().quit)
        top_bar.addWidget(exit_btn)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_container)

        self.append_bubble("assistant", f"Hello {self.active_user}! Ask me anything or tell me to run tasks on your PC.")

        input_container = QWidget()
        input_container.setStyleSheet("background: rgba(36, 38, 44, 240); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 20px;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(16, 8, 12, 8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Tell me any task (e.g. open roblox blox fruit, search google, play music)...")
        self.input_field.setFont(QFont("Segoe UI", 13))
        self.input_field.setStyleSheet("background: transparent; color: #f1f3f4; border: none;")
        self.input_field.returnPressed.connect(self.send_prompt)

        send_btn = QPushButton("↵")
        send_btn.setFixedSize(30, 30)
        send_btn.setStyleSheet("QPushButton { background: #8ab4f8; color: #1e1f20; font-weight: bold; border-radius: 15px; }")
        send_btn.clicked.connect(self.send_prompt)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)

        main_layout.addLayout(top_bar)
        main_layout.addWidget(self.scroll, 1)
        main_layout.addWidget(input_container)

        self.setCentralWidget(container)

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, int(screen.height() * 0.16))
        self.drag_pos = QPoint()

        # Silent updater thread starts in background
        self.updater = AutoUpdater()
        self.updater.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_pos)

    def append_bubble(self, role: str, text: str):
        row = QHBoxLayout()
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFont(QFont("Segoe UI", 11))

        if role == "user":
            bubble.setStyleSheet("background-color: #2b303c; color: #e8eaed; padding: 10px 14px; border-radius: 14px;")
            row.addStretch()
            row.addWidget(bubble)
        else:
            bubble.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); color: #d2e3fc; padding: 10px 14px; border-radius: 14px; border: 1px solid rgba(138, 180, 248, 0.25);")
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
        self.append_bubble("user", query)
        self.conversation.append({"role": "user", "text": query})

        AuditLogger.log(self.active_user, self.pc_name, self.win_user, query, "TASK_TRIGGERED")

        self.worker = TaskExecutionWorker(query, self.conversation)
        self.worker.task_completed.connect(self.on_task_finished)
        self.worker.start()

    def on_task_finished(self, result_text: str):
        self.append_bubble("assistant", result_text)
        self.conversation.append({"role": "assistant", "text": result_text})


# ----------------- ENTRY POINT -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pc_name = os.environ.get("COMPUTERNAME", "Unknown-PC")
    win_user = os.environ.get("USERNAME", "Unknown-User")

    auth = AuthDialog(pc_name, win_user)
    if auth.exec() == QDialog.DialogCode.Accepted:
        win = GeminiDesktopAssistant(auth.authenticated_user, auth.is_admin, pc_name, win_user)
        win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)