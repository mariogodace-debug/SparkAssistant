# -*- coding: utf-8 -*-
import sys
import os

# ----------------- FIX NOCONSOLE MULTIPROCESSING STREAMS -----------------
# Prevents AttributeError: 'NoneType' object has no attribute 'write'
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

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
import math
import multiprocessing as mp
import queue
from threading import Event, Lock, Thread, current_thread
from urllib.parse import quote_plus
import numpy as np

# Safe dynamic vision & input imports
cv2 = None
mp_mediapipe = None
sr = None
keyboard = None

try:
    import cv2
    import mediapipe as mp_mediapipe
    import speech_recognition as sr
    import keyboard
except ImportError:
    pass

from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QLabel, 
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QScrollArea, QFrame, QDialog, QMessageBox, QRadioButton, 
    QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)

# ============================================================
# WINDOWS DPI & SCREEN SETUP
# ============================================================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32
screen_w = max(1, user32.GetSystemMetrics(0))
screen_h = max(1, user32.GetSystemMetrics(1))

# ============================================================
# WIN32 FAST INPUT CONSTANTS & HELPERS
# ============================================================
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
VK_F4 = 0x73
KEYEVENTF_KEYUP = 0x0002

def clamp(val, min_val, max_val):
    return max(min_val, min(max_val, val))

def fast_move(x, y):
    cx = int(clamp(x, 0, screen_w - 1))
    cy = int(clamp(y, 0, screen_h - 1))
    user32.SetCursorPos(cx, cy)

def fast_click():
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def fast_right_click():
    user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

def fast_scroll(amount):
    if amount:
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(amount), 0)

def send_alt_f4():
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(VK_F4, 0, 0, 0)
    user32.keybd_event(VK_F4, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)

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
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    return True

# ============================================================
# APP CONFIGURATION
# ============================================================
APP_NAME = "SparkAssistant"
GITHUB_REPO = "mariogodace-debug/SparkAssistant"

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

def enable_windows_startup():
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
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
    except Exception:
        pass

