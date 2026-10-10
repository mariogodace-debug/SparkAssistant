import os
import subprocess
import webbrowser
import time
from pathlib import Path
import win32gui
import win32con

class SystemController:
    @staticmethod
    def launch_app(app_command):
        """Launches an application process."""
        try:
            subprocess.Popen(app_command, shell=True)
            return True
        except Exception as e:
            print(f"Error launching {app_command}: {e}")
            return False

    @staticmethod
    def search_web(query):
        """Opens default browser with a search query."""
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)

    @staticmethod
    def find_window_by_title(partial_title):
        """Finds window handle (HWND) matching title."""
        target_hwnd = None

        def enum_windows_callback(hwnd, _):
            nonlocal target_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if partial_title.lower() in title.lower():
                    target_hwnd = hwnd

        win32gui.EnumWindows(enum_windows_callback, None)
        return target_hwnd

    @staticmethod
    def drag_window(hwnd, target_x, target_y, steps=30, delay=0.015):
        """Simulates dragging a window smoothly across the screen."""
        if not hwnd:
            return
        
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)

        rect = win32gui.GetWindowRect(hwnd)
        start_x, start_y = rect[0], rect[1]
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        for step in range(1, steps + 1):
            curr_x = int(start_x + (target_x - start_x) * (step / steps))
            curr_y = int(start_y + (target_y - start_y) * (step / steps))
            win32gui.MoveWindow(hwnd, curr_x, curr_y, width, height, True)
            time.sleep(delay)

    # --- THIS IS THE ONLY NEW FUNCTION ADDED ---
    @staticmethod
    def run_desktop_powershell(script_name):
        """Finds and executes a .ps1 script from the Windows Desktop."""
        desktop_dir = Path.home() / "Desktop"
        
        if not script_name.endswith(".ps1"):
            script_name += ".ps1"

        script_path = desktop_dir / script_name

        if not script_path.exists():
            print(f"File not found on Desktop: {script_path}")
            return f"Error: {script_name} does not exist on your Desktop."

        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(script_path)
        ]

        try:
            subprocess.Popen(command)
            return f"Executing {script_name} from Desktop..."
        except Exception as e:
            return f"Failed to execute script: {e}"