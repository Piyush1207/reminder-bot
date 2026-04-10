# 

import subprocess
import sys
import platform
import os

class AppLauncher:
    def __init__(self):
        self.os_name = platform.system()
    
    def open_browser(self):
        """Open default web browser"""
        if self.os_name == "Windows":
            os.system("start http://www.google.com")
        elif self.os_name == "Darwin":  # macOS
            subprocess.run(["open", "http://www.google.com"])
        else:  # Linux
            subprocess.run(["xdg-open", "http://www.google.com"])
    
    def open_spotify(self):
        """Open Spotify application"""
        if self.os_name == "Windows":
            # Common Spotify paths
            paths = [
                r"C:\Users\{}\AppData\Roaming\Spotify\Spotify.exe".format(os.getenv("USERNAME")),
                r"C:\Program Files\Spotify\Spotify.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    os.startfile(path)
                    return
        elif self.os_name == "Darwin":
            subprocess.run(["open", "-a", "Spotify"])
        else:  # Linux
            subprocess.run(["spotify"], shell=True)
    
    def open_file_manager(self):
        """Open system file manager"""
        if self.os_name == "Windows":
            os.system("explorer")
        elif self.os_name == "Darwin":
            subprocess.run(["open", "."])
        else:  # Linux
            subprocess.run(["nautilus"])
    
    def open_custom_app(self, app_path):
        """Open any custom application"""
        if self.os_name == "Windows":
            os.startfile(app_path)
        elif self.os_name == "Darwin":
            subprocess.run(["open", app_path])
        else:
            subprocess.run([app_path])
    
    def open_url(self, url):
        """Open specific URL"""
        if self.os_name == "Windows":
            os.system(f"start {url}")
        elif self.os_name == "Darwin":
            subprocess.run(["open", url])
        else:
            subprocess.run(["xdg-open", url])