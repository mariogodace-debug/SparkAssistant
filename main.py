# -*- coding: utf-8 -*-
import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import re
import time
import json
import socket
import hashlib
import datetime
import urllib.parse
import urllib.request
import subprocess
import webbrowser
import sqlite3
from pathlib import Path
import ctypes
import multiprocessing as mp
from urllib.parse import quote_plus
import numpy as np

psutil = None
pyperclip = None
mss = None
pytesseract = None

try:
    import psutil
except ImportError:
    pass

try:
    import pyperclip
except ImportError:
    pass

try:
    import mss
    import pytesseract
    if os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    pass

from PyQt6.QtCore import (
    Qt, QPoint, QThread, pyqtSignal, pyqtProperty,
    QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import QFont, QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QLabel,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QScrollArea, QFrame, QDialog, QMessageBox, QTextEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog
)

try:
    pass
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

APP_NAME = "SparkAssistant"
ADMIN_USERNAME = "shadow"
ADMIN_DEFAULT_PASS = "7098"
CREATE_NO_WINDOW = 0x08000000

if getattr(sys, 'frozen', False):
    PORTABLE_DIR = Path(sys.executable).resolve().parent
else:
    PORTABLE_DIR = Path(__file__).resolve().parent

USER_DB_PATH = PORTABLE_DIR / "users_db.json"
KNOWLEDGE_DB_PATH = PORTABLE_DIR / "knowledge.db"
NOTES_DB_PATH = PORTABLE_DIR / "notes.db"
REMINDERS_DB_PATH = PORTABLE_DIR / "reminders.db"
LOG_FILE_PATH = PORTABLE_DIR / "DeskAssistant_activity_log.txt"

ROBLOX_EXPERIENCES = {
    "blox fruits": "2753915549",
    "blox fruit": "2753915549",
    "brookhaven": "4924922222",
    "adopt me": "920587237",
    "arsenal": "286090429",
    "blade ball": "13772394625",
    "doors": "6516141723",
}

def init_databases():
    for db_path, query in [
        (NOTES_DB_PATH, "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, title TEXT, content TEXT, timestamp TEXT)"),
        (REMINDERS_DB_PATH, "CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, task TEXT, due_time TEXT, status TEXT)")
    ]:
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute(query)
            conn.close()
        except Exception:
            pass

init_databases()


# ==================== UNIVERSAL AUTONOMOUS TASK ENGINE ====================

