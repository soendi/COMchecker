import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from src.app import COMcheckerApp


def main():
    root = tk.Tk()
    app = COMcheckerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
