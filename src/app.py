import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import threading
import os
import sys
import subprocess
import ctypes
from datetime import datetime

from src.scanner import PortMonitor, get_available_ports
from src.version import VERSION, APP_NAME, APP_AUTHOR, APP_DESCRIPTION
from src.updater import check_for_update, run_update
from src.logger import Logger
from src.settings import Settings
from src.database import Database
from src.email_sender import EmailSender

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#0078d4"


class SettingsDialog:
    def __init__(self, parent):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Einstellungen")
        self.dialog.geometry("550x500")
        self.dialog.minsize(500, 400)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.settings = Settings()
        self.email_sender = EmailSender()
        self.result = None

        self._setup_ui()
        self._load_settings()
        self.dialog.wait_window()

    def _setup_ui(self):
        tabview = ctk.CTkTabview(self.dialog, segmented_button_fg_color="#333333",
                                  segmented_button_selected_color=ACCENT)
        tabview.pack(fill="both", expand=True, padx=15, pady=15)

        tab_email = tabview.add("E-Mail")
        tab_printer = tabview.add("Drucker")
        tab_autostart = tabview.add("Autostart")
        tab_datenbank = tabview.add("Datenbank")

        self._setup_email_tab(tab_email)
        self._setup_printer_tab(tab_printer)
        self._setup_autostart_tab(tab_autostart)
        self._setup_database_tab(tab_datenbank)

        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(btn_frame, text="Speichern", command=self._save,
                       fg_color=ACCENT, width=120).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_frame, text="Abbrechen", command=self.dialog.destroy,
                       fg_color="#555555", width=120).pack(side="right")

    def _setup_email_tab(self, parent):
        parent.grid_columnconfigure(1, weight=1)

        labels = ["SMTP-Server:", "Port:", "Verschl\u00fcsselung:", "Benutzername:", "Passwort:", "Absender-Adresse:"]
        self.email_widgets = {}

        for i, label in enumerate(labels):
            ctk.CTkLabel(parent, text=label, anchor="w").grid(row=i, column=0, sticky="w", padx=(10, 10), pady=6)
            if label == "Port:":
                var = ctk.StringVar()
                entry = ctk.CTkEntry(parent, textvariable=var, width=120)
                entry.grid(row=i, column=1, sticky="w", padx=10, pady=6)
                self.email_widgets[label] = var
            elif label == "Verschl\u00fcsselung:":
                var = ctk.StringVar(value="STARTTLS")
                menu = ctk.CTkOptionMenu(parent, variable=var, values=["STARTTLS", "SSL", "Keine"],
                                          fg_color="#333333", button_color=ACCENT)
                menu.grid(row=i, column=1, sticky="w", padx=10, pady=6)
                self.email_widgets[label] = var
            elif label == "Passwort:":
                var = ctk.StringVar()
                entry = ctk.CTkEntry(parent, textvariable=var, width=250, show="*")
                entry.grid(row=i, column=1, sticky="ew", padx=10, pady=6)
                self.email_widgets[label] = var
            else:
                var = ctk.StringVar()
                entry = ctk.CTkEntry(parent, textvariable=var, width=250)
                entry.grid(row=i, column=1, sticky="ew", padx=10, pady=6)
                self.email_widgets[label] = var

        ctk.CTkButton(parent, text="Verbindung testen", command=self._test_email,
                       fg_color="#4caf50", width=150).grid(row=len(labels), column=0, columnspan=2,
                                                            padx=10, pady=(15, 5))
        self.email_test_label = ctk.CTkLabel(parent, text="", anchor="w")
        self.email_test_label.grid(row=len(labels) + 1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def _setup_printer_tab(self, parent):
        self.printer_var = ctk.StringVar()

        ctk.CTkLabel(parent, text="Standarddrucker ausw\u00e4hlen:", anchor="w").pack(anchor="w", padx=10, pady=(15, 5))

        printers = self._get_available_printers()
        self.printer_menu = ctk.CTkOptionMenu(parent, variable=self.printer_var,
                                               values=printers if printers else ["Kein Drucker gefunden"],
                                               fg_color="#333333", button_color=ACCENT, width=300)
        self.printer_menu.pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(parent, text="Der ausgew\u00e4hlte Drucker wird f\u00fcr den Log-Ausdruck verwendet.",
                       text_color="#888888", anchor="w").pack(anchor="w", padx=10, pady=(5, 0))

    def _setup_autostart_tab(self, parent):
        self.autostart_var = ctk.BooleanVar(value=False)

        ctk.CTkLabel(parent, text="Autostart-Einstellungen", anchor="w",
                       font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(15, 5))

        cb = ctk.CTkCheckBox(parent, text="COMchecker automatisch beim Windows-Start ausf\u00fchren",
                              variable=self.autostart_var, onvalue=True, offvalue=False,
                              fg_color=ACCENT, hover_color="#106ebe")
        cb.pack(anchor="w", padx=10, pady=10)

        ctk.CTkLabel(parent, text="Die App wird über die Windows-Taskplanung (mit Admin-Rechten) gestartet.\n"
                       "Kein UAC-Dialog beim Systemstart.",
                       text_color="#888888", anchor="w", justify="left").pack(anchor="w", padx=10, pady=(0, 10))

    def _setup_database_tab(self, parent):
        db = Database()

        ctk.CTkLabel(parent, text="Datenbank-Sicherung", anchor="w",
                       font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(15, 5))

        ctk.CTkLabel(parent, text=f"Aktuelle Datenbank:\n{db.db_path}",
                       text_color="#888888", anchor="w", justify="left").pack(anchor="w", padx=10, pady=5)

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(anchor="w", padx=10, pady=15)

        ctk.CTkButton(btn_frame, text="Backup erstellen", command=self._backup_db,
                       fg_color="#4caf50", width=140).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Datenbank wiederherstellen", command=self._restore_db,
                       fg_color="#ff9800", width=200).pack(side="left")

    def _get_available_printers(self):
        try:
            import win32print
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1)
            return [p[2] for p in printers] if printers else ["Standarddrucker (System)"]
        except Exception:
            return ["Standarddrucker (System)"]

    def _test_email(self):
        config = self._collect_email_config()
        self.email_sender.save_config(config)
        success, msg = self.email_sender.test_connection()
        self.email_test_label.configure(text=msg, text_color="#4caf50" if success else "#f44336")

    def _collect_email_config(self):
        return {
            "server": self.email_widgets["SMTP-Server:"].get(),
            "port": int(self.email_widgets["Port:"].get() or "587"),
            "encryption": self.email_widgets["Verschl\u00fcsselung:"].get(),
            "username": self.email_widgets["Benutzername:"].get(),
            "password": self.email_widgets["Passwort:"].get(),
            "sender": self.email_widgets["Absender-Adresse:"].get(),
        }

    def _load_settings(self):
        config = self.email_sender.get_config()
        label_map = {
            "server": "SMTP-Server:", "port": "Port:", "encryption": "Verschl\u00fcsselung:",
            "username": "Benutzername:", "password": "Passwort:", "sender": "Absender-Adresse:",
        }
        for key, label in label_map.items():
            if label in self.email_widgets:
                self.email_widgets[label].set(str(config.get(key, "")))

        printer = self.settings.get("printer_name", "")
        if printer:
            self.printer_var.set(printer)

        existing = self.settings.get_autostart()
        self.autostart_var.set(existing is not None)

    def _save(self):
        config = self._collect_email_config()
        self.email_sender.save_config(config)
        self.settings.set("printer_name", self.printer_var.get())
        exe_path = os.path.abspath(sys.argv[0])
        self.settings.set_autostart(self.autostart_var.get(), exe_path)
        self.dialog.destroy()

    def _backup_db(self):
        path = filedialog.asksaveasfilename(
            title="Datenbank-Backup speichern",
            defaultextension=".db",
            filetypes=[("Datenbank", "*.db"), ("Alle Dateien", "*.*")]
        )
        if path:
            try:
                db = Database()
                result = db.backup(path)
                messagebox.showinfo("Backup", f"Datenbank-Backup erstellt:\n{result}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Backup fehlgeschlagen:\n{e}")

    def _restore_db(self):
        path = filedialog.askopenfilename(
            title="Datenbank-Backup wiederherstellen",
            filetypes=[("Datenbank", "*.db"), ("Alle Dateien", "*.*")]
        )
        if path:
            result = messagebox.askyesno("Wiederherstellung",
                                           "Achtung: Die aktuelle Datenbank wird ersetzt!\n\n"
                                           "Fortfahren?")
            if result:
                try:
                    db = Database()
                    count = db.restore(path)
                    messagebox.showinfo("Wiederherstellung",
                                        f"{count} Datensätze wurden wiederhergestellt.")
                except Exception as e:
                    messagebox.showerror("Fehler", f"Wiederherstellung fehlgeschlagen:\n{e}")


