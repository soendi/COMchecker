import sys
import os
import ctypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _elevate():
    if _is_admin():
        return
    exe = sys.executable if getattr(sys, "frozen", False) else sys.executable
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)


_elevate()

import customtkinter as ctk
from src.app import COMcheckerApp


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = COMcheckerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