class AutonomousTaskEngine:
    APP_ALIASES = {
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "edge": "start msedge",
        "microsoft edge": "start msedge",
        "brave": "start brave",
        "firefox": "start firefox",
        "notepad": "start notepad",
        "calculator": "start calc",
        "calc": "start calc",
        "paint": "start mspaint",
        "cmd": "start cmd",
        "command prompt": "start cmd",
        "terminal": "start wt",
        "powershell": "start powershell",
        "task manager": "start taskmgr",
        "taskmgr": "start taskmgr",
        "control panel": "start control",
        "settings": "start ms-settings:",
        "windows settings": "start ms-settings:",
        "wifi settings": "start ms-settings:network-wifi",
        "bluetooth": "start ms-settings:bluetooth",
        "bluetooth settings": "start ms-settings:bluetooth",
        "display settings": "start ms-settings:display",
        "sound settings": "start ms-settings:sound",
        "file explorer": "start explorer",
        "explorer": "start explorer",
        "files": "start explorer",
        "this pc": "start explorer shell:MyComputerFolder",
        "recycle bin": "start explorer shell:RecycleBinFolder",
        "vscode": "start code",
        "vs code": "start code",
        "visual studio code": "start code",
        "spotify": "start spotify:",
        "discord": "start discord:",
        "steam": "start steam:",
        "whatsapp": "start whatsapp:",
        "telegram": "start tg:",
        "roblox": "start roblox:",
        "word": "start winword",
        "excel": "start excel",
        "powerpoint": "start powerpnt",
        "snipping tool": "start ms-screenclip:",
        "device manager": "start devmgmt.msc",
        "disk management": "start diskmgmt.msc",
        "services": "start services.msc",
        "registry": "start regedit",
        "regedit": "start regedit",
        "character map": "start charmap",
        "magnifier": "start magnify",
        "on screen keyboard": "start osk",
    }

    WEB_SHORTCUTS = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "reddit": "https://www.reddit.com",
        "chatgpt": "https://chatgpt.com",
        "claude": "https://claude.ai",
        "gemini": "https://gemini.google.com",
        "tradingview": "https://www.tradingview.com",
        "tinkercad": "https://www.tinkercad.com",
        "cults3d": "https://cults3d.com",
        "supabase": "https://supabase.com",
        "netlify": "https://app.netlify.com",
        "stackoverflow": "https://stackoverflow.com",
        "wikipedia": "https://www.wikipedia.org",
        "amazon": "https://www.amazon.in",
        "flipkart": "https://www.flipkart.com",
    }

    @classmethod
    def find_shortcut_in_start_menu(cls, app_query: str) -> str:
        search_dirs = [
            Path(os.environ.get("ProgramData", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        ]
        target = app_query.lower().strip()
        best_match = None

        for base_dir in search_dirs:
            if not base_dir.exists():
                continue
            try:
                for root, _, files in os.walk(str(base_dir)):
                    for f in files:
                        if f.lower().endswith((".lnk", ".url", ".exe")):
                            name_no_ext = os.path.splitext(f)[0].lower()
                            if name_no_ext == target:
                                return os.path.join(root, f)
                            elif target in name_no_ext and best_match is None:
                                best_match = os.path.join(root, f)
            except Exception:
                continue
        return best_match or ""

    @classmethod
    def launch_anything(cls, target_raw: str) -> str:
        target = target_raw.strip().lower()
        target = re.sub(r'^(?:please\s+|can\s+you\s+|bro\s+)?(?:open|launch|start|run)\s+(?:the\s+|my\s+|app\s+)?', '', target).strip()

        if not target:
            return "Please specify what you want to open."

        # 1. Check Roblox games
        for game_name, place_id in ROBLOX_EXPERIENCES.items():
            if game_name in target:
                os.system(f"start roblox://placeId={place_id}")
                return f"🎮 Launched {game_name.title()} in Roblox!"

        # 2. Check User Special Folders
        user_home = Path.home()
        folder_map = {
            "downloads": user_home / "Downloads",
            "download": user_home / "Downloads",
            "documents": user_home / "Documents",
            "desktop": user_home / "Desktop",
            "pictures": user_home / "Pictures",
            "videos": user_home / "Videos",
            "music": user_home / "Music",
        }
        if target in folder_map and folder_map[target].exists():
            os.startfile(str(folder_map[target]))
            return f"📂 Opened your {target.title()} folder."

        # 3. Check Direct App Aliases
        if target in cls.APP_ALIASES:
            subprocess.Popen(cls.APP_ALIASES[target], shell=True)
            return f"🚀 Opened {target.title()}."

        # 4. Check Web Shortcuts
        if target in cls.WEB_SHORTCUTS:
            webbrowser.open(cls.WEB_SHORTCUTS[target])
            return f"🌐 Opened {target.title()} in your browser."

        # 5. Check if it's a URL / Domain (e.g., example.com)
        if "." in target and " " not in target:
            url = target if target.startswith("http") else f"https://{target}"
            webbrowser.open(url)
            return f"🌐 Opened {url}"

        # 6. Scan Windows Start Menu & Desktop Shortcuts (.lnk / .exe)
        shortcut_path = cls.find_shortcut_in_start_menu(target)
        if shortcut_path:
            try:
                os.startfile(shortcut_path)
                return f"🚀 Launched '{os.path.basename(shortcut_path)}' from system shortcuts."
            except Exception:
                pass

        # 7. Try Windows App Execution Alias / PATH executable
        try:
            res = subprocess.run(f"where {target}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
            if res.returncode == 0:
                subprocess.Popen(f'start "" "{target}"', shell=True)
                return f"🚀 Launched {target}."
        except Exception:
            pass

        # 8. Try PowerShell Start-Process fallback or open on Web
        try:
            ps_check = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Start-Process '{target}' -ErrorAction Stop"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW, timeout=3
            )
            if ps_check.returncode == 0:
                return f"🚀 Started '{target}'."
        except Exception:
            pass

        # 9. Final Fallback: Open via Google "I'm Feeling Lucky" or Search
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(target)}")
        return f"🌐 Could not find a local app named '{target_raw}', so I opened it in your browser."

    @classmethod
    def close_app(cls, app_query: str) -> str:
        target = re.sub(r'^(?:please\s+|can\s+you\s+)?(?:close|kill|stop|exit|quit)\s+(?:the\s+|app\s+)?', '', app_query.lower()).strip()
        if not target:
            return "Specify which application to close."

        proc_aliases = {
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "edge": "msedge.exe",
            "notepad": "notepad.exe",
            "calculator": "CalculatorApp.exe",
            "calc": "CalculatorApp.exe",
            "vscode": "Code.exe",
            "vs code": "Code.exe",
            "spotify": "Spotify.exe",
            "discord": "Discord.exe",
            "steam": "steam.exe",
            "roblox": "RobloxPlayerBeta.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "vlc": "vlc.exe",
        }
        exe_name = proc_aliases.get(target, f"{target}.exe" if not target.endswith(".exe") else target)

        killed = []
        if psutil:
            for p in psutil.process_iter(['name']):
                try:
                    pname = p.info['name'] or ""
                    if target in pname.lower() or pname.lower() == exe_name.lower():
                        p.terminate()
                        killed.append(pname)
                except Exception:
                    pass
        if killed:
            return f"🛑 Closed running process(es): {', '.join(set(killed))}."

        res = subprocess.run(f"taskkill /F /IM {exe_name} /T", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        if res.returncode == 0:
            return f"🛑 Closed {exe_name}."
        return f"⚠️ Could not find an active process matching '{target}'."

    @classmethod
    def execute_If_Matched(cls, prompt: str, active_user: str) -> str:
        p_clean = prompt.strip()
        p = p_clean.lower()

        # 1. Open / Launch / Start Any App, Folder, or Website
        if re.match(r'^(?:please\s+|can\s+you\s+|bro\s+)?(?:open|launch|start)\s+.+', p):
            return cls.launch_anything(p_clean)

        # 2. Close / Kill / Quit Any App
        if re.match(r'^(?:please\s+|can\s+you\s+|bro\s+)?(?:close|kill|quit|terminate)\s+.+', p):
            if p not in ("close window", "exit", "quit"):
                return cls.close_app(p_clean)

        # 3. Play Music / Video on YouTube or Spotify
        if p.startswith("play "):
            query_media = p_clean[5:].strip()
            for game_name, place_id in ROBLOX_EXPERIENCES.items():
                if game_name in query_media.lower():
                    os.system(f"start roblox://placeId={place_id}")
                    return f"🎮 Launching {game_name.title()} in Roblox!"
            if "spotify" in query_media.lower():
                track = re.sub(r'\s+on\s+spotify', '', query_media, flags=re.IGNORECASE).strip()
                os.system(f'start spotify:search:"{track}"')
                return f"🎵 Playing '{track}' on Spotify."
            else:
                track = re.sub(r'\s+on\s+youtube', '', query_media, flags=re.IGNORECASE).strip()
                webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(track)}")
                return f"▶️ Opening '{track}' on YouTube."

        # 4. Volume & Media Keys
        if p in ("volume up", "increase volume", "louder", "vol up"):
            subprocess.Popen("powershell -Command $w=New-Object -ComObject WScript.Shell;1..5| ForEach-Object {$w.SendKeys([char]175) }", shell=True, creationflags=CREATE_NO_WINDOW)
            return "🔊 Increased system volume."
        if p in ("volume down", "decrease volume", "quieter", "vol down"):
            subprocess.Popen("powershell -Command $w=New-Object -ComObject WScript.Shell;1..5| ForEach-Object {$w.SendKeys([char]174) }", shell=True, creationflags=CREATE_NO_WINDOW)
            return "🔉 Decreased system volume."
        if p in ("mute", "unmute", "mute volume", "toggle mute"):
            subprocess.Popen("powershell -Command (New-Object -ComObject WScript.Shell).SendKeys([char]173)", shell=True, creationflags=CREATE_NO_WINDOW)
            return "🔇 Toggled system volume mute."

        # 5. Power & Workstation Control
        if p in ("lock pc", "lock screen", "lock computer", "lock"):
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "🔒 Workstation locked."
        if p in ("sleep pc", "sleep computer", "put pc to sleep"):
            subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "🌙 Putting PC to sleep..."
        if p in ("shutdown pc", "shutdown computer"):
            subprocess.Popen("shutdown /s /t 30", shell=True)
            return "⚠️ PC will shut down in 30 seconds. Type `cancel shutdown` to abort."
        if p in ("cancel shutdown", "abort shutdown", "stop shutdown"):
            subprocess.Popen("shutdown /a", shell=True)
            return "✅ Scheduled shutdown cancelled."
        if p in ("restart pc", "reboot pc"):
            subprocess.Popen("shutdown /r /t 30", shell=True)
            return "🔄 PC will restart in 30 seconds. Type `cancel shutdown` to abort."

        # 6. Screenshot Capture
        if p in ("take screenshot", "screenshot", "capture screen", "take a screenshot"):
            if mss:
                try:
                    out_file = Path.home() / "Desktop" / f"Spark_Screenshot_{int(time.time())}.png"
                    with mss.mss() as sct:
                        sct.shot(output=str(out_file))
                    os.startfile(str(out_file))
                    return f"📸 Screenshot saved to Desktop and opened:\n{out_file}"
                except Exception as e:
                    return f"Screenshot error: {e}"
            else:
                subprocess.Popen("start ms-screenclip:", shell=True)
                return "📸 Launched Windows Snipping Tool."

        # 7. File & Folder Creation on Desktop
        folder_match = re.match(r'^(?:create|make|new)\s+folder\s+(?:named\s+|called\s+)?(.+)', p_clean, flags=re.IGNORECASE)
        if folder_match:
            fname = folder_match.group(1).strip()
            target_dir = Path.home() / "Desktop" / fname
            target_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(target_dir))
            return f"📁 Created folder '{fname}' on your Desktop and opened it."

        file_match = re.match(r'^(?:create|make|new)\s+file\s+(?:named\s+|called\s+)?(.+)', p_clean, flags=re.IGNORECASE)
        if file_match:
            fname = file_match.group(1).strip()
            target_file = Path.home() / "Desktop" / fname
            if not target_file.exists():
                target_file.write_text("", encoding="utf-8")
            os.startfile(str(target_file))
            return f"📄 Created file '{fname}' on your Desktop and opened it."

        if p in ("empty recycle bin", "clear recycle bin"):
            subprocess.Popen("powershell -NoProfile -Command Clear-RecycleBin -Force -ErrorAction SilentlyContinue", shell=True, creationflags=CREATE_NO_WINDOW)
            return "🗑️ Emptied the Windows Recycle Bin."

        # 8. System Diagnostics, Time, IP, Battery, Processes
        if p in ("time", "what time is it", "current time", "date", "what is the date"):
            now = datetime.datetime.now().strftime("%A, %d %B %Y | %I:%M:%S %p")
            return f"🕒 Current Date & Time:\n{now}"

        if p in ("my ip", "ip address", "what is my ip", "check ip"):
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                return f"🌐 Network Info:\n• Hostname: {hostname}\n• Local IPv4: {local_ip}"
            except Exception as e:
                return f"Could not read IP: {e}"

        if p in ("battery", "battery status", "check battery"):
            if psutil and hasattr(psutil, "sensors_battery"):
                bat = psutil.sensors_battery()
                if bat:
                    plug = "Plugged In ⚡" if bat.power_plugged else "On Battery 🔋"
                    return f"🔋 Battery Status: {bat.percent}% ({plug})"
                return "🖥️ No battery detected (Desktop PC / AC Power)."

        if p in ("top processes", "running apps", "list processes", "what is using my ram"):
            if psutil:
                procs = []
                for proc in psutil.process_iter(['name', 'memory_info']):
                    try:
                        mem_mb = proc.info['memory_info'].rss / (1024 * 1024)
                        procs.append((mem_mb, proc.info['name']))
                    except Exception:
                        pass
                procs.sort(reverse=True)
                top5 = "\n".join([f"• {name}: {round(mem, 1)} MB" for mem, name in procs[:6]])
                return f"⚙️ Top RAM-Consuming Processes:\n{top5}"

        # 9. Direct Terminal / PowerShell Execution (cmd <X> / run <X> / powershell <X>)
        if p.startswith(("cmd ", "powershell ", "ps ", "terminal ", "run command ")):
            raw_cmd = re.sub(r'^(?:cmd|powershell|ps|terminal|run command)\s+', '', p_clean, flags=re.IGNORECASE).strip()
            try:
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", raw_cmd],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, timeout=12, creationflags=CREATE_NO_WINDOW
                )
                out = (proc.stdout or proc.stderr or "Command executed with no output.").strip()
                return f"💻 [Terminal Output]:\n{out[:1800]}"
            except Exception as e:
                return f"💻 [Command Error]: {e}"

        # 10. Search Web & YouTube Shortcuts
        if p.startswith(("google ", "search ", "search for ")):
            q = re.sub(r'^(?:google|search for|search)\s+', '', p_clean, flags=re.IGNORECASE).strip()
            webbrowser.open(f"https://www.google.com/search?q={quote_plus(q)}")
            return f"🌐 Opened Google search for '{q}'."

        if p.startswith("youtube "):
            q = p_clean[8:].strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(q)}")
            return f"▶️ Opened YouTube search for '{q}'."

        return ""


# ==================== AGENT REACH, CONTEXT 7 & SYSTEM TOOLS ====================