class UpdateProgressDialog:
    def __init__(self, parent):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Update")
        self.dialog.geometry("380x130")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(frame, text="Neue Version wird heruntergeladen...",
                       anchor="w", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 10))

        self.progress = ctk.CTkProgressBar(frame, height=14, progress_color=ACCENT,
                                            fg_color="#444444")
        self.progress.pack(fill="x")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(frame, text="", text_color="#aaaaaa")
        self.status_label.pack(anchor="w", pady=(5, 0))

        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    def set_progress(self, fraction):
        self.progress.set(fraction)
        self.status_label.configure(text=f"{int(fraction * 100)}%")
        self.dialog.update_idletasks()

    def close(self):
        self.dialog.grab_release()
        self.dialog.destroy()


class COMcheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("960x700")
        self.root.minsize(850, 600)

        self.logger = Logger()
        self.settings = Settings()
        self.db = Database()
        self.email_sender = EmailSender()
        self.logger.info(f"{APP_NAME} v{VERSION} gestartet")

        self.monitor = PortMonitor()
        self.monitor.on_status(self._on_port_status)
        self.monitor.on_data(self._on_port_data)

        self.port_widgets = {}
        self.monitoring = False
        self.preset_timeout_ms = 100

        self._setup_menu()
        self._setup_ui()
        self._hide_submenu_on_leave()
        self._refresh_port_list()

    def _setup_menu(self):
        menu_bg = "#2b2b2b"
        menu_fg = "#ffffff"
        active_bg = ACCENT
        active_fg = "#ffffff"

        self.menubar = tk.Menu(self.root, bg=menu_bg, fg=menu_fg,
                                activebackground=active_bg, activeforeground=active_fg,
                                font=("Segoe UI", 10))

        file_menu = tk.Menu(self.menubar, tearoff=0, bg=menu_bg, fg=menu_fg,
                             activebackground=active_bg, activeforeground=active_fg,
                             font=("Segoe UI", 10))
        file_menu.add_command(label="Einstellungen...", command=self._open_settings, accelerator="Strg+,")
        file_menu.add_separator()
        file_menu.add_command(label="Ports erneut scannen", command=self._refresh_port_list, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self._quit, accelerator="Alt+F4")
        self.menubar.add_cascade(label="Datei", menu=file_menu)

        monitor_menu = tk.Menu(self.menubar, tearoff=0, bg=menu_bg, fg=menu_fg,
                                activebackground=active_bg, activeforeground=active_fg,
                                font=("Segoe UI", 10))
        monitor_menu.add_command(label="Monitoring starten", command=self._start_monitoring, accelerator="F6")
        monitor_menu.add_command(label="Monitoring stoppen", command=self._stop_monitoring, accelerator="F7")
        monitor_menu.add_separator()

        self.autostart_menu_var = tk.BooleanVar(value=self._is_autostart_enabled())
        monitor_menu.add_checkbutton(label="Autostart", variable=self.autostart_menu_var,
                                      command=self._toggle_autostart_menu)
        self.menubar.add_cascade(label="Monitoring", menu=monitor_menu)

        help_menu = tk.Menu(self.menubar, tearoff=0, bg=menu_bg, fg=menu_fg,
                             activebackground=active_bg, activeforeground=active_fg,
                             font=("Segoe UI", 10))
        help_menu.add_command(label="Logdatei \u00f6ffnen", command=self._open_log)
        help_menu.add_command(label="Logdatei senden...", command=self._send_log_email)
        help_menu.add_separator()
        help_menu.add_command(label="Auf Updates pr\u00fcfen...", command=self._check_update)
        help_menu.add_separator()
        help_menu.add_command(label="Deinstallieren...", command=self._uninstall_app)
        help_menu.add_separator()
        help_menu.add_command(label="Info", command=self._show_about)
        self.menubar.add_cascade(label="Hilfe", menu=help_menu)

        self.root.config(menu=self.menubar)

        self.root.bind("<F5>", lambda e: self._refresh_port_list())
        self.root.bind("<F6>", lambda e: self._start_monitoring())
        self.root.bind("<F7>", lambda e: self._stop_monitoring())
        self.root.bind("<Control-comma>", lambda e: self._open_settings())

    def _hide_submenu_on_leave(self):
        def _on_leave(event):
            x, y = event.x_root, event.y_root
            try:
                menu = event.widget
                if isinstance(menu, tk.Menu):
                    menu_x = menu.winfo_rootx()
                    menu_y = menu.winfo_rooty()
                    menu_w = menu.winfo_width()
                    menu_h = menu.winfo_height()
                    if menu_w > 0 and menu_h > 0:
                        if (x < menu_x - 200 or x > menu_x + menu_w + 200 or
                            y < menu_y - 200 or y > menu_y + menu_h + 200):
                            menu.unpost()
            except Exception:
                pass

        def _on_window_move(event):
            try:
                self.menubar.unpost()
                for i in range(self.menubar.index("end") or 0):
                    try:
                        self.menubar.detach(i)
                    except Exception:
                        pass
            except Exception:
                pass

        for menu_name in ["Datei", "Monitoring", "Hilfe"]:
            try:
                idx = self.menubar.index(menu_name)
                menu = self.menubar.nametowidget(self.menubar.entrycascade(idx) or "")
                if menu:
                    menu.bind("<Leave>", _on_leave, add="+")
            except Exception:
                pass

        self.root.bind("<Configure>", _on_window_move, add="+")

    def _is_autostart_enabled(self):
        return self.settings.get_autostart() is not None

    def _toggle_autostart_menu(self):
        exe_path = os.path.abspath(sys.argv[0])
        self.settings.set_autostart(self.autostart_menu_var.get(), exe_path)
        if self.autostart_menu_var.get():
            self.logger.info("Autostart aktiviert")
            self._status("Autostart aktiviert")
        else:
            self.logger.info("Autostart deaktiviert")
            self._status("Autostart deaktiviert")

    def _setup_ui(self):
        header = ctk.CTkFrame(self.root, fg_color=ACCENT, height=48, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text=APP_NAME, text_color="#ffffff",
                      font=("Segoe UI", 15, "bold")).pack(side="left", padx=15, pady=8)

        ctk.CTkLabel(header, text=APP_DESCRIPTION, text_color="#cce5ff",
                       font=("Segoe UI", 10)).pack(side="left", padx=5, pady=8)

        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        admin_text = "Administrator" if is_admin else "Benutzer"
        admin_color = "#ff9800" if is_admin else "#aaaaaa"
        ctk.CTkLabel(header, text=admin_text, text_color=admin_color,
                       font=("Segoe UI", 9)).pack(side="right", padx=15, pady=8)

        main_container = ctk.CTkFrame(self.root, fg_color="#2b2b2b")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        ports_frame = ctk.CTkFrame(main_container, fg_color="#333333", corner_radius=6)
        ports_frame.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(ports_frame, text="COM-Ports", font=("Segoe UI", 11, "bold"),
                       anchor="w").pack(anchor="w", padx=12, pady=(8, 2))

        self.ports_scroll = ctk.CTkScrollableFrame(ports_frame, fg_color="#333333",
                                                     scrollbar_button_color="#555555",
                                                     scrollbar_button_hover_color=ACCENT,
                                                     corner_radius=0)
        self.ports_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        config_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        config_frame.pack(fill="x", pady=(5, 5))

        ctk.CTkLabel(config_frame, text="Preset:").pack(side="left", padx=(0, 5))
        self.preset_var = ctk.StringVar(value="")
        ctk.CTkOptionMenu(config_frame, variable=self.preset_var,
                           values=["", "Addimat", "iButton", "JK2000",
                                   "NCR Orderman 2in1 SignIn (1)",
                                   "NCR Orderman 2in1 SignIn (2)", "WMF"],
                           fg_color="#333333", button_color=ACCENT, width=150,
                           command=self._apply_preset).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(config_frame, text="Baudrate:").pack(side="left", padx=(0, 5))
        self.baudrate_var = ctk.StringVar(value="9600")
        ctk.CTkOptionMenu(config_frame, variable=self.baudrate_var,
                           values=["9600", "19200", "38400", "57600", "115200"],
                           fg_color="#333333", button_color=ACCENT, width=85).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(config_frame, text="Datenbits:").pack(side="left", padx=(0, 5))
        self.databits_var = ctk.StringVar(value="8")
        ctk.CTkOptionMenu(config_frame, variable=self.databits_var,
                           values=["5", "6", "7", "8"],
                           fg_color="#333333", button_color=ACCENT, width=60).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(config_frame, text="Parit\u00e4t:").pack(side="left", padx=(0, 5))
        self.parity_var = ctk.StringVar(value="None")
        ctk.CTkOptionMenu(config_frame, variable=self.parity_var,
                           values=["None", "Even", "Odd"],
                           fg_color="#333333", button_color=ACCENT, width=70).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(config_frame, text="Stoppbits:").pack(side="left", padx=(0, 5))
        self.stopbits_var = ctk.StringVar(value="1")
        ctk.CTkOptionMenu(config_frame, variable=self.stopbits_var,
                           values=["1", "1.5", "2"],
                           fg_color="#333333", button_color=ACCENT, width=60).pack(side="left")

        log_frame = ctk.CTkFrame(main_container, fg_color="#333333", corner_radius=6)
        log_frame.pack(fill="both", expand=True, pady=(5, 5))

        ctk.CTkLabel(log_frame, text="Empfangene Daten", font=("Segoe UI", 11, "bold"),
                       anchor="w").pack(anchor="w", padx=12, pady=(8, 2))

        self.log_text = ctk.CTkTextbox(log_frame, fg_color="#1e1e1e", text_color="#d4d4d4",
                                        font=("Consolas", 11), corner_radius=4,
                                        scrollbar_button_color="#555555",
                                        scrollbar_button_hover_color=ACCENT)
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        btn_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))

        self.start_btn = ctk.CTkButton(btn_frame, text="Monitoring Starten",
                                        fg_color=ACCENT, hover_color="#106ebe",
                                        font=("Segoe UI", 11, "bold"),
                                        command=self._start_monitoring, width=160)
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(btn_frame, text="Monitoring Stoppen",
                                       fg_color="#555555", hover_color="#666666",
                                       font=("Segoe UI", 11, "bold"),
                                       state="disabled", command=self._stop_monitoring, width=160)
        self.stop_btn.pack(side="left")

        ctk.CTkButton(btn_frame, text="Ports scannen",
                       fg_color="#444444", hover_color="#555555",
                       command=self._refresh_port_list, width=120).pack(side="right", padx=(8, 0))

        ctk.CTkButton(btn_frame, text="Log l\u00f6schen",
                       fg_color="#444444", hover_color="#555555",
                       command=self._clear_log, width=100).pack(side="right")

        self.status_frame = ctk.CTkFrame(self.root, fg_color="#1e1e1e", height=28, corner_radius=0)
        self.status_frame.pack(fill="x", side="bottom")
        self.status_frame.pack_propagate(False)

        self.status_label = ctk.CTkLabel(self.status_frame, text="Bereit",
                                           text_color="#aaaaaa", anchor="w")
        self.status_label.pack(side="left", padx=10)

        ctk.CTkLabel(self.status_frame, text=f"v{VERSION}",
                      text_color="#555555").pack(side="right", padx=10)

    def _refresh_port_list(self):
        for widget in self.ports_scroll.winfo_children():
            widget.destroy()
        self.port_widgets.clear()

        ports = get_available_ports()
        if not ports:
            lbl = ctk.CTkLabel(self.ports_scroll, text="Keine COM-Ports gefunden",
                                text_color="#f44336")
            lbl.pack(padx=10, pady=10)
            self._status("Keine COM-Ports gefunden")
            return

        for port_name in ports:
            row = ctk.CTkFrame(self.ports_scroll, fg_color="#2a2a2a", corner_radius=4)
            row.pack(fill="x", padx=5, pady=2)

            dot = ctk.CTkFrame(row, width=12, height=12, fg_color="#555555", corner_radius=6)
            dot.pack(side="left", padx=(8, 8), pady=6)
            dot.pack_propagate(False)

            ctk.CTkLabel(row, text=port_name, text_color=ACCENT,
                          font=("Consolas", 12, "bold"), width=8, anchor="w").pack(side="left")

            status_lbl = ctk.CTkLabel(row, text="Warte...", text_color="#cccccc", anchor="w")
            status_lbl.pack(side="left", padx=(10, 0), fill="x", expand=True)

            self.port_widgets[port_name] = {"dot": dot, "status": status_lbl, "frame": row}

        self.logger.info(f"Ports gescannt: {len(ports)} gefunden")
        self._status(f"{len(ports)} COM-Ports gefunden. F6 zum Starten.")

    def _on_port_status(self, port, status, message):
        def _update():
            if port not in self.port_widgets:
                return
            w = self.port_widgets[port]
            colors = {
                "starte": ("#ff9800", "#cccccc"),
                "verboseunden": ("#4caf50", "#4caf50"),
                "fehler": ("#f44336", "#f44336"),
                "getrennt": ("#555555", "#888888"),
            }
            dot_color, text_color = colors.get(status, ("#555555", "#888888"))
            w["dot"].configure(fg_color=dot_color)
            w["status"].configure(text=message, text_color=text_color)

        self.root.after(0, _update)

    def _on_port_data(self, port, data, timestamp):
        def _update():
            ts = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:11]
            self.log_text.insert("end", f"[{ts}] {port}: {data}\n",
                                  tag_name="data")
            self.log_text.see("end")

            self.db.save_data(port, data, datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f"))

            if port in self.port_widgets:
                w = self.port_widgets[port]
                w["dot"].configure(fg_color="#2196f3")
                w["status"].configure(text="Daten empfangen", text_color="#2196f3")
                self.root.after(2000, lambda w=w: w["dot"].configure(fg_color="#4caf50"))
                self.root.after(2000, lambda w=w: w["status"].configure(
                    text="Empf\u00e4ngt Daten", text_color="#4caf50"))

            self._status(f"Daten empfangen auf {port}")

        self.root.after(0, _update)

    def _apply_preset(self, choice):
        presets = {
            "Addimat": {"baudrate": "9600", "databits": "8", "stopbits": "1", "parity": "None", "timeout_ms": 50},
            "iButton": {"baudrate": "9600", "databits": "8", "stopbits": "1", "parity": "None", "timeout_ms": 10},
            "JK2000": {"baudrate": "2400", "databits": "8", "stopbits": "1", "parity": "None", "timeout_ms": 10},
            "NCR Orderman 2in1 SignIn (1)": {"baudrate": "9600", "databits": "8", "stopbits": "1", "parity": "None", "timeout_ms": 10},
            "NCR Orderman 2in1 SignIn (2)": {"baudrate": "115200", "databits": "8", "stopbits": "1", "parity": "None", "timeout_ms": 10},
            "WMF": {"baudrate": "9600", "databits": "8", "stopbits": "1", "parity": "None", "timeout_ms": 50},
        }
        p = presets.get(choice)
        if p:
            self.baudrate_var.set(p["baudrate"])
            self.databits_var.set(p["databits"])
            self.stopbits_var.set(p["stopbits"])
            self.parity_var.set(p["parity"])
            self.preset_timeout_ms = p["timeout_ms"]
            self.logger.info(f"Preset '{choice}' geladen (Timeout={p['timeout_ms']}ms)")
            self._log(f"Preset '{choice}' geladen (Timeout={p['timeout_ms']}ms)")

    def _get_serial_config(self):
        import serial
        parity_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
        }
        stopbits_map = {
            "1": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO,
        }
        return {
            "baudrate": int(self.baudrate_var.get()),
            "bytesize": int(self.databits_var.get()),
            "parity": parity_map.get(self.parity_var.get(), serial.PARITY_NONE),
            "stopbits": stopbits_map.get(self.stopbits_var.get(), serial.STOPBITS_ONE),
            "timeout": self.preset_timeout_ms / 1000.0,
        }

    def _start_monitoring(self):
        if self.monitoring:
            return

        ports = get_available_ports()
        if not ports:
            messagebox.showwarning("Keine Ports", "Keine COM-Ports gefunden.")
            return

        self.monitor.config = self._get_serial_config()

        if self.monitor.start(ports):
            self.monitoring = True
            self.start_btn.configure(state="disabled", fg_color="#555555")
            self.stop_btn.configure(state="normal", fg_color="#f44336", hover_color="#d32f2f")
            msg = f"Monitoring gestartet auf {len(ports)} Port(s) mit {self.baudrate_var.get()} Baud, Timeout={self.preset_timeout_ms}ms"
            self.logger.info(msg)
            self._log(msg)
            self._status(f"\u00dcberwache {len(ports)} Ports...")
        else:
            messagebox.showerror("Fehler", "Monitoring konnte nicht gestartet werden.")

    def _stop_monitoring(self):
        if not self.monitoring:
            return

        self.monitor.stop()
        self.monitoring = False

        self.start_btn.configure(state="normal", fg_color=ACCENT, hover_color="#106ebe")
        self.stop_btn.configure(state="disabled", fg_color="#555555", hover_color="#666666")

        for w in self.port_widgets.values():
            w["dot"].configure(fg_color="#555555")
            w["status"].configure(text="Gestoppt", text_color="#888888")

        self.logger.info("Monitoring gestoppt")
        self._log("Monitoring gestoppt")
        self._status("Monitoring gestoppt")

    def _log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {message}\n")
        self.log_text.see("end")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")

    def _status(self, text):
        self.status_label.configure(text=text)

    def _open_settings(self):
        SettingsDialog(self.root)

    def _open_log(self):
        try:
            self.logger.open_log()
        except Exception as e:
            messagebox.showerror("Fehler", f"Logdatei konnte nicht ge\u00f6ffnet werden:\n{e}")

    def _send_log_email(self):
        config = self.email_sender.get_config()
        if not config["server"] or not config["sender"]:
            result = messagebox.askyesno("E-Mail-Konfiguration",
                                           "E-Mail wurde noch nicht konfiguriert.\n"
                                           "M\u00f6chten Sie jetzt die Einstellungen \u00f6ffnen?")
            if result:
                self._open_settings()
            return

        recipient = simpledialog.askstring("Logdatei senden",
                                            "Empf\u00e4nger-Adresse:",
                                            initialvalue=config["sender"])
        if recipient:
            self._status("Sende Logdatei...")
            def _send():
                success, msg = self.email_sender.send_log(self.logger.log_path, recipient)
                self.root.after(0, lambda: self._status(msg if success else f"Fehler: {msg}"))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Logdatei senden", msg))
            threading.Thread(target=_send, daemon=True).start()

    def _check_update(self):
        self._status("Suche nach Updates...")

        def _check():
            try:
                result = check_for_update()
                if result is None:
                    self.root.after(0, lambda: self._show_no_update())
                else:
                    _, version, _ = result
                    self.root.after(0, lambda: self._show_update_available(version))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Update-Fehler: {e}"))
                self.root.after(0, lambda: self._status("Update-Pr\u00fcfung fehlgeschlagen"))

        threading.Thread(target=_check, daemon=True).start()

    def _show_no_update(self):
        messagebox.showinfo("Update", f"Keine neuere Version verf\u00fcgbar.\n\nAktuelle Version: v{VERSION}")
        self._status("Kein Update verf\u00fcgbar")

    def _show_update_available(self, version):
        result = messagebox.askyesno(
            "Update verf\u00fcgbar",
            f"Neue Version {version} gefunden!\n\n"
            f"M\u00f6chten Sie das Update jetzt installieren?\n\n"
            f"Aktuelle Version: v{VERSION}"
        )
        if result:
            self._run_update(version)

    def _run_update(self, version):
        progress_dialog = UpdateProgressDialog(self.root)

        def on_progress(fraction):
            self.root.after(0, lambda: progress_dialog.set_progress(fraction))

        def on_done(success, error_msg):
            self.root.after(0, lambda: progress_dialog.close())
            if not success:
                self.root.after(0, lambda: messagebox.showerror(
                    "Update-Fehler", f"Download fehlgeschlagen:\n{error_msg}"))
                self.root.after(0, lambda: self._status("Update fehlgeschlagen"))

        run_update(version, on_progress, on_done)

    def _uninstall_app(self):
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        uninstall_path = os.path.join(exe_dir, "unins000.exe")
        if os.path.exists(uninstall_path):
            self.logger.info("Deinstallation gestartet")
            subprocess.Popen([uninstall_path])
            self.root.destroy()
        else:
            messagebox.showerror("Fehler",
                "Uninstaller nicht gefunden.\n"
                "Bitte deinstallieren Sie COMchecker manuell über:\n"
                "Systemsteuerung > Apps & Features")

    def _show_about(self):
        messagebox.showinfo(
            f"\u00dcber {APP_NAME}",
            f"{APP_NAME} v{VERSION}\n\n"
            f"{APP_DESCRIPTION}\n\n"
            f"Entwickelt von {APP_AUTHOR}\n\n"
            f"\u00dcberwacht alle COM-Ports gleichzeitig\n"
            f"und empf\u00e4ngt Daten von Addimat-Kellnerschl\u00f6ssern."
        )

    def _quit(self):
        if self.monitoring:
            self.monitor.stop()
        self.logger.info("Programm beendet")
        self.root.destroy()
