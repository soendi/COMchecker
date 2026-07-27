import winreg
import os
import sys
import subprocess
from src.version import APP_NAME, APP_AUTHOR

REG_PATH = f"Software\\{APP_AUTHOR}\\{APP_NAME}"
TASK_NAME = "COMchecker"


class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    def _get_key(self, access=winreg.KEY_READ):
        try:
            return winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, access)
        except FileNotFoundError:
            return None

    def _create_key(self):
        return winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)

    def get(self, name, default=None):
        key = self._get_key()
        if key is None:
            return default
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return value
        except FileNotFoundError:
            return default
        finally:
            winreg.CloseKey(key)

    def set(self, name, value):
        key = self._create_key()
        try:
            if isinstance(value, int):
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
            elif isinstance(value, bool):
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1 if value else 0)
            else:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
        finally:
            winreg.CloseKey(key)

    def delete_key(self, name):
        key = self._create_key()
        try:
            winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)

    def delete_all(self):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        except FileNotFoundError:
            pass

    # ---- Autostart via Task Scheduler (Admin-kompatibel) ----

    def _task_exists(self):
        try:
            result = subprocess.run(
                ["schtasks", "/QUERY", "/TN", TASK_NAME],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception:
            return False

    def _create_task(self, exe_path):
        cmd = [
            "schtasks", "/CREATE", "/SC", "ONLOGON",
            "/TN", TASK_NAME,
            "/TR", exe_path,
            "/RL", "HIGHEST",
            "/F"
        ]
        subprocess.run(cmd, capture_output=True, text=True,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=True)

    def _delete_task(self):
        subprocess.run(
            ["schtasks", "/DELETE", "/TN", TASK_NAME, "/F"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def get_autostart(self):
        return TASK_NAME if self._task_exists() else None

    def set_autostart(self, enable, exe_path=None):
        if enable:
            if exe_path is None:
                exe_path = os.path.abspath(sys.argv[0])
            self._create_task(exe_path)
        else:
            self._delete_task()