class AgentReach:
    @classmethod
    def extract_youtube_id(cls, url: str) -> str:
        match = re.search(r'(?:youtu\.be\/|v=|\/embed\/|\/v\/|\/shorts\/)([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else ""

    @classmethod
    def fetch_youtube_page_details(cls, vid_id: str) -> dict:
        details = {"title": "", "author": "", "description": "", "captions": ""}
        try:
            req = urllib.request.Request(
                f"https://www.youtube.com/watch?v={vid_id}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            title_m = re.search(r'"videoDetails":\{.*?"title":"((?:\\.|[^"\\])*)"', html)
            author_m = re.search(r'"videoDetails":\{.*?"author":"((?:\\.|[^"\\])*)"', html)
            desc_m = re.search(r'"shortDescription":"((?:\\.|[^"\\])*)"', html)

            if title_m:
                details["title"] = bytes(title_m.group(1), "utf-8").decode("unicode_escape", errors="ignore")
            if author_m:
                details["author"] = bytes(author_m.group(1), "utf-8").decode("unicode_escape", errors="ignore")
            if desc_m:
                details["description"] = bytes(desc_m.group(1), "utf-8").decode("unicode_escape", errors="ignore")

            cap_m = re.search(r'"captionTracks":\s*(\[.*?\])', html)
            if cap_m:
                tracks = json.loads(cap_m.group(1))
                if tracks and tracks[0].get("baseUrl"):
                    c_url = tracks[0]["baseUrl"]
                    req_c = urllib.request.Request(c_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req_c, timeout=5) as c_resp:
                        xml_data = c_resp.read().decode("utf-8", errors="ignore")
                        texts = re.findall(r'<text[^>]*>(.*?)</text>', xml_data)
                        cleaned = " ".join([re.sub(r'&[^;]+;', ' ', t) for t in texts if t.strip()])
                        if cleaned.strip():
                            details["captions"] = cleaned[:3500]
        except Exception:
            pass

        if not details["title"]:
            try:
                oembed = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_id}&format=json"
                req_o = urllib.request.Request(oembed, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_o, timeout=4) as r_o:
                    odata = json.loads(r_o.read().decode())
                    details["title"] = odata.get("title", "")
                    details["author"] = odata.get("author_name", "")
            except Exception:
                pass
        return details

    @classmethod
    def fetch_youtube_content(cls, url: str) -> str:
        vid_id = cls.extract_youtube_id(url)
        if not vid_id:
            return "[Agent Reach Error] Could not parse a valid 11-character YouTube video ID."

        transcript_text = ""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            try:
                ytt_instance = YouTubeTranscriptApi()
                if hasattr(ytt_instance, "fetch"):
                    fetched = ytt_instance.fetch(vid_id, languages=['en', 'en-US', 'hi'])
                    if hasattr(fetched, "to_raw_data"):
                        raw = fetched.to_raw_data()
                        transcript_text = " ".join([x.get("text", "") for x in raw])
                    else:
                        transcript_text = " ".join([getattr(x, "text", "") for x in fetched])
            except Exception:
                pass

            if not transcript_text.strip() and hasattr(YouTubeTranscriptApi, "get_transcript"):
                raw = YouTubeTranscriptApi.get_transcript(vid_id, languages=['en', 'en-US', 'hi'])
                transcript_text = " ".join([x.get("text", "") for x in raw])
        except Exception:
            pass

        page_info = cls.fetch_youtube_page_details(vid_id)
        if not transcript_text.strip():
            transcript_text = page_info.get("captions", "")

        header = f"Video Title: {page_info.get('title') or 'Unknown'}\nChannel: {page_info.get('author') or 'Unknown'}\n"
        if transcript_text.strip():
            return f"{header}\nTranscript:\n{transcript_text[:3500]}"
        elif page_info.get("description"):
            return f"{header}\nVideo Description (No subtitles on video):\n{page_info['description'][:2500]}"
        elif page_info.get("title"):
            return f"{header}\n(Subtitles and extended description are disabled for this video.)"
        return "[Agent Reach Error] Could not retrieve video data. Check your internet connection."

    @classmethod
    def fetch_github_repo(cls, url: str) -> str:
        match = re.search(r'github\.com\/([^\/]+)\/([^\/\s#\?]+)', url)
        if not match:
            return "[Agent Reach Error] Invalid GitHub repository URL."
        owner, repo = match.group(1), match.group(2)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "SparkAssistant/4.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                desc = data.get("description") or "No description provided."
                stars = data.get("stargazers_count", 0)
                forks = data.get("forks_count", 0)
                lang = data.get("language") or "Multiple/Unknown"
                topics = ", ".join(data.get("topics", []))
                return (
                    f"📦 Repository: {owner}/{repo}\n"
                    f"⭐ Stars: {stars} | 🍴 Forks: {forks} | 💻 Language: {lang}\n"
                    f"🏷️ Topics: {topics if topics else 'None'}\n"
                    f"📝 Description: {desc}"
                )
        except Exception as e:
            return f"[Agent Reach GitHub Error]: {str(e)}"

    @classmethod
    def fetch_reddit_post(cls, url: str) -> str:
        clean_url = url.split("?")[0].rstrip("/") + ".json"
        try:
            req = urllib.request.Request(clean_url, headers={"User-Agent": "SparkAssistant/4.0 (Windows)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                post_data = data[0]['data']['children'][0]['data']
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')[:1200]
                score = post_data.get('score', 0)
                sub = post_data.get('subreddit_name_prefixed', '')
                return f"📌 {sub} (Upvotes: {score})\nTitle: {title}\n\n{selftext}"
        except Exception as e:
            return f"[Agent Reach Reddit Error]: {str(e)}"


class Context7Docs:
    @classmethod
    def fetch_pypi_docs(cls, package_name: str) -> str:
        pkg = package_name.strip().lower()
        aliases = {
            "cv2": "opencv-python",
            "opencv": "opencv-python",
            "pil": "pillow",
            "sklearn": "scikit-learn",
            "bs4": "beautifulsoup4",
            "yt": "youtube-transcript-api"
        }
        pkg = aliases.get(pkg, pkg)
        url = f"https://pypi.org/pypi/{pkg}/json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SparkAssistant/4.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                info = data.get("info", {})
                summary = info.get("summary", "No summary available.")
                version = info.get("version", "latest")
                home_page = info.get("home_page") or info.get("project_url") or ""
                desc = info.get("description", "")
                desc_clean = re.sub(r'<[^>]+>', '', desc).strip()[:1400]
                return (
                    f"📚 [Context 7 Live Docs: {pkg} (v{version})]\n"
                    f"🔹 Summary: {summary}\n"
                    f"🔗 Docs URL: {home_page}\n\n"
                    f"📖 Documentation Excerpt:\n{desc_clean}"
                )
        except Exception:
            return f"📚 [Context 7] Could not find package '{package_name}' on PyPI. Try the exact pip package name."


class SystemMonitor:
    @classmethod
    def get_stats(cls) -> str:
        if psutil is None:
            return "psutil library not installed. Run `pip install psutil`."
        try:
            cpu = psutil.cpu_percent(interval=0.3)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return (
                f"📊 [System Performance Status]\n"
                f"• CPU Load: {cpu}%\n"
                f"• RAM Usage: {ram.percent}% ({round(ram.used / (1024**3), 2)} GB / {round(ram.total / (1024**3), 2)} GB)\n"
                f"• Disk Free: {round(disk.free / (1024**3), 1)} GB ({100 - disk.percent}% free)"
            )
        except Exception as e:
            return f"Error reading system stats: {str(e)}"


class ScreenOCR:
    @classmethod
    def capture_and_read(cls) -> str:
        if mss is None or pytesseract is None:
            return "[OCR Error] Please install mss and pytesseract (`pip install mss pytesseract`) and Tesseract-OCR."
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                img_np = np.array(img)
                text = pytesseract.image_to_string(img_np).strip()
                return text if text else "[OCR] No legible text found on screen."
        except Exception as e:
            return f"[OCR Error] {str(e)}"


# ==================== DATABASE & HYBRID AI ENGINE ====================

class ScratchpadManager:
    @classmethod
    def save_note(cls, username: str, title: str, content: str):
        try:
            conn = sqlite3.connect(str(NOTES_DB_PATH))
            tstamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO notes (username, title, content, timestamp) VALUES (?, ?, ?, ?)", (username.lower(), title, content, tstamp))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @classmethod
    def clear_notes(cls, username: str):
        try:
            conn = sqlite3.connect(str(NOTES_DB_PATH))
            conn.execute("DELETE FROM notes WHERE username = ?", (username.lower(),))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @classmethod
    def load_notes(cls, username: str) -> list:
        try:
            conn = sqlite3.connect(str(NOTES_DB_PATH))
            c = conn.cursor()
            c.execute("SELECT title, content, timestamp FROM notes WHERE username = ? ORDER BY id DESC", (username.lower(),))
            rows = c.fetchall()
            conn.close()
            return rows
        except Exception:
            return []


class ReminderManager:
    @classmethod
    def add_reminder(cls, username: str, task: str) -> str:
        try:
            conn = sqlite3.connect(str(REMINDERS_DB_PATH))
            due = (datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime("%H:%M:%S")
            conn.execute("INSERT INTO reminders (username, task, due_time, status) VALUES (?, ?, ?, ?)", (username.lower(), task, due, "PENDING"))
            conn.commit()
            conn.close()
            return f"Reminder saved: '{task}' (Scheduled for {due})."
        except Exception:
            return "Failed to set reminder."

    @classmethod
    def get_reminders(cls, username: str) -> list:
        try:
            conn = sqlite3.connect(str(REMINDERS_DB_PATH))
            c = conn.cursor()
            c.execute("SELECT task, due_time FROM reminders WHERE username = ? AND status = 'PENDING'", (username.lower(),))
            rows = c.fetchall()
            conn.close()
            return rows
        except Exception:
            return []


class KnowledgeDatabase:
    STOPWORDS = {
        "open", "close", "launch", "start", "run", "play", "what", "is", "are", "the", "a",
        "an", "in", "on", "to", "for", "of", "and", "or", "how", "can", "you", "me", "my",
        "tell", "about", "explain", "define", "please", "bro", "hey", "hi", "hello", "with"
    }

    @classmethod
    def get_connection(cls):
        conn = sqlite3.connect(str(KNOWLEDGE_DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def initialize_db(cls):
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(title, content, category);")
            cursor.execute("SELECT count(*) FROM knowledge_fts")
            if cursor.fetchone()[0] == 0:
                starter = [
                    ("Identity", "SparkAssistant is an autonomous, portable desktop companion with Agent Reach, Context 7 live docs, OCR, and Ollama local AI.", "System"),
                    ("RAM", "RAM is high-speed volatile system memory used by the CPU to store actively running applications and temporary execution state.", "Hardware"),
                    ("Blox Fruits Overview", "Blox Fruits is an adventure game on Roblox where players master fighting styles, swords, and devil fruits.", "Roblox"),
                    ("Buddha Fruit", "The Buddha Fruit is the #1 grinding and raid fruit in Blox Fruits due to its giant hitbox, damage reduction, and melee reach.", "Roblox"),
                    ("Kitsune Fruit", "Kitsune is a mythical beast-type fruit featuring high speed, tail meters, transformation, and strong AoE fox fire disruption.", "Roblox"),
                    ("Screen Capture Hotkey", "Press Win + Shift + S to launch the Windows Snipping Tool selector for screen captures.", "Windows")
                ]
                cursor.executemany("INSERT INTO knowledge_fts (title, content, category) VALUES (?, ?, ?)", starter)
                conn.commit()
            conn.close()
        except Exception:
            pass

    @classmethod
    def query(cls, prompt: str) -> str:
        prompt_clean = prompt.strip()
        if not prompt_clean:
            return ""
        try:
            sanitized = re.sub(r'[^\w\s]', '', prompt_clean.lower()).strip()
            meaningful_tokens = [t for t in sanitized.split() if len(t) > 2 and t not in cls.STOPWORDS]
            if not meaningful_tokens:
                return ""
            conn = cls.get_connection()
            cursor = conn.cursor()
            fts_query = " AND ".join([f'"{t}"*' for t in meaningful_tokens])
            cursor.execute("SELECT title, content, category FROM knowledge_fts WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT 2", (fts_query,))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                return "\n\n".join([f"📁 [{r['title']}] ({r['category']}):\n{r['content']}" for r in rows])
        except Exception:
            pass
        return ""

KnowledgeDatabase.initialize_db()


class HybridAIEngine:
    force_offline = False
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    OLLAMA_MODEL = "llama3.2:1b"

    GREETINGS = {"hello", "hi", "hey", "hola", "yo", "sup", "good morning", "good evening", "how are you", "who are you"}

    @classmethod
    def ensure_ollama_running(cls):
        try:
            with socket.create_connection(("127.0.0.1", 11434), timeout=0.4):
                return True
        except Exception:
            try:
                subprocess.Popen("ollama serve", shell=True, stdout= subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
                time.sleep(1.2)
                return True
            except Exception:
                return False

    @classmethod
    def is_offline_forced(cls) -> bool:
        return bool(cls.force_offline)

    @classmethod
    def is_connected_to_internet(cls) -> bool:
        if cls.is_offline_forced():
            return False
        try:
            with socket.create_connection(('1.1.1.1', 53), timeout=0.6):
                return True
        except Exception:
            return False

    @classmethod
    def query_online_knowledge(cls, prompt: str) -> str:
        clean_prompt = prompt.strip()
        if clean_prompt.lower().rstrip("?!.") in cls.GREETINGS:
            return ""
        cleaned_topic = re.sub(r'^(?:what is|who is|explain|tell me about|define)\s+', '', clean_prompt, flags=re.IGNORECASE).strip()
        clean_q = urllib.parse.quote_plus(cleaned_topic if cleaned_topic else clean_prompt)
        try:
            url = f"https://api.duckduckgo.com/?q={clean_q}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SparkAssistant/4.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode())
                if data.get("AbstractText"):
                    return f"🌐 [Online DDG]\n{data['AbstractText']}"
        except Exception:
            pass
        try:
            wiki_slug = urllib.parse.quote(cleaned_topic.replace(" ", "_") if cleaned_topic else clean_prompt)
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_slug}"
            req = urllib.request.Request(wiki_url, headers={"User-Agent": "SparkAssistant/4.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode())
                if data.get("extract"):
                    return f"🌐 [Online Wiki]\n{data['extract']}"
        except Exception:
            pass
        return ""

    @classmethod
    def query_offline_ollama(cls, prompt: str, system_persona: str = "") -> str:
        cls.ensure_ollama_running()
        try:
            payload = {
                "model": cls.OLLAMA_MODEL,
                "prompt": f"{system_persona}\n\nUser: {prompt}\nAssistant:",
                "stream": False,
                "keep_alive": 0
            }
            req = urllib.request.Request(
                cls.OLLAMA_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                reply = data.get("response", "").strip()
                if reply:
                    return f"🤖 [Llama AI]\n{reply}"
        except Exception:
            pass
        return ""

    @classmethod
    def query(cls, prompt: str, system_persona: str = "") -> str:
        prompt_clean = prompt.strip()
        if not prompt_clean:
            return "Please enter a valid command or query."

        # 1. Agent Reach: YouTube URLs
        if "youtube.com" in prompt_clean or "youtu.be" in prompt_clean:
            yt_content = AgentReach.fetch_youtube_content(prompt_clean)
            if yt_content.startswith("[Agent Reach Error"):
                return yt_content
            summary_prompt = f"Summarize the main points and takeaways from this YouTube video data:\n\n{yt_content}"
            ai_summary = cls.query_offline_ollama(summary_prompt, system_persona)
            if ai_summary:
                return f"👁️ [Agent Reach: YouTube Analysis]\n{ai_summary}"
            return f"👁️ [Agent Reach: YouTube Data]\n{yt_content[:1200]}"

        # 2. Agent Reach: GitHub URLs
        if "github.com/" in prompt_clean:
            gh_info = AgentReach.fetch_github_repo(prompt_clean)
            ai_summary = cls.query_offline_ollama(f"Explain what this GitHub repo does based on this data:\n{gh_info}", system_persona)
            return f"👁️ [Agent Reach: GitHub]\n{gh_info}" + (f"\n\n{ai_summary}" if ai_summary else "")

        # 3. Agent Reach: Reddit URLs
        if "reddit.com/r/" in prompt_clean:
            rd_info = AgentReach.fetch_reddit_post(prompt_clean)
            return f"👁️ [Agent Reach: Reddit]\n{rd_info}"

        # 4. Context 7 Live Docs (/docs <lib>)
        if prompt_clean.lower().startswith("/docs "):
            lib_name = prompt_clean[6:].strip()
            return Context7Docs.fetch_pypi_docs(lib_name)

        # 5. Marketing Skills Engine (/pitch, /copy, /ad)
        if prompt_clean.lower().startswith(("/pitch ", "/copy ", "/ad ")):
            prefix, user_topic = prompt_clean.split(" ", 1)
            marketing_sys = (
                "You are an elite startup pitch coach and conversion copywriter. "
                "Provide a punchy Hook, Core Value Proposition, 3 Bullet Benefits, and a Call to Action."
            )
            ans = cls.query_offline_ollama(f"Create a high-converting {prefix[1:]} for: {user_topic}", marketing_sys)
            return ans if ans else "⚠️ Local Ollama is not responding. Ensure `llama3.2:1b` is installed (`ollama pull llama3.2:1b`)."

        # 6. Quick Math Evaluator
        safe_expr = re.sub(r'[^0-9\+\-\*\/\(\)\.\^ ]', '', prompt_clean)
        if safe_expr and any(c in safe_expr for c in "+-*/") and re.match(r'^[\d\s\+\-\*\/\(\)\.\^]+$', prompt_clean):
            try:
                res = eval(safe_expr.replace("^", "**"), {"__builtins__": None}, {})
                return f"🧮 Math Result: {res}"
            except Exception:
                pass

        # 7. Conversational Greetings
        if prompt_clean.lower().rstrip("?!.") in cls.GREETINGS:
            ollama_ans = cls.query_offline_ollama(prompt_clean, system_persona)
            if ollama_ans:
                return ollama_ans
            return "👋 Hey! SparkAssistant is ready. Tell me to `open <any app>`, `close <app>`, `play <song>`, `take screenshot`, or ask any question!"

        # 8. Local Llama AI (Primary brain for open-ended questions & tasks)
        ollama_ans = cls.query_offline_ollama(prompt_clean, system_persona)
        if ollama_ans:
            return ollama_ans

        # 9. Online Knowledge (DDG / Wiki fallback)
        if not cls.is_offline_forced() and cls.is_connected_to_internet():
            online_ans = cls.query_online_knowledge(prompt_clean)
            if online_ans:
                return online_ans

        # 10. Local SQLite FTS5 Knowledge Base
        local_db_ans = KnowledgeDatabase.query(prompt_clean)
        if local_db_ans:
            return f"🔒 [Offline DB]\n{local_db_ans}"

        return f"🤖 Local Ollama did not respond. Make sure Ollama is installed or type `google {prompt_clean}` to search the web."


# ==================== USER AUTH & AUDIT LOGS ====================

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users() -> dict:
    if not USER_DB_PATH.exists():
        initial = {
            ADMIN_USERNAME.lower(): {
                "display_name": ADMIN_USERNAME,
                "password_hash": hash_pw(ADMIN_DEFAULT_PASS),
                "is_admin": True,
                "persona": "Cyberpunk AI",
                "system_prompt": "You are SparkAssistant, an elite cybernetic AI companion. Be concise, technical, and sharp.",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        try:
            with open(USER_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(initial, f, indent=4)
        except Exception:
            pass
        return initial
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
        entry = f"[{timestamp}] USER: {user_tag} | PC: {pc_name} ({win_user}) | PROMPT: \"{query}\" | ACTION: {action}\n"
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

    @classmethod
    def read_all_logs(cls) -> list:
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


# ==================== UI COMPONENTS & DIALOGS ====================

class HoverButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class AnimatedToggle(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = True
        self._circle_position = 22.0
        self.anim = QPropertyAnimation(self, b"circle_position", self)
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    @pyqtProperty(float)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def isChecked(self):
        return self._checked

    def setChecked(self, value: bool):
        self._checked = bool(value)
        HybridAIEngine.force_offline = not self._checked
        self.anim.stop()
        self.anim.setEndValue(22.0 if self._checked else 2.0)
        self.anim.start()
        self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor("#22c55e") if self._checked else QColor("#334155")
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(int(self._circle_position), 2, 16, 16)
        p.end()


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.users = load_users()
        self.setWindowTitle("🔑 Change Profile Password")
        self.setFixedSize(360, 270)
        self.setStyleSheet("""
            QDialog { background-color: #0d0f17; color: #ffffff; }
            QLabel { color: #e8eaed; font-size: 12px; }
            QLineEdit, QComboBox { background-color: #141724; color: #ffffff; border: 1px solid #2b3044; border-radius: 6px; padding: 7px; }
            QPushButton { background-color: #1e293b; color: #8ab4f8; border: 1px solid #334155; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #334155; color: #ffffff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Select Profile:"))
        self.user_combo = QComboBox()
        for k, v in self.users.items():
            self.user_combo.addItem(v.get("display_name", k), k)
        layout.addWidget(self.user_combo)

        layout.addWidget(QLabel("Current Password:"))
        self.old_pw = QLineEdit()
        self.old_pw.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.old_pw)

        layout.addWidget(QLabel("New Password:"))
        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_pw)

        btn_row = QHBoxLayout()
        cancel_btn = HoverButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = HoverButton("Update Password")
        save_btn.clicked.connect(self.update_pw)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def update_pw(self):
        u_key = self.user_combo.currentData()
        old_p = self.old_pw.text().strip()
        new_p = self.new_pw.text().strip()
        if not new_p:
            QMessageBox.warning(self, "Error", "New password cannot be empty.")
            return
        if self.users[u_key].get("password_hash") != hash_pw(old_p):
            QMessageBox.critical(self, "Denied", "Current password is incorrect!")
            return
        self.users[u_key]["password_hash"] = hash_pw(new_p)
        save_users(self.users)
        QMessageBox.information(self, "Success", f"Password updated for {self.users[u_key].get('display_name')}!")
        self.accept()


class PluginsHubDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_command = ""
        self.setWindowTitle("🚀 Spark Plugins & Autonomous Task Hub")
        self.setFixedSize(470, 410)
        self.setStyleSheet("""
            QDialog { background-color: #0d0f17; color: #ffffff; }
            QLabel { color: #cbd5e1; font-size: 12px; }
            QPushButton { background-color: #141724; color: #8ab4f8; border: 1px solid #262c44; border-radius: 8px; padding: 10px; font-weight: bold; text-align: left; }
            QPushButton:hover { background-color: #1e2438; border-color: #4f6bff; color: #ffffff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        header = QLabel("<b>Select an AI Plugin or OS Task Action:</b>")
        header.setStyleSheet("color: #ffffff; font-size: 14px;")
        layout.addWidget(header)

        btn_open = HoverButton("🚀 Universal App Launcher: Open Any App, Folder, or Website")
        btn_open.clicked.connect(lambda: self.prompt_input("Open Anything", "Enter app, folder, or site name (e.g., chrome, vscode, downloads):", "open "))
        layout.addWidget(btn_open)

        btn_yt = HoverButton("👁️ Agent Reach: Summarize YouTube / GitHub / Reddit URL")
        btn_yt.clicked.connect(lambda: self.prompt_input("Agent Reach URL", "Paste a YouTube, GitHub, or Reddit link:", ""))
        layout.addWidget(btn_yt)

        btn_docs = HoverButton("📚 Context 7: Fetch Live Python Library Documentation")
        btn_docs.clicked.connect(lambda: self.prompt_input("Context 7 Docs", "Enter library name (e.g., pyqt6, opencv, mediapipe):", "/docs "))
        layout.addWidget(btn_docs)

        btn_pitch = HoverButton("📈 Marketing Engine: Generate Startup Pitch / Ad Copy")
        btn_pitch.clicked.connect(lambda: self.prompt_input("Marketing Engine", "Describe your product, club, or idea:", "/pitch "))
        layout.addWidget(btn_pitch)

        btn_cmd = HoverButton("💻 Run Custom PowerShell / Terminal Command")
        btn_cmd.clicked.connect(lambda: self.prompt_input("Terminal Runner", "Enter PowerShell/CMD command (e.g., ipconfig, dir):", "cmd "))
        layout.addWidget(btn_cmd)

        btn_stats = HoverButton("📊 Check Live System CPU / RAM / Top Processes")
        btn_stats.clicked.connect(lambda: self.trigger_direct("system status"))
        layout.addWidget(btn_stats)

    def prompt_input(self, title: str, label: str, prefix: str):
        text, ok = QInputDialog.getText(self, title, label)
        if ok and text.strip():
            self.selected_command = f"{prefix}{text.strip()}"
            self.accept()

    def trigger_direct(self, cmd: str):
        self.selected_command = cmd
        self.accept()


class ScratchpadDialog(QDialog):
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("📝 Spark Scratchpad Notes")
        self.resize(520, 430)
        self.setStyleSheet("""
            QDialog { background-color: #0d0f17; color: #ffffff; }
            QLineEdit, QTextEdit { background-color: #141724; color: #ffffff; border: 1px solid #2b3044; border-radius: 6px; padding: 8px; font-family: 'Consolas'; }
            QPushButton { background-color: #1e293b; color: #8ab4f8; border: 1px solid #334155; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #334155; color: #ffffff; }
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Jot down quick markdown notes, reminders, or code snippets:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Note Title...")
        layout.addWidget(self.title_input)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Type note content here...")
        layout.addWidget(self.content_input)

        btn_row = QHBoxLayout()
        save_btn = HoverButton("💾 Save Note")
        save_btn.clicked.connect(self.save)
        clear_btn = HoverButton("🗑️ Clear All Notes")
        clear_btn.clicked.connect(self.clear_all)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        self.notes_list = QTextEdit()
        self.notes_list.setReadOnly(True)
        self.notes_list.setPlaceholderText("Saved notes will appear here...")
        layout.addWidget(self.notes_list)
        self.load_notes()

    def save(self):
        t = self.title_input.text().strip()
        c = self.content_input.toPlainText().strip()
        if t and c:
            ScratchpadManager.save_note(self.username, t, c)
            self.title_input.clear()
            self.content_input.clear()
            self.load_notes()

    def clear_all(self):
        ScratchpadManager.clear_notes(self.username)
        self.load_notes()

    def load_notes(self):
        notes = ScratchpadManager.load_notes(self.username)
        txt = ""
        for title, content, tstamp in notes:
            txt += f"### {title} ({tstamp})\n{content}\n" + "-" * 38 + "\n"
        self.notes_list.setText(txt)


class PasswordPromptDialog(QDialog):
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.verified = False
        self.setWindowTitle(f"🔒 Password Required - {username}")
        self.setFixedSize(340, 190)
        self.setStyleSheet("""
            QDialog { background-color: #0d0f17; color: #ffffff; border: 1px solid #2b3a55; border-radius: 12px; }
            QLabel { color: #e8eaed; font-size: 13px; }
            QLineEdit { background-color: #141724; color: #ffffff; border: 1px solid #252a36; border-radius: 6px; padding: 8px; }
            QPushButton { background-color: #1e293b; color: #8ab4f8; border: 1px solid #334155; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #334155; color: #ffffff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel(f"Enter password for <b>{username}</b>:"))
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("Password...")
        self.pwd_input.returnPressed.connect(self.verify)
        layout.addWidget(self.pwd_input)

        btn_row = QHBoxLayout()
        cancel_btn = HoverButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        confirm_btn = HoverButton("Confirm")
        confirm_btn.clicked.connect(self.verify)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

    def verify(self):
        users = load_users()
        user_key = self.username.lower()
        if user_key in users and users[user_key].get("password_hash") == hash_pw(self.pwd_input.text().strip()):
            self.verified = True
            self.accept()
        else:
            QMessageBox.critical(self, "Access Denied", "Incorrect password!")
            self.pwd_input.clear()


class AuthDialog(QDialog):
    def __init__(self, pc_name: str, win_user: str, parent=None):
        super().__init__(parent)
        self.pc_name = pc_name
        self.win_user = win_user
        self.users = load_users()
        self.authenticated_user = None

        self.setWindowTitle("Spark Assistant - Create Profile")
        self.setFixedSize(380, 380)
        self.setStyleSheet("""
            QDialog { background-color: #0d0f17; color: #e8eaed; border-radius: 12px; }
            QLabel { color: #e8eaed; font-size: 12px; }
            QLineEdit, QComboBox { background-color: #141724; color: #ffffff; border: 1px solid #252a36; border-radius: 6px; padding: 6px; }
            QPushButton { background-color: #1e293b; color: #8ab4f8; border: 1px solid #334155; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #334155; color: #ffffff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("<b>Create New Spark Profile</b>")
        title.setStyleSheet("color: #8ab4f8; font-size: 15px;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        layout.addWidget(QLabel("Choose AI Vibe / Persona:"))
        self.persona_combo = QComboBox()
        self.persona_combo.addItems([
            "Cyberpunk AI",
            "Hacker / Developer",
            "Friendly Study Buddy",
            "Minimalist Professional",
            "Pirate Captain (Blox Fruits Vibe)"
        ])
        layout.addWidget(self.persona_combo)

        self.submit_btn = HoverButton("Create Profile")
        self.submit_btn.clicked.connect(self.handle_auth)
        layout.addWidget(self.submit_btn)

    def handle_auth(self):
        uname = self.username_input.text().strip()
        pwd = self.password_input.text().strip()
        if not uname or not pwd:
            return
        key = uname.lower()
        if key in self.users:
            QMessageBox.warning(self, "Exists", "User already registered.")
            return

        persona = self.persona_combo.currentText()
        prompts = {
            "Cyberpunk AI": "You are SparkAssistant, an elite cybernetic AI companion in a neon-drenched future. Be concise, technical, and edgy.",
            "Hacker / Developer": "You are SparkAssistant, an expert senior software engineer and ethical hacker. Give clean terminal code and precise diagnostics.",
            "Friendly Study Buddy": "You are SparkAssistant, a warm, patient, and cheerful study tutor. Explain concepts clearly and encouragingly.",
            "Minimalist Professional": "You are SparkAssistant, a highly structured executive assistant. Provide clean, professional bullet points.",
            "Pirate Captain (Blox Fruits Vibe)": "Ahoy! You be SparkAssistant, a fierce pirate captain exploring the seas. Talk with pirate slang!"
        }
        sys_prompt = prompts.get(persona, "You are SparkAssistant, an autonomous desktop companion.")

        self.users[key] = {
            "display_name": uname,
            "password_hash": hash_pw(pwd),
            "is_admin": False,
            "persona": persona,
            "system_prompt": sys_prompt,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_users(self.users)
        self.authenticated_user = uname
        self.accept()


class HotstarProfileSelector(QDialog):
    def __init__(self, pc_name: str, win_user: str, parent=None):
        super().__init__(parent)
        self.pc_name = pc_name
        self.win_user = win_user
        self.users = load_users()
        self.selected_user = None
        self.is_admin = False
        self.persona = ""
        self.system_prompt = ""

        self.setWindowTitle("Who is watching? - Spark Profiles")
        self.resize(660, 420)
        self.setStyleSheet("""
            QDialog { background-color: #0b0d14; color: #ffffff; }
            QLabel#Title { color: #ffffff; font-size: 22px; font-weight: bold; font-family: 'Segoe UI'; }
            QLabel#Sub { color: #9ca3af; font-size: 13px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 35, 40, 30)
        layout.setSpacing(18)

        title = QLabel("Who's watching Spark?", alignment=Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("Title")
        layout.addWidget(title)

        sub = QLabel(f"Device: {pc_name} ({win_user})", alignment=Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("Sub")
        layout.addWidget(sub)

        self.profiles_layout = QHBoxLayout()
        self.profiles_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.profiles_layout.setSpacing(25)
        layout.addLayout(self.profiles_layout)

        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        change_pw_btn = HoverButton("🔑 Change Password")
        change_pw_btn.setFixedSize(150, 32)
        change_pw_btn.setStyleSheet("""
            QPushButton { background-color: #141724; color: #8ab4f8; border: 1px solid #2b3a55; border-radius: 8px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #1e293b; color: #ffffff; }
        """)
        change_pw_btn.clicked.connect(self.open_change_pw)
        bottom_bar.addWidget(change_pw_btn)
        bottom_bar.addStretch()
        layout.addLayout(bottom_bar)

        self.populate_profiles()

    def open_change_pw(self):
        dlg = ChangePasswordDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.users = load_users()

    def populate_profiles(self):
        while self.profiles_layout.count():
            item = self.profiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for uname, udata in self.users.items():
            disp_name = udata.get("display_name", uname)
            is_adm = udata.get("is_admin", False)
            persona = udata.get("persona", "Default AI")
            avatar_char = disp_name[0].upper()

            card = QWidget()
            card.setFixedSize(115, 145)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(6)

            avatar = QLabel(avatar_char, alignment=Qt.AlignmentFlag.AlignCenter)
            avatar.setFixedSize(80, 80)
            avatar_bg = "#2563eb" if is_adm else "#374151"
            avatar.setStyleSheet(f"background-color: {avatar_bg}; color: #ffffff; font-size: 30px; font-weight: bold; border-radius: 40px; border: 2px solid #4b5563;")
            card_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)

            lbl = QLabel(disp_name, alignment=Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #e5e7eb; font-size: 13px; font-weight: 600;")
            card_layout.addWidget(lbl)

            vibe_lbl = QLabel(persona, alignment=Qt.AlignmentFlag.AlignCenter)
            vibe_lbl.setStyleSheet("color: #60a5fa; font-size: 10px;")
            card_layout.addWidget(vibe_lbl)

            card.mousePressEvent = lambda event, u=disp_name, adm=is_adm, p=persona, sp=udata.get("system_prompt", ""): self.select_profile(u, adm, p, sp)
            self.profiles_layout.addWidget(card)

        add_card = QWidget()
        add_card.setFixedSize(115, 145)
        add_card.setCursor(Qt.CursorShape.PointingHandCursor)
        add_layout = QVBoxLayout(add_card)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.setSpacing(6)

        add_icon = QLabel("+", alignment=Qt.AlignmentFlag.AlignCenter)
        add_icon.setFixedSize(80, 80)
        add_icon.setStyleSheet("background-color: #1f2937; color: #9ca3af; font-size: 34px; border-radius: 40px; border: 2px dashed #4b5563;")
        add_layout.addWidget(add_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        add_lbl = QLabel("Add Profile", alignment=Qt.AlignmentFlag.AlignCenter)
        add_lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
        add_layout.addWidget(add_lbl)

        add_card.mousePressEvent = lambda e: self.open_register_dialog()
        self.profiles_layout.addWidget(add_card)

    def select_profile(self, username: str, is_admin: bool, persona: str, system_prompt: str):
        pwd_dlg = PasswordPromptDialog(username, self)
        if pwd_dlg.exec() != QDialog.DialogCode.Accepted or not pwd_dlg.verified:
            return

        self.selected_user = username
        self.is_admin = is_admin
        self.persona = persona
        self.system_prompt = system_prompt
        self.accept()

    def open_register_dialog(self):
        reg_dlg = AuthDialog(self.pc_name, self.win_user, parent=self)
        if reg_dlg.exec() == QDialog.DialogCode.Accepted:
            self.users = load_users()
            self.populate_profiles()


class AdminPanelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Shield Admin Console - Activity & Security")
        self.resize(860, 480)
        self.setStyleSheet("""
            QDialog { background-color: #0b0d14; color: #ffffff; }
            QLabel { color: #8ab4f8; font-size: 13px; }
            QTableWidget { background-color: #08090f; color: #e8eaed; border: 1px solid #1f2438; }
            QHeaderView::section { background-color: #141724; color: #8ab4f8; padding: 6px; }
            QPushButton { background-color: #1e293b; color: #8ab4f8; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #334155; color: #ffffff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("<b>System Activity Audit Logs</b>"))
        top_row.addStretch()

        pw_btn = HoverButton("🔑 Change Password")
        pw_btn.clicked.connect(lambda: ChangePasswordDialog(self).exec())
        top_row.addWidget(pw_btn)

        clr_btn = HoverButton("🗑️ Clear Audit Logs")
        clr_btn.clicked.connect(self.clear_all)
        top_row.addWidget(clr_btn)
        layout.addLayout(top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "User & PC", "Prompt", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        self.populate_logs()

    def clear_all(self):
        AuditLogger.clear_logs()
        self.populate_logs()

    def populate_logs(self):
        raw = AuditLogger.read_all_logs()
        self.table.setRowCount(0)
        pattern = re.compile(r'\[(.*?)\] USER:\s*(.*?)\s*\|\s*PC:\s*(.*?)\s*\|\s*PROMPT:\s*\"(.*?)\"\s*\|\s*ACTION:\s*(.*)')
        for line in reversed(raw):
            m = pattern.match(line)
            r = self.table.rowCount()
            self.table.insertRow(r)
            if m:
                tstamp, user, pc, prompt, action = m.groups()
                self.table.setItem(r, 0, QTableWidgetItem(tstamp))
                self.table.setItem(r, 1, QTableWidgetItem(f"{user} ({pc})"))
                self.table.setItem(r, 2, QTableWidgetItem(prompt))
                self.table.setItem(r, 3, QTableWidgetItem(action))
            else:
                self.table.setItem(r, 0, QTableWidgetItem(line))


# ==================== MAIN ASSISTANT WINDOW ====================

class SolidCardFrame(QFrame):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#0d0f17"))
        p.setPen(QPen(QColor("#232942"), 1.5))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 14, 14)
        p.end()


class GeminiDesktopAssistant(QMainWindow):
    def __init__(self, active_user: str, is_admin: bool, persona: str, system_prompt: str, pc_name: str, win_user: str):
        super().__init__()
        self.active_user = active_user
        self.is_admin = is_admin
        self.persona = persona
        self.system_prompt = system_prompt
        self.pc_name = pc_name
        self.win_user = win_user
        self.is_compact = True
        self.drag_pos = QPoint()
        self.thinking_label = None

        # Silently ensure Ollama daemon is active in the background
        HybridAIEngine.ensure_ollama_running()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setStyleSheet("""
            QMainWindow { background-color: #0d0f17; }
            QScrollArea { background-color: #0d0f17; border: none; }
            QScrollBar:vertical { background-color: #0d0f17; width: 6px; margin: 4px 2px 4px 0px; border-radius: 3px; }
            QScrollBar::handle:vertical { background-color: #252b3d; min-height: 25px; border-radius: 3px; }
            QScrollBar::handle:vertical:hover { background-color: #3b4259; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.container = SolidCardFrame(self)
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(12, 10, 12, 10)
        self.main_layout.setSpacing(8)

        # Top Navigation Bar
        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(2, 2, 2, 2)
        self.top_bar.setSpacing(4)

        self.title_lbl = QLabel(f"✦ Spark ({self.active_user})")
        self.title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #8ab4f8; background: transparent;")
        self.top_bar.addWidget(self.title_lbl)
        self.top_bar.addStretch()

        self.plugins_btn = HoverButton("🚀 Plugins")
        self.plugins_btn.setFixedSize(64, 22)
        self.plugins_btn.setToolTip("Open Universal App Launcher, Agent Reach & Context 7 Hub")
        self.plugins_btn.setStyleSheet("QPushButton { background-color: #1e3a8a; color: #bfdbfe; border: 1px solid #3b82f6; border-radius: 5px; font-size: 9px; font-weight: bold; } QPushButton:hover { background-color: #2563eb; color: #ffffff; }")
        self.plugins_btn.clicked.connect(self.open_plugins_hub)
        self.top_bar.addWidget(self.plugins_btn)

        self.ocr_btn = HoverButton("📸 OCR")
        self.ocr_btn.setFixedSize(48, 22)
        self.ocr_btn.setToolTip("Capture Screen & Read Text via OCR")
        self.ocr_btn.setStyleSheet("QPushButton { background-color: #3b0764; color: #e9d5ff; border: 1px solid #7e22ce; border-radius: 5px; font-size: 9px; font-weight: bold; } QPushButton:hover { background-color: #6b21a8; color: #ffffff; }")
        self.ocr_btn.clicked.connect(self.trigger_ocr)
        self.top_bar.addWidget(self.ocr_btn)

        self.clipboard_btn = HoverButton("📋 AI Tools")
        self.clipboard_btn.setFixedSize(64, 22)
        self.clipboard_btn.setToolTip("Instant Clipboard AI Actions")
        self.clipboard_btn.setStyleSheet("QPushButton { background-color: #064e3b; color: #a7f3d0; border: 1px solid #047857; border-radius: 5px; font-size: 9px; font-weight: bold; } QPushButton:hover { background-color: #047857; color: #ffffff; }")
        self.clipboard_btn.clicked.connect(self.show_clipboard_menu)
        self.top_bar.addWidget(self.clipboard_btn)

        self.notes_btn = HoverButton("📝 Notes")
        self.notes_btn.setFixedSize(54, 22)
        self.notes_btn.setToolTip("Open Scratchpad Notes")
        self.notes_btn.setStyleSheet("QPushButton { background-color: #172554; color: #93c5fd; border: 1px solid #1d4ed8; border-radius: 5px; font-size: 9px; font-weight: bold; } QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }")
        self.notes_btn.clicked.connect(lambda: ScratchpadDialog(self.active_user, self).exec())
        self.top_bar.addWidget(self.notes_btn)

        self.switch_btn = HoverButton("👥 Switch")
        self.switch_btn.setFixedSize(58, 22)
        self.switch_btn.setToolTip("Switch Profile or Change Password")
        self.switch_btn.setStyleSheet("QPushButton { background-color: #1e1b4b; color: #c7d2fe; border: 1px solid #3730a3; border-radius: 5px; font-size: 9px; font-weight: bold; } QPushButton:hover { background-color: #3730a3; color: #ffffff; }")
        self.switch_btn.clicked.connect(self.switch_profile)
        self.top_bar.addWidget(self.switch_btn)

        self.clear_btn = HoverButton("🗑️")
        self.clear_btn.setFixedSize(24, 22)
        self.clear_btn.setToolTip("Clear Chat Screen")
        self.clear_btn.setStyleSheet("QPushButton { background-color: #141724; color: #94a3b8; border: 1px solid #2b3044; border-radius: 5px; font-size: 10px; } QPushButton:hover { background-color: #2b3044; color: #ffffff; }")
        self.clear_btn.clicked.connect(self.clear_chat_bubbles)
        self.top_bar.addWidget(self.clear_btn)

        self.offline_toggle = AnimatedToggle()
        self.offline_toggle.setToolTip("Green: Online Mode | Gray: Offline Mode")
        self.top_bar.addWidget(self.offline_toggle)

        if self.is_admin:
            self.admin_btn = HoverButton("⚡ Admin")
            self.admin_btn.setFixedSize(54, 22)
            self.admin_btn.setStyleSheet("QPushButton { background-color: #151820; color: #8ab4f8; border-radius: 5px; border: 1px solid #2b3a55; font-size: 9px; font-weight: bold; } QPushButton:hover { background-color: #1e293b; color: #ffffff; }")
            self.admin_btn.clicked.connect(self.open_admin_hub)
            self.top_bar.addWidget(self.admin_btn)

        ctrl_style = "QPushButton { background-color: #141724; color: #d4d4d8; border: 1px solid #2b3044; border-radius: 5px; font-size: 10px; } QPushButton:hover { background-color: #2b3044; color: #ffffff; }"

        self.expand_btn = HoverButton("▲")
        self.expand_btn.setFixedSize(22, 22)
        self.expand_btn.setStyleSheet(ctrl_style)
        self.expand_btn.clicked.connect(self.toggle_compact_mode)
        self.top_bar.addWidget(self.expand_btn)

        min_btn = HoverButton("—")
        min_btn.setFixedSize(22, 22)
        min_btn.setStyleSheet(ctrl_style)
        min_btn.clicked.connect(self.showMinimized)
        self.top_bar.addWidget(min_btn)

        exit_btn = HoverButton("✕")
        exit_btn.setFixedSize(22, 22)
        exit_btn.setStyleSheet("QPushButton { background-color: #141724; color: #fca5a5; border: 1px solid #7f1d1d; border-radius: 5px; font-size: 10px; } QPushButton:hover { background-color: #7f1d1d; color: #ffffff; }")
        exit_btn.clicked.connect(QApplication.instance().quit)
        self.top_bar.addWidget(exit_btn)

        # Chat Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #0d0f17;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(4, 4, 12, 4)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_container)

        # Input Bar
        self.input_container = QFrame()
        self.input_container.setObjectName("InputBar")
        self.input_container.setStyleSheet("QFrame#InputBar { background-color: #141724; border: 1px solid #252b42; border-radius: 17px; }")
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(14, 4, 6, 4)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Try 'open chrome', 'close notepad', 'play lofi', 'take screenshot', or ask anything...")
        self.input_field.setStyleSheet("background: transparent; color: #ffffff; border: none;")
        self.input_field.returnPressed.connect(self.send_prompt)

        send_btn = HoverButton("↵")
        send_btn.setFixedSize(26, 26)
        send_btn.setStyleSheet("QPushButton { background-color: #8ab4f8; color: #050505; border-radius: 13px; font-weight: bold; } QPushButton:hover { background-color: #bfdbfe; }")
        send_btn.clicked.connect(self.send_prompt)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)

        self.main_layout.addLayout(self.top_bar)
        self.main_layout.addWidget(self.scroll, 1)
        self.main_layout.addWidget(self.input_container)

        self.setCentralWidget(self.container)
        self.apply_mode_geometry()

        self.append_bubble(
            "assistant",
            f"Welcome, {self.active_user}! [{self.persona}]\n"
            f"• Type `open <any app/website/folder>` or `close <app>`\n"
            f"• Type `play <song>`, `take screenshot`, `create folder <name>`, or `top processes`"
        )

    def clear_chat_bubbles(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
            elif item.widget():
                item.widget().deleteLater()
        self.append_bubble("assistant", "🧹 Chat cleared. Ready for your next command.")

    def open_plugins_hub(self):
        dlg = PluginsHubDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_command:
            self.input_field.setText(dlg.selected_command)
            self.send_prompt()

    def trigger_ocr(self):
        if self.is_compact:
            self.toggle_compact_mode()
        self.append_bubble("user", "📸 [Capture Screen & Run OCR]")
        text = ScreenOCR.capture_and_read()
        self.append_bubble("assistant", f"📸 [OCR Extracted Text]:\n{text}")
        if "Error" not in text and "No legible" not in text:
            self.run_background_query(f"Explain and analyze this screen text:\n{text}")

    def show_clipboard_menu(self):
        if not pyperclip:
            QMessageBox.warning(self, "Missing Library", "Install pyperclip (`pip install pyperclip`).")
            return
        clip = pyperclip.paste().strip()
        if not clip:
            QMessageBox.information(self, "Empty", "Your Windows clipboard is currently empty.")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("📋 Clipboard AI Tool Hub")
        msg.setText(f"Clipboard preview: \"{clip[:60]}...\"\n\nSelect AI action:")
        sum_btn = msg.addButton("Summarize", QMessageBox.ButtonRole.ActionRole)
        fix_btn = msg.addButton("Fix Bug / Code", QMessageBox.ButtonRole.ActionRole)
        trans_btn = msg.addButton("Translate to English", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        prompt = ""
        if clicked == sum_btn:
            prompt = f"Summarize this text concisely:\n{clip}"
        elif clicked == fix_btn:
            prompt = f"Fix any bugs or issues in this code/text and explain the fix:\n{clip}"
        elif clicked == trans_btn:
            prompt = f"Translate this text into fluent English:\n{clip}"

        if prompt:
            if self.is_compact:
                self.toggle_compact_mode()
            self.append_bubble("user", prompt)
            self.run_background_query(prompt)

    def open_admin_hub(self):
        pwd_dlg = PasswordPromptDialog(self.active_user, self)
        if pwd_dlg.exec() != QDialog.DialogCode.Accepted or not pwd_dlg.verified:
            return
        AdminPanelDialog(self).exec()

    def switch_profile(self):
        selector = HotstarProfileSelector(self.pc_name, self.win_user, self)
        if selector.exec() == QDialog.DialogCode.Accepted and selector.selected_user:
            self.active_user = selector.selected_user
            self.is_admin = selector.is_admin
            self.persona = selector.persona
            self.system_prompt = selector.system_prompt
            self.title_lbl.setText(f"✦ Spark ({self.active_user})")
            self.clear_chat_bubbles()

    def apply_mode_geometry(self):
        screen = QApplication.primaryScreen().geometry()
        if self.is_compact:
            self.scroll.hide()
            self.expand_btn.setText("▲")
            self.resize(650, 82)
            self.move((screen.width() - 650) // 2, 16)
        else:
            self.scroll.show()
            self.expand_btn.setText("▼")
            self.resize(760, 520)
            self.move((screen.width() - 760) // 2, 40)

    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        self.apply_mode_geometry()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_pos)

    def append_bubble(self, role: str, text: str) -> QLabel:
        row = QHBoxLayout()
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFont(QFont("Segoe UI", 10))
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setMaximumWidth(490 if role == "user" else 550)
        bubble.setStyleSheet(
            f"QLabel {{ background-color: {'#181c2c' if role == 'user' else '#101420'}; "
            f"color: {'#ffffff' if role == 'user' else '#93c5fd'}; "
            f"border: 1px solid {'#2e3650' if role == 'user' else '#1e293b'}; "
            f"border-radius: 12px; padding: 10px 14px; }}"
        )
        if role == "user":
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)
        QApplication.processEvents()
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        return bubble

    def send_prompt(self):
        query = self.input_field.text().strip()
        if not query:
            return
        self.input_field.clear()
        if self.is_compact:
            self.toggle_compact_mode()
        self.append_bubble("user", query)
        AuditLogger.log(self.active_user, self.pc_name, self.win_user, query, "TASK_TRIGGERED")

        p_low = query.lower()
        if p_low in ("clear", "/clear", "cls"):
            self.clear_chat_bubbles()
            return

        if p_low in ("system status", "check ram", "pc specs"):
            self.append_bubble("assistant", SystemMonitor.get_stats())
            return

        if p_low.startswith("remind me ") or p_low.startswith("add reminder "):
            task = re.sub(r'^(?:remind me to|remind me|add reminder)\s+', '', query, flags=re.IGNORECASE).strip()
            res = ReminderManager.add_reminder(self.active_user, task)
            self.append_bubble("assistant", f"⏰ [Reminder Manager]\n{res}")
            return

        if p_low in ("show reminders", "my reminders", "list reminders"):
            rems = ReminderManager.get_reminders(self.active_user)
            txt = "⏰ Active Reminders:\n" + "\n".join([f"• {r[0]} (Due: {r[1]})" for r in rems]) if rems else "No active reminders."
            self.append_bubble("assistant", txt)
            return

        # Check Universal Autonomous Task Engine first
        task_output = AutonomousTaskEngine.execute_If_Matched(query, self.active_user)
        if task_output:
            self.append_bubble("assistant", task_output)
            return

        self.run_background_query(query)

    def run_background_query(self, query: str):
        self.thinking_label = self.append_bubble("assistant", "⏳ Processing request...")
        self.worker = TaskExecutionWorker(query, self.system_prompt)
        self.worker.task_completed.connect(self.on_task_finished)
        self.worker.start()

    def on_task_finished(self, result_text: str):
        if self.thinking_label is not None:
            self.thinking_label.setText(result_text)
            self.thinking_label = None
            QApplication.processEvents()
            self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        else:
            self.append_bubble("assistant", result_text)


class TaskExecutionWorker(QThread):
    task_completed = pyqtSignal(str)

    def __init__(self, prompt: str, system_prompt: str):
        super().__init__()
        self.prompt = prompt
        self.system_prompt = system_prompt

    def run(self):
        ans = HybridAIEngine.query(self.prompt, self.system_prompt)
        self.task_completed.emit(ans)


if __name__ == "__main__":
    mp.freeze_support()
    app = QApplication(sys.argv)
    pc = socket.gethostname()
    win_usr = os.environ.get("USERNAME", "user")

    selector = HotstarProfileSelector(pc, win_usr)
    if selector.exec() == QDialog.DialogCode.Accepted and selector.selected_user:
        window = GeminiDesktopAssistant(
            selector.selected_user,
            selector.is_admin,
            selector.persona,
            selector.system_prompt,
            pc,
            win_usr
        )
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


# ==========================================
# SPARKVAULT INTELLIGENCE INTEGRATION
# ==========================================
try:
    from fast_assistant import query_vault, search_offline_vault, is_online
    
    def handle_vault_command(user_cmd):
        """Processes AI and offline-database tasks inside SparkAssistant."""
        cmd_lower = user_cmd.strip().lower()
        
        if cmd_lower.startswith("ask "):
            prompt = user_cmd[4:].strip()
            print("\n[SparkVault 3B Engine Querying...]")
            query_vault(prompt, model="qwen2.5:3b", stream=True)
            return True
            
        elif cmd_lower.startswith("code "):
            prompt = user_cmd[5:].strip()
            print("\n[SparkVault 7B Coder Generating...]")
            query_vault(prompt, model="spark-coder:7b", stream=True)
            return True
            
        elif cmd_lower.startswith("r1 "):
            prompt = user_cmd[3:].strip()
            print("\n[DeepSeek-R1 Logical Synthesis...]")
            query_vault(prompt, model="deepseek-r1:7b", stream=True)
            return True
            
        elif cmd_lower.startswith("vault-search "):
            kw = user_cmd[13:].strip()
            link, text = search_offline_vault(kw)
            if link:
                print(f"\n[Found in Database]: http://localhost:8088{link}")
                print(f"[Excerpt]: {text[:300]}...\n")
            else:
                print("\n[No direct match found in 20 offline archives]\n")
            return True
            
        return False
        
except ImportError:
    def handle_vault_command(user_cmd):
        return False

# ========================================================
# SPARKASSISTANT NATIVE VAULT ENGINE (HYBRID RAG + OLLAMA)
# ========================================================
import socket
import string
import urllib.request
import urllib.parse
import json
import re
import requests
from bs4 import BeautifulSoup

VAULT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLLAMA_API = "http://localhost:11434/api/generate"
KIWIX_API = "http://localhost:8088"
STOP_WORDS = {"how", "do", "i", "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is", "can", "what", "why", "with", "write", "an", "essay"}

def check_internet(timeout=1.0):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("1.1.1.1", 53))
        return True
    except Exception:
        return False

def get_keywords(query):
    words = re.findall(r'\b[a-zA-Z0-9_+#\.]+\b', query)
    cleaned = [w for w in words if w.lower() not in STOP_WORDS]
    return " ".join(cleaned[:5]) if cleaned else query

def search_kiwix(query):
    try:
        url = f"{KIWIX_API}/search?pattern={urllib.parse.quote(get_keywords(query))}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            html = res.read().decode('utf-8', errors='ignore')
        matches = re.findall(r'href="(/[^"]+/[^"]+)"', html)
        clean = [m for m in matches if not any(x in m for x in ['.css', '.js', '.png', '.ico', '/skin/'])]
        if clean:
            top_link = clean[0]
            art_req = urllib.request.Request(f"{KIWIX_API}{top_link}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(art_req, timeout=1.5) as art_res:
                soup = BeautifulSoup(art_res.read().decode('utf-8', errors='ignore'), "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                return top_link, " ".join(soup.stripped_strings)[:1500]
        return None, ""
    except Exception:
        return None, ""

def search_duckduckgo(query):
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(get_keywords(query))}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=2.0) as res:
            soup = BeautifulSoup(res.read().decode('utf-8', errors='ignore'), "html.parser")
            snippets = [s.get_text() for s in soup.find_all("a", class_="result__snippet")[:2]]
            return " ".join(snippets)[:1200]
    except Exception:
        return ""

def spark_generate(prompt, model="qwen2.5:3b"):
    """Core function to query the local neural models with RAG context."""
    link, context = search_kiwix(prompt)
    source = f"136GB HDD Database ({link})" if context else ""
    
    if not context and check_internet():
        context = search_duckduckgo(prompt)
        if context:
            source = "Live Web Search"
            
    full_prompt = (
        f"Context from {source}:\n\"\"\"{context}\"\"\"\n\n"
        f"Instruction: Use the context above to deliver an accurate, well-structured response.\n"
        f"User Prompt: {prompt}"
    ) if context else prompt

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": True,
        "options": {"num_predict": 750, "num_ctx": 2048, "temperature": 0.3}
    }
    try:
        res = requests.post(OLLAMA_API, json=payload, stream=True, timeout=None)
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode('utf-8'))
                print(chunk.get("response", ""), end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\n[Ollama Engine Error]: {e}\n")

def process_sparkassistant_command(user_text):
    """Router for SparkAssistant voice/text commands."""
    cmd = user_text.strip()
    cmd_lower = cmd.lower()
    
    if cmd_lower.startswith("ask "):
        spark_generate(cmd[4:].strip(), model="qwen2.5:3b")
        return True
    elif cmd_lower.startswith("code "):
        spark_generate(cmd[5:].strip(), model="spark-coder:7b")
        return True
    elif cmd_lower.startswith("r1 "):
        spark_generate(cmd[3:].strip(), model="deepseek-r1:7b")
        return True
    return False