# ============================================================
# SAFE CAMERA AND VISION ENGINE
# ============================================================
class CameraStream:
    def __init__(self, preferred_index=0):
        self.preferred_index = preferred_index
        self.cap = None
        self.thread = None
        self.stop_event = Event()
        self.lock = Lock()
        self.frame = None
        self.running = False

    def start(self):
        if cv2 is None:
            raise RuntimeError("OpenCV not installed.")
        
        # Test default webcam indices safely
        opened = False
        for idx in [self.preferred_index, 0, 1]:
            for backend in [cv2.CAP_DSHOW, cv2.CAP_ANY]:
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.cap = cap
                        opened = True
                        break
                    cap.release()
            if opened:
                break

        if not opened:
            raise RuntimeError("NO_CAMERA_FOUND")

        self.stop_event.clear()
        self.running = True
        self.thread = Thread(target=self._reader, name="CameraWorker", daemon=True)
        self.thread.start()
        return self

    def _reader(self):
        while not self.stop_event.is_set() and self.cap is not None:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.005)
                continue
            with self.lock:
                self.frame = frame
        self.running = False

    def read(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def release(self):
        self.stop_event.set()
        cap = self.cap
        self.cap = None

        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

        thread = self.thread
        if thread is not None and thread.is_alive() and thread is not current_thread():
            thread.join(timeout=1.0)

        self.thread = None
        with self.lock:
            self.frame = None
        self.running = False

def voice_worker(command_queue, stop_event):
    if sr is None:
        return
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.5
    recognizer.phrase_threshold = 0.2
    recognizer.non_speaking_duration = 0.3

    try:
        microphone = sr.Microphone()
    except Exception:
        return

    try:
        with microphone as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
            except Exception:
                pass

            while not stop_event.is_set():
                try:
                    audio = recognizer.listen(source, timeout=0.5, phrase_time_limit=4)
                except sr.WaitTimeoutError:
                    continue
                except Exception:
                    time.sleep(0.05)
                    continue

                if stop_event.is_set():
                    break

                try:
                    text = recognizer.recognize_google(audio).lower().strip()
                except Exception:
                    continue

                wake_words = (
                    "hey computer", "hey mouse", "computer", "mouse",
                    "assistant", "hey jarvis", "hi jarvis", "jarvis"
                )

                for w in wake_words:
                    text = text.replace(w, "").strip()

                if not text:
                    continue

                try:
                    command_queue.put_nowait(text)
                except queue.Full:
                    pass
    except Exception:
        return

def handle_voice_command(cmd):
    cmd = cmd.lower().strip()
    if not cmd:
        return ""

    if cmd.startswith("youtube ") or cmd == "youtube":
        q = cmd[8:].strip() if cmd.startswith("youtube ") else ""
        url = f"https://www.youtube.com/results?search_query={quote_plus(q)}" if q else "https://www.youtube.com"
        webbrowser.open(url)
        return f"YouTube: {q}" if q else "Opening YouTube"

    if cmd.startswith("google ") or cmd == "google":
        q = cmd[7:].strip() if cmd.startswith("google ") else ""
        url = f"https://www.google.com/search?q={quote_plus(q)}" if q else "https://www.google.com"
        webbrowser.open(url)
        return f"Google: {q}" if q else "Opening Google"

    if cmd in ("close", "close window", "close this", "exit window"):
        send_alt_f4()
        return "Closing Window"

    if cmd in ("open browser", "browser"):
        webbrowser.open("https://www.google.com")
        return "Opening Browser"

    return f"Voice: {cmd}"

def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def classify_fingers(points):
    wrist = points[0]
    index_ext = distance(points[8], wrist) > distance(points[6], wrist)
    middle_ext = distance(points[12], wrist) > distance(points[10], wrist)
    ring_ext = distance(points[16], wrist) > distance(points[14], wrist)
    pinky_ext = distance(points[20], wrist) > distance(points[18], wrist)

    palm_scale = max(distance(wrist, points[9]), 1.0)
    thumb_index_dist = distance(points[4], points[6]) / palm_scale

    return index_ext, middle_ext, ring_ext, pinky_ext, thumb_index_dist

FINGER_BONES = [
    ([(0, 1), (1, 2), (2, 3), (3, 4)], (0, 180, 255)),
    ([(0, 5), (5, 6), (6, 7), (7, 8)], (255, 230, 0)),
    ([(9, 10), (10, 11), (11, 12)],    (120, 230, 0)),
    ([(13, 14), (14, 15), (15, 16)],   (40, 140, 255)),
    ([(0, 17), (17, 18), (18, 19), (19, 20)], (255, 60, 200)),
    ([(5, 9), (9, 13), (13, 17)],      (130, 130, 150)),
]

def draw_glow_skeleton(frame, points):
    for bones, col in FINGER_BONES:
        glow_col = tuple(max(0, int(c / 3)) for c in col)
        for a, b in bones:
            cv2.line(frame, points[a], points[b], glow_col, 5, cv2.LINE_AA)
        for a, b in bones:
            cv2.line(frame, points[a], points[b], col, 1, cv2.LINE_AA)

    for p in points:
        cv2.circle(frame, p, 4, (20, 20, 20), -1, cv2.LINE_AA)
        cv2.circle(frame, p, 2, (255, 255, 255), -1, cv2.LINE_AA)

def draw_reticle(frame, center, color, radius=18):
    x, y = int(center[0]), int(center[1])
    cv2.circle(frame, (x, y), radius, color, 2, cv2.LINE_AA)
    cv2.circle(frame, (x, y), radius + 5, tuple(max(0, int(c / 3)) for c in color), 1, cv2.LINE_AA)
    arm = radius + 8
    cv2.line(frame, (x - arm, y), (x - radius - 2, y), color, 1, cv2.LINE_AA)
    cv2.line(frame, (x + radius + 2, y), (x + arm, y), color, 1, cv2.LINE_AA)
    cv2.line(frame, (x, y - arm), (x, y - radius - 2), color, 1, cv2.LINE_AA)
    cv2.line(frame, (x, y + radius + 2), (x, y + arm), color, 1, cv2.LINE_AA)

def draw_hud(frame, gesture, sensitivity, status):
    overlay = frame.copy()
    cv2.rectangle(overlay, (15, 15), (340, 135), (10, 10, 18), -1)
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

    cv2.putText(frame, "VIRTUAL MOUSE PRO", (30, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"GESTURE: {gesture.upper()}", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 220, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, f"SPEED: {sensitivity:.1f}x", (30, 94), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 255, 180), 1, cv2.LINE_AA)
    cv2.putText(frame, "[ / ] SPEED    Q / ESC EXIT", (30, 117), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 190), 1, cv2.LINE_AA)

    if status:
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (w - 310, 20), (w - 20, 58), (10, 10, 18), -1)
        cv2.putText(frame, status[:32], (w - 295, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

def virtual_mouse_process_worker(shutdown_event, error_queue):
    if cv2 is None or mp_mediapipe is None:
        error_queue.put("MISSING_DEPS")
        return

    sensitivity = 1.0
    camera = None
    hands = None
    voice_process = None
    voice_stop = None
    voice_queue = None

    last_cursor_pos = None
    last_scroll_y = None
    scroll_accumulator = 0.0

    left_gesture_active = False
    right_gesture_active = False
    last_left_click_time = 0.0
    last_right_click_time = 0.0

    click_interval = max(0.2, min(0.6, user32.GetDoubleClickTime() / 1000.0))
    status_text = ""
    status_until = 0.0

    try:
        try:
            camera = CameraStream(preferred_index=0).start()
        except RuntimeError:
            error_queue.put("NO_CAMERA")
            return

        hands = mp_mediapipe.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )

        voice_stop = mp.Event()
        voice_queue = mp.Queue(maxsize=20)
        voice_process = mp.Process(target=voice_worker, args=(voice_queue, voice_stop), daemon=True)
        try:
            voice_process.start()
        except Exception:
            voice_process = None

        def inc_speed():
            nonlocal sensitivity
            sensitivity = min(2.5, round(sensitivity + 0.1, 1))

        def dec_speed():
            nonlocal sensitivity
            sensitivity = max(0.4, round(sensitivity - 0.1, 1))

        if keyboard is not None:
            try:
                keyboard.add_hotkey("]", inc_speed)
                keyboard.add_hotkey("[", dec_speed)
            except Exception:
                pass

        cv2.namedWindow("Virtual Mouse Pro", cv2.WINDOW_NORMAL)

        while not shutdown_event.is_set():
            frame = camera.read()
            if frame is None:
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break
                continue

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            gesture = "none"
            now = time.perf_counter()

            if now >= status_until:
                status_text = ""

            if results.multi_hand_landmarks:
                hand = results.multi_hand_landmarks[0]
                points = [(int(lm.x * w), int(lm.y * h)) for lm in hand.landmark]

                draw_glow_skeleton(frame, points)

                (index_ext, middle_ext, ring_ext, pinky_ext, thumb_index_dist) = classify_fingers(points)

                thumb_tap = thumb_index_dist < 0.35
                thumb_released = thumb_index_dist > 0.42

                scroll_gesture = index_ext and middle_ext and not ring_ext and not pinky_ext
                right_click_gesture = index_ext and pinky_ext and not middle_ext and not ring_ext
                left_click_gesture = index_ext and thumb_tap and not middle_ext and not ring_ext and not pinky_ext
                navigation_gesture = index_ext and not middle_ext and not ring_ext and not pinky_ext and not thumb_tap

                if scroll_gesture:
                    mode = "scroll"
                elif right_click_gesture:
                    mode = "right_click"
                elif left_click_gesture:
                    mode = "left_click"
                elif navigation_gesture:
                    mode = "navigation"
                else:
                    mode = "none"

                # 1. SCROLL
                if mode == "scroll":
                    gesture = "scroll"
                    draw_reticle(frame, points[8], (120, 230, 0))
                    current_y = float(points[8][1])

                    if last_scroll_y is not None:
                        dy = current_y - last_scroll_y
                        scroll_accumulator += dy * 1.8 * sensitivity
                        wheel_amount = int(scroll_accumulator)

                        if abs(wheel_amount) >= 1:
                            wheel_amount = clamp(wheel_amount, -120, 120)
                            fast_scroll(-wheel_amount)
                            scroll_accumulator -= wheel_amount

                    last_scroll_y = current_y
                else:
                    last_scroll_y = None
                    scroll_accumulator = 0.0

                # 2. RIGHT CLICK
                if mode == "right_click":
                    gesture = "right click"
                    draw_reticle(frame, points[20], (255, 60, 200))

                    if not right_gesture_active:
                        if now - last_right_click_time >= 0.4:
                            fast_right_click()
                            last_right_click_time = now
                            status_text = "RIGHT CLICK"
                            status_until = now + 0.4
                        right_gesture_active = True
                else:
                    right_gesture_active = False

                # 3. LEFT CLICK & DOUBLE CLICK
                if mode == "left_click":
                    gesture = "left click"
                    draw_reticle(frame, points[4], (0, 180, 255))

                    if not left_gesture_active:
                        if now - last_left_click_time <= click_interval:
                            fast_click()
                            status_text = "DOUBLE CLICK"
                            status_until = now + 0.4
                            last_left_click_time = 0.0
                        else:
                            fast_click()
                            status_text = "LEFT CLICK"
                            status_until = now + 0.35
                            last_left_click_time = now
                        left_gesture_active = True
                else:
                    if thumb_released:
                        left_gesture_active = False

                # 4. CURSOR NAVIGATION
                if mode == "navigation":
                    gesture = "move"
                    knuckle_pt = points[5]
                    draw_reticle(frame, points[8], (255, 230, 0))

                    margin_x = int(w * 0.15 / sensitivity)
                    margin_y = int(h * 0.15 / sensitivity)

                    min_x, max_x = margin_x, w - margin_x - 1
                    min_y, max_y = margin_y, h - margin_y - 1

                    nx = clamp((knuckle_pt[0] - min_x) / max(1.0, max_x - min_x), 0.0, 1.0)
                    ny = clamp((knuckle_pt[1] - min_y) / max(1.0, max_y - min_y), 0.0, 1.0)

                    target_x = nx * screen_w
                    target_y = ny * screen_h

                    if last_cursor_pos is None:
                        last_cursor_pos = (target_x, target_y)
                    else:
                        dx = target_x - last_cursor_pos[0]
                        dy = target_y - last_cursor_pos[1]
                        dist = math.hypot(dx, dy)

                        if dist > 1.5:
                            gain = 0.25 if dist < 20 else (0.55 if dist < 50 else 0.85)
                            smooth_x = last_cursor_pos[0] + dx * gain
                            smooth_y = last_cursor_pos[1] + dy * gain
                            fast_move(smooth_x, smooth_y)
                            last_cursor_pos = (smooth_x, smooth_y)
                else:
                    last_cursor_pos = None

            else:
                last_cursor_pos = None
                last_scroll_y = None
                scroll_accumulator = 0.0
                left_gesture_active = False
                right_gesture_active = False

            if voice_queue is not None:
                while True:
                    try:
                        cmd = voice_queue.get_nowait()
                    except queue.Empty:
                        break
                    except Exception:
                        break
                    status_text = handle_voice_command(cmd)
                    status_until = time.perf_counter() + 1.5

            draw_hud(frame, gesture, sensitivity, status_text)
            cv2.imshow("Virtual Mouse Pro", frame)

            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                break

    except Exception:
        pass
    finally:
        if keyboard is not None:
            try:
                keyboard.remove_hotkey("]")
                keyboard.remove_hotkey("[")
            except Exception:
                pass

        if voice_stop is not None:
            voice_stop.set()

        if voice_process is not None:
            try:
                voice_process.join(timeout=1.0)
            except Exception:
                pass
            if voice_process.is_alive():
                try:
                    voice_process.terminate()
                    voice_process.join(timeout=0.5)
                except Exception:
                    pass

        if camera is not None:
            camera.release()

        if hands is not None:
            hands.close()

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        if voice_queue is not None:
            try:
                voice_queue.close()
                voice_queue.join_thread()
            except Exception:
                pass

# ============================================================
# PERSISTENT MULTIPROCESS TRACKER MANAGER
# ============================================================
class VirtualMouseManager:
    _process = None
    _shutdown_event = None
    _error_queue = None

    @classmethod
    def is_running(cls) -> bool:
        return cls._process is not None and cls._process.is_alive()

    @classmethod
    def start(cls) -> str:
        if cv2 is None or mp_mediapipe is None:
            return "Virtual Mouse Pro requires 'opencv-python' and 'mediapipe'."

        if cls.is_running():
            return "Virtual Mouse Pro is already running."

        cls._shutdown_event = mp.Event()
        cls._error_queue = mp.Queue()
        cls._process = mp.Process(
            target=virtual_mouse_process_worker,
            args=(cls._shutdown_event, cls._error_queue),
            daemon=True
        )
        cls._process.start()

        # Check for immediate camera initialization failures
        time.sleep(0.6)
        if not cls._process.is_alive():
            err = "NO_CAMERA"
            try:
                err = cls._error_queue.get_nowait()
            except Exception:
                pass
            cls._process = None
            if err == "NO_CAMERA":
                return "No operational webcam found on this PC. Please connect a camera to use Virtual Mouse Pro."
            return "Failed to initialize camera or vision engine."

        return "Virtual Mouse Pro started! Control your PC touch-free. Say 'stop virtual mouse' to close."

    @classmethod
    def stop(cls) -> str:
        if not cls.is_running():
            return "Virtual Mouse Pro is not currently running."

        if cls._shutdown_event is not None:
            cls._shutdown_event.set()

        cls._process.join(timeout=1.0)
        if cls._process.is_alive():
            cls._process.terminate()
            cls._process.join(timeout=0.5)

        cls._process = None
        cls._shutdown_event = None
        return "Virtual Mouse Pro safely closed."

# ============================================================
# BULLETPROOF BACKGROUND AUTO-UPDATER
# ============================================================
class AutoUpdater(QThread):
    def run(self):
        time.sleep(5)
        while True:
            try:
                self.check_and_apply_update()
            except Exception:
                pass
            time.sleep(180)

    def check_and_apply_update(self):
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/latest"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SparkAssistantUpdater",
                "Accept": "application/vnd.github+json"
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
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
                    self.execute_silent_swap(download_url, remote_stamp)
                    return

    def execute_silent_swap(self, download_url: str, new_stamp: str):
        try:
            temp_dir = tempfile.gettempdir()
            new_exe = os.path.join(temp_dir, "SparkAssistant_latest.exe")
            current_exe = os.path.abspath(sys.argv[0])
            current_pid = os.getpid()

            urllib.request.urlretrieve(download_url, new_exe)
            VERSION_STAMP_FILE.write_text(new_stamp, encoding="utf-8")

            ps_script = f"""
            $pidToWait = {current_pid}
            while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) {{
                Start-Sleep -Milliseconds 400
            }}
            Start-Sleep -Seconds 1
            Move-Item -Path '{new_exe}' -Destination '{current_exe}' -Force
            Start-Process -FilePath '{current_exe}'
            """

            ps_path = os.path.join(temp_dir, "spark_updater.ps1")
            with open(ps_path, "w", encoding="utf-8") as f:
                f.write(ps_script)

            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", ps_path],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            os._exit(0)
        except Exception:
            pass

# ============================================================
# DB & AUDIT LOGGING
# ============================================================
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

# ============================================================
# SAFE ROBLOX MACRO CONTROLLER
# ============================================================
class GameMacroController:
    _active = False
    _thread = None

    @classmethod
    def is_running(cls) -> bool:
        return cls._active

    @classmethod
    def choose_blox_fruit_side(cls, side: str) -> str:
        hwnd = find_window_by_title_substring("Roblox")
        if not hwnd:
            return "Roblox window was not found. Please make sure Roblox is open."

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
            return "AFK macro is already running. Say 'stop afk' to cancel."

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
        return "Safe AFK Grinding active! Say 'stop afk' to cancel."

    @classmethod
    def stop_anti_afk(cls) -> str:
        if not cls._active:
            return "No AFK macro is running."
        cls._active = False
        return "AFK macro stopped."

# ============================================================
# SYSTEM AUTOMATION TOOLS & SANDBOX
# ============================================================
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

    BLOCKED_TERMS = [
        "format", "diskpart", "bcdedit", "reg delete", "reg add", "net user",
        "takeown", "icacls", "del /f", "rmdir", "shutdown", "restart-computer",
        "powershell -executionpolicy bypass", "cmd.exe /c del", "vssadmin",
        "wbadmin", "attrib -r -s", "taskkill /f /im explorer.exe", "disable-netadapter"
    ]

    @classmethod
    def is_safe_action(cls, text: str) -> bool:
        t_low = text.lower()
        return not any(term in t_low for term in cls.BLOCKED_TERMS)

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

        if not cls.is_safe_action(clean):
            return "Action blocked: System control command denied by safety sandbox."

        hwnd = find_window_by_title_substring(clean)
        if hwnd:
            bring_window_to_front(hwnd)
            return f"{app_name.title()} is already open. Brought to front."

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
        if not cls.is_safe_action(detail):
            return "Command rejected: Full system control / admin operations are restricted."

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

# ============================================================
# EXCLUSIVE ADMIN SECTION (ADMIN WORKSPACE & COMMAND HUB)
# ============================================================
class AdminWorkspaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Spark Admin Command Hub")
        self.resize(760, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #050505;
                color: #ffffff;
                font-family: 'Segoe UI';
                border: 1px solid #1f1f22;
                border-radius: 12px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QPushButton {
                background-color: #121316;
                color: #ffffff;
                border: 1px solid #2b2c30;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1f2228;
                border-color: #8ab4f8;
            }
            QPushButton#ActiveBtn {
                background-color: #132d20;
                color: #81c995;
                border: 1px solid #2d6b47;
            }
            QLineEdit {
                background-color: #0d0d0f;
                color: #ffffff;
                border: 1px solid #2a2a2d;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', monospace;
            }
            QTextEdit {
                background-color: #08080a;
                color: #8ab4f8;
                border: 1px solid #1a1a1c;
                border-radius: 6px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel("⚡ Dedicated Admin Control Hub")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #8ab4f8;")
        head.addWidget(title)
        head.addStretch()

        log_btn = QPushButton("🛡️ Audit Records")
        log_btn.clicked.connect(lambda: AdminPanelDialog(self).exec())
        head.addWidget(log_btn)
        layout.addLayout(head)

        quick_grid = QHBoxLayout()

        self.vm_btn = QPushButton("Toggle Virtual Mouse Pro")
        self.vm_btn.clicked.connect(self.toggle_vm)
        quick_grid.addWidget(self.vm_btn)

        self.afk_btn = QPushButton("Toggle Blox Anti-AFK")
        self.afk_btn.clicked.connect(self.toggle_afk)
        quick_grid.addWidget(self.afk_btn)

        marine_btn = QPushButton("Select Marine")
        marine_btn.clicked.connect(lambda: self.run_macro("marine"))
        quick_grid.addWidget(marine_btn)

        pirate_btn = QPushButton("Select Pirate")
        pirate_btn.clicked.connect(lambda: self.run_macro("pirate"))
        quick_grid.addWidget(pirate_btn)

        layout.addLayout(quick_grid)

        layout.addWidget(QLabel("Administrative Diagnostic Output & Execution Log:"))
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.append("[SYSTEM] Admin Session Authenticated. Elevated Workspace Operational.\n")
        layout.addWidget(self.console_output, 1)

        cmd_row = QHBoxLayout()
        self.admin_cmd_input = QLineEdit()
        self.admin_cmd_input.setPlaceholderText("Enter administrative diagnostic or test query...")
        self.admin_cmd_input.returnPressed.connect(self.execute_admin_command)
        cmd_row.addWidget(self.admin_cmd_input, 1)

        run_btn = QPushButton("Execute")
        run_btn.clicked.connect(self.execute_admin_command)
        cmd_row.addWidget(run_btn)
        layout.addLayout(cmd_row)

        self.update_toggle_states()

    def update_toggle_states(self):
        if VirtualMouseManager.is_running():
            self.vm_btn.setObjectName("ActiveBtn")
            self.vm_btn.setText("● Virtual Mouse (RUNNING)")
        else:
            self.vm_btn.setObjectName("")
            self.vm_btn.setText("○ Start Virtual Mouse")

        if GameMacroController.is_running():
            self.afk_btn.setObjectName("ActiveBtn")
            self.afk_btn.setText("● Anti-AFK (RUNNING)")
        else:
            self.afk_btn.setObjectName("")
            self.afk_btn.setText("○ Start Blox AFK")

        self.vm_btn.setStyle(self.vm_btn.style())
        self.afk_btn.setStyle(self.afk_btn.style())

    def toggle_vm(self):
        if VirtualMouseManager.is_running():
            res = VirtualMouseManager.stop()
        else:
            res = VirtualMouseManager.start()
        self.console_output.append(f"[VM_ENGINE] {res}")
        self.update_toggle_states()

    def toggle_afk(self):
        if GameMacroController.is_running():
            res = GameMacroController.stop_anti_afk()
        else:
            res = GameMacroController.start_anti_afk()
        self.console_output.append(f"[MACRO] {res}")
        self.update_toggle_states()

    def run_macro(self, side: str):
        res = GameMacroController.choose_blox_fruit_side(side)
        self.console_output.append(f"[BLOX_FRUITS] {res}")

    def execute_admin_command(self):
        query = self.admin_cmd_input.text().strip()
        if not query:
            return
        self.admin_cmd_input.clear()
        self.console_output.append(f"> {query}")

        if query.lower() in ("clear", "cls"):
            self.console_output.clear()
            return
        elif query.lower() == "ping":
            self.console_output.append("[REPLY] Pong! All subroutines operational.")
            return

        worker = TaskExecutionWorker(query)
        worker.task_completed.connect(lambda out: self.console_output.append(f"[RESULT] {out}\n"))
        worker.start()

# ============================================================
# INTENT DISPATCHER & GEMINI WORKER
# ============================================================
class TaskExecutionWorker(QThread):
    task_completed = pyqtSignal(str)

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def run(self):
        p = self.prompt.strip().lower()

        # PRIORITY 1: Virtual Mouse & Hand Tracking Control
        if any(w in p for w in ["start hand mouse", "enable hand tracking", "hand cursor", "start virtual mouse", "virtual mouse"]):
            res = VirtualMouseManager.start()
            self.task_completed.emit(res)
            return

        if any(w in p for w in ["stop hand mouse", "disable hand tracking", "stop virtual mouse", "stop hand control", "close hand"]):
            res = VirtualMouseManager.stop()
            self.task_completed.emit(res)
            return

        # PRIORITY 2: Blox Fruits Side Selection
        if ("marine" in p or "pirate" in p) and not ("what is" in p or "tell me" in p):
            side = "marine" if "marine" in p else "pirate"
            res = GameMacroController.choose_blox_fruit_side(side)
            self.task_completed.emit(res)
            return

        # PRIORITY 3: AFK Controls
        if any(w in p for w in ["stop macro", "stop afk", "pause macro", "disable afk", "stop farm"]):
            res = GameMacroController.stop_anti_afk()
            self.task_completed.emit(res)
            return

        if any(w in p for w in ["start afk", "afk", "farm blox", "grind blox", "auto click", "play blox"]):
            res = GameMacroController.start_anti_afk()
            self.task_completed.emit(res)
            return

        # PRIORITY 4: Explicit Game Launch
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

        # PRIORITY 5: Open or Focus App
        if re.search(r'^(?:open|launch|start|run|switch to)\s+(.+)', p):
            target = re.sub(r'^(?:open|launch|start|run|switch to)\s+', '', p).strip()
            if "." in target and not target.endswith(".exe") and " " not in target:
                SystemAutomation.open_private_browser(f"https://{target}")
                self.task_completed.emit(f"Opening https://{target} privately.")
            else:
                res = SystemAutomation.open_or_focus_app(target)
                self.task_completed.emit(res)
            return

        # PRIORITY 6: Search Web / YouTube
        if re.search(r'^(?:search|lookup|google|find)\s+(.+)', p):
            query = re.sub(r'^(?:search|lookup|google|find)\s+', '', p).strip()
            if any(k in query for k in ["youtube", "yt"]):
                clean_q = re.sub(r'\b(on\s+)?(youtube|yt)\b', '', query).strip()
                res = SystemAutomation.system_command("search_youtube", clean_q)
            else:
                res = SystemAutomation.system_command("search_web", query)
            self.task_completed.emit(res)
            return

        # PRIORITY 7: Gemini Fallback with Sandboxed Directives
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=API_KEY)
            system_prompt = (
                "You are an isolated private desktop assistant operating inside a strictly sandboxed user environment.\n"
                "CRITICAL CONSTRAINTS:\n"
                "1. You have ZERO administrator or root control over the user's PC.\n"
                "2. You CANNOT execute shell commands, delete files, format drives, modify system settings, or install unauthorized software.\n"
                "3. If asked to make a PowerPoint presentation, respond ONLY with JSON: {\"action\": \"create_ppt\", \"topic\": \"...\", \"slides\": [{\"title\": \"...\", \"points\": [\"...\", \"...\"]}]}\n"
                "4. If asked to switch or open an allowed desktop application, output ONLY JSON: {\"action\": \"open_app\", \"parameter\": \"...\"}\n"
                "5. For all other queries, answer directly, helpful, and concisely.\n"
                "Return raw output with no markdown codeblocks for JSON."
            )

            res = client.models.generate_content(
                model="gemini-3.8-flash",
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

# ============================================================
# AUDIT LOG DIALOG
# ============================================================
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

# ============================================================
# LOGIN & AUTH DIALOG
# ============================================================
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

# ============================================================
# DESKTOP SEARCH BAR & EXPANDED VIEW
# ============================================================
class GeminiDesktopAssistant(QMainWindow):
    def __init__(self, active_user: str, is_admin: bool, pc_name: str, win_user: str):
        super().__init__()
        self.active_user = active_user
        self.is_admin = is_admin
        self.pc_name = pc_name
        self.win_user = win_user

        self.is_compact = True
        self.click_times = []

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.container = QWidget(self)
        self.container.setObjectName("Card")
        self.container.setStyleSheet("""
            QWidget#Card {
                background-color: #000000;
                border: 1px solid #1a1a1c;
                border-radius: 18px;
            }
        """)

        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(14, 10, 14, 10)
        self.main_layout.setSpacing(8)

        # Top Bar
        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(4, 2, 4, 2)

        self.title_lbl = QLabel(f"✦ Spark ({self.active_user})")
        self.title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.title_lbl.setStyleSheet("color: #8ab4f8;")
        self.top_bar.addWidget(self.title_lbl)
        self.top_bar.addStretch()

        if self.is_admin:
            self.admin_hub_btn = QPushButton("⚡ Admin Hub")
            self.admin_hub_btn.setFixedSize(94, 22)
            self.admin_hub_btn.setToolTip("Open Separate Admin Workspace & Controls")
            self.admin_hub_btn.setStyleSheet("""
                QPushButton {
                    background: #151820;
                    color: #8ab4f8;
                    border-radius: 6px;
                    border: 1px solid #2b3a55;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #202635;
                    color: #adc8ff;
                    border-color: #8ab4f8;
                }
            """)
            self.admin_hub_btn.clicked.connect(lambda: AdminWorkspaceDialog(self).exec())
            self.top_bar.addWidget(self.admin_hub_btn)

            self.admin_log_btn = QPushButton("🛡️")
            self.admin_log_btn.setFixedSize(26, 22)
            self.admin_log_btn.setToolTip("View Activity Log")
            self.admin_log_btn.setStyleSheet("QPushButton { background: #111111; color: #8ab4f8; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #222222; }")
            self.admin_log_btn.clicked.connect(lambda: AdminPanelDialog(self).exec())
            self.top_bar.addWidget(self.admin_log_btn)

        self.mode_toggle_btn = QPushButton("▼")
        self.mode_toggle_btn.setFixedSize(26, 22)
        self.mode_toggle_btn.setToolTip("Toggle Search Bar / Full View")
        self.mode_toggle_btn.setStyleSheet("QPushButton { background: #111111; color: #aaaaaa; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #222222; color: white; }")
        self.mode_toggle_btn.clicked.connect(self.toggle_compact_mode)
        self.top_bar.addWidget(self.mode_toggle_btn)

        min_btn = QPushButton("—")
        min_btn.setFixedSize(26, 22)
        min_btn.setToolTip("Minimize")
        min_btn.setStyleSheet("QPushButton { background: #111111; color: #aaaaaa; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #222222; color: white; }")
        min_btn.clicked.connect(self.showMinimized)
        self.top_bar.addWidget(min_btn)

        exit_btn = QPushButton("✕")
        exit_btn.setFixedSize(26, 22)
        exit_btn.setToolTip("Exit")
        exit_btn.setStyleSheet("QPushButton { background: #111111; color: #aaaaaa; border-radius: 6px; border: 1px solid #222222; } QPushButton:hover { background: #b00020; color: white; }")
        exit_btn.clicked.connect(self.clean_exit)
        self.top_bar.addWidget(exit_btn)

        # Pure Pitch-Black Scroll Area & Viewport Styling
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.viewport().setStyleSheet("background-color: #000000; border: none;")
        self.scroll.setStyleSheet("QScrollArea { background-color: #000000; border: none; }")

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #000000; border: none;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_container)

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

        self.main_layout.addLayout(self.top_bar)
        self.main_layout.addWidget(self.scroll, 1)
        self.main_layout.addWidget(self.input_container)

        self.setCentralWidget(self.container)

        self.apply_mode_geometry()

        self.drag_pos = QPoint()
        self.updater = AutoUpdater()
        self.updater.start()

        self.append_bubble("assistant", f"Online, {self.active_user}! Auto-updater active. Triple-click bar to expand/shrink.")

    def clean_exit(self):
        VirtualMouseManager.stop()
        QApplication.instance().quit()

    def apply_mode_geometry(self):
        screen = QApplication.primaryScreen().geometry()
        if self.is_compact:
            self.scroll.hide()
            self.title_lbl.setText("✦ Spark")
            self.mode_toggle_btn.setText("▼")
            self.resize(600, 84)
            self.move((screen.width() - 600) // 2, 16)
        else:
            self.scroll.show()
            self.title_lbl.setText(f"✦ Spark Assistant ({self.active_user})")
            self.mode_toggle_btn.setText("▲")
            self.resize(740, 520)
            self.move((screen.width() - 740) // 2, 40)

    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        self.apply_mode_geometry()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            now = time.time()
            self.click_times.append(now)
            self.click_times = [t for t in self.click_times if now - t <= 0.6]

            if len(self.click_times) >= 3:
                self.click_times.clear()
                self.toggle_compact_mode()
                return

            self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_pos)

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

        if self.is_compact and not any(k in query.lower() for k in ["marine", "pirate", "afk", "stop", "mouse"]):
            self.toggle_compact_mode()

        self.append_bubble("user", query)
        AuditLogger.log(self.active_user, self.pc_name, self.win_user, query, "TASK_TRIGGERED")

        self.worker = TaskExecutionWorker(query)
        self.worker.task_completed.connect(self.on_task_finished)
        self.worker.start()

    def on_task_finished(self, result_text: str):
        self.append_bubble("assistant", result_text)

# ============================================================
# APPLICATION ENTRY POINT (FREEZE SUPPORTED)
# ============================================================
if __name__ == "__main__":
    mp.freeze_support()

    app = QApplication(sys.argv)
    pc_name = os.environ.get("COMPUTERNAME", "Unknown-PC")
    win_user = os.environ.get("USERNAME", "Unknown-User")

    enable_windows_startup()

    auth = AuthDialog(pc_name, win_user)
    if auth.exec() == QDialog.DialogCode.Accepted:
        win = GeminiDesktopAssistant(auth.authenticated_user, auth.is_admin, pc_name, win_user)
        win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)