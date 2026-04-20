import psutil
import pywin32
import win32gui
import win32process
import os

STUDY_APPS = ['code', 'winword', 'acrobat', 'devenv', 'chrome', 'msedge', 'python', 'focuslens']
DISTRACTING_APPS = ['spotify', 'discord', 'steam', 'epicgames', 'netflix']

class AppTracker:
    def get_active_window(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name().lower().replace('.exe', '')
            window_title = win32gui.GetWindowText(hwnd).lower()
            
            category = "DISTRACTING" # Matches "DISTRACTION = non-study app" logically
            
            # Allow local test terms so "TRUE FOCUS" registers natively on the UI 
            if any(app in process_name for app in STUDY_APPS) or \
               any(kw in window_title for kw in ["study", "pdf", "wikipedia", "docs", "localhost", "focuslens"]):
                category = "STUDY"
            
            if any(app in process_name for app in DISTRACTING_APPS) or \
               any(kw in window_title for kw in ["youtube", "instagram", "game", "twitter"]):
                category = "DISTRACTING"
                
            return process_name, window_title, category
        except Exception as e:
            return "unknown", "unknown", "DISTRACTING"
