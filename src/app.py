import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime

from src.scanner import PortMonitor, get_available_ports
from src.version import VERSION, APP_NAME, APP_AUTHOR, APP_DESCRIPTION
from src.updater import check_for_update, run_update


class UpdateProgressDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Update")
        self.dialog.geometry("360x120")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.dialog.configure(bg="#2b2b2b")

        frame = tk.Frame(self.dialog, bg="#2b2b2b", padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame, text="Neue Version wird heruntergeladen...",
            bg="#2b2b2b", fg="#ffffff", font=("Segoe UI", 10)
        ).pack(anchor=tk.W, pady=(0, 10))

        self.progress = ttk.Progressbar(frame, length=320, mode="determinate")
        self.progress.pack(fill=tk.X)

        self.status_label = tk.Label(
            frame, text="", bg="#2b2b2b", fg="#aaaaaa", font=("Segoe UI", 8)
        )
        self.status_label.pack(anchor=tk.W, pady=(5, 0))

        self.dialog.protocol("WM_DELETE_WINDOW", self._noop)

    def _noop(self):
        pass

    def set_progress(self, fraction):
        self.progress["value"] = int(fraction * 100)
        self.status_label.config(text=f"{int(fraction * 100)}%")
        self.dialog.update_idletasks()

    def close(self):
        self.dialog.grab_release()
        self.dialog.destroy()


class StatusBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(bg="#1e1e1e", height=28)
        self.pack_propagate(False)

        self.label = tk.Label(
            self, text="Bereit", anchor=tk.W, padx=10,
            bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 9)
        )
        self.label.pack(side=tk.LEFT)

        self.version_label = tk.Label(
            self, text=f"v{VERSION}", anchor=tk.E, padx=10,
            bg="#1e1e1e", fg="#555555", font=("Segoe UI", 9)
        )
        self.version_label.pack(side=tk.RIGHT)

    def set_text(self, text):
        self.label.config(text=text)


class COMcheckerApp:
    COLORS = {
        "bg": "#2b2b2b",
        "fg": "#ffffff",
        "card_bg": "#333333",
        "card_fg": "#dddddd",
        "accent": "#0078d4",
        "success": "#4caf50",
        "error": "#f44336",
        "warning": "#ff9800",
        "info": "#2196f3",
        "border": "#404040",
        "text_area_bg": "#1e1e1e",
        "text_area_fg": "#d4d4d4",
    }

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        self.monitor = PortMonitor()
        self.monitor.on_status(self._on_port_status)
        self.monitor.on_data(self._on_port_data)

        self.port_labels = {}
        self.monitoring = False
        self._setup_styles()
        self._setup_menu()
        self._setup_ui()
        self._refresh_port_list()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("vista")
        style.configure("Accent.TButton", foreground="#ffffff", background=self.COLORS["accent"])
        style.configure("TFrame", background=self.COLORS["bg"])
        style.configure("TLabelframe", background=self.COLORS["bg"], foreground=self.COLORS["fg"])
        style.configure("TLabelframe.Label", background=self.COLORS["bg"], foreground=self.COLORS["fg"])
        style.configure("TButton", padding=(12, 5))
        style.configure("TProgressbar", thickness=12)

    def _setup_menu(self):
        menubar = tk.Menu(self.root, bg=self.COLORS["card_bg"], fg=self.COLORS["fg"],
                          activebackground=self.COLORS["accent"], activeforeground="#ffffff")

        file_menu = tk.Menu(menubar, tearoff=0, bg=self.COLORS["card_bg"], fg=self.COLORS["fg"],
                            activebackground=self.COLORS["accent"], activeforeground="#ffffff")
        file_menu.add_command(label="Ports erneut scannen", command=self._refresh_port_list, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit, accelerator="Alt+F4")
        menubar.add_cascade(label="Datei", menu=file_menu)

        monitor_menu = tk.Menu(menubar, tearoff=0, bg=self.COLORS["card_bg"], fg=self.COLORS["fg"],
                               activebackground=self.COLORS["accent"], activeforeground="#ffffff")
        monitor_menu.add_command(label="Monitoring starten", command=self._start_monitoring, accelerator="F6")
        monitor_menu.add_command(label="Monitoring stoppen", command=self._stop_monitoring, accelerator="F7")
        menubar.add_cascade(label="Monitoring", menu=monitor_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=self.COLORS["card_bg"], fg=self.COLORS["fg"],
                            activebackground=self.COLORS["accent"], activeforeground="#ffffff")
        help_menu.add_command(label="Nach Updates suchen...", command=self._check_update)
        help_menu.add_separator()
        help_menu.add_command(label="Info", command=self._show_about)
        menubar.add_cascade(label="Hilfe", menu=help_menu)

        self.root.config(menu=menubar)

        self.root.bind("<F5>", lambda e: self._refresh_port_list())
        self.root.bind("<F6>", lambda e: self._start_monitoring())
        self.root.bind("<F7>", lambda e: self._stop_monitoring())

    def _setup_ui(self):
        self.root.configure(bg=self.COLORS["bg"])

        header = tk.Frame(self.root, bg=self.COLORS["accent"], height=48)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header, text=APP_NAME, fg="#ffffff", bg=self.COLORS["accent"],
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT, padx=15, pady=8)

        tk.Label(
            header, text=APP_DESCRIPTION, fg="#cce5ff", bg=self.COLORS["accent"],
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=5, pady=8)

        main_container = tk.Frame(self.root, bg=self.COLORS["bg"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        paned = tk.PanedWindow(main_container, orient=tk.VERTICAL, bg=self.COLORS["bg"],
                                sashwidth=4, sashrelief=tk.FLAT, sashpad=0)
        paned.pack(fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(paned, bg=self.COLORS["bg"])
        paned.add(top_frame, height=200)

        ports_frame = tk.LabelFrame(
            top_frame, text=" COM-Ports ", font=("Segoe UI", 9, "bold"),
            bg=self.COLORS["bg"], fg=self.COLORS["fg"],
            relief=tk.GROOVE, bd=1, padx=8, pady=8
        )
        ports_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(ports_frame, bg=self.COLORS["card_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(ports_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.ports_inner = tk.Frame(canvas, bg=self.COLORS["card_bg"])

        self.ports_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.ports_inner, anchor=tk.NW, tags="inner")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        config_frame = tk.Frame(main_container, bg=self.COLORS["bg"])
        config_frame.pack(fill=tk.X, pady=(0, 5))

        ports = ["9600", "19200", "38400", "57600", "115200"]
        tk.Label(config_frame, text="Baudrate:", bg=self.COLORS["bg"], fg=self.COLORS["fg"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.baudrate_var = tk.StringVar(value="9600")
        baud_menu = ttk.Combobox(config_frame, textvariable=self.baudrate_var, values=ports, width=8, state="readonly")
        baud_menu.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(config_frame, text="Datenbits:", bg=self.COLORS["bg"], fg=self.COLORS["fg"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.databits_var = tk.StringVar(value="8")
        db_menu = ttk.Combobox(config_frame, textvariable=self.databits_var, values=["5", "6", "7", "8"],
                               width=4, state="readonly")
        db_menu.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(config_frame, text="Parit\u00e4t:", bg=self.COLORS["bg"], fg=self.COLORS["fg"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.parity_var = tk.StringVar(value="None")
        parity_menu = ttk.Combobox(config_frame, textvariable=self.parity_var,
                                   values=["None", "Even", "Odd"], width=6, state="readonly")
        parity_menu.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(config_frame, text="Stoppbits:", bg=self.COLORS["bg"], fg=self.COLORS["fg"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.stopbits_var = tk.StringVar(value="1")
        sb_menu = ttk.Combobox(config_frame, textvariable=self.stopbits_var, values=["1", "1.5", "2"],
                               width=4, state="readonly")
        sb_menu.pack(side=tk.LEFT)

        log_frame = tk.LabelFrame(
            main_container, text=" Empfangene Daten ", font=("Segoe UI", 9, "bold"),
            bg=self.COLORS["bg"], fg=self.COLORS["fg"],
            relief=tk.GROOVE, bd=1, padx=8, pady=8
        )
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_container = tk.Frame(log_frame, bg=self.COLORS["card_bg"])
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_container, height=8,
            bg=self.COLORS["text_area_bg"], fg=self.COLORS["text_area_fg"],
            font=("Consolas", 11), insertbackground=self.COLORS["fg"],
            relief=tk.FLAT, bd=0, padx=8, pady=6,
            highlightthickness=1, highlightbackground=self.COLORS["border"],
            highlightcolor=self.COLORS["accent"],
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.tag_config("timestamp", foreground="#888888")
        self.log_text.tag_config("port", foreground=self.COLORS["accent"], font=("Consolas", 11, "bold"))
        self.log_text.tag_config("data", foreground=self.COLORS["success"])
        self.log_text.tag_config("error", foreground=self.COLORS["error"])
        self.log_text.tag_config("header", foreground=self.COLORS["warning"], font=("Consolas", 11, "bold"))

        btn_frame = tk.Frame(main_container, bg=self.COLORS["bg"])
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        self.start_btn = tk.Button(
            btn_frame, text="Monitoring Starten",
            bg=self.COLORS["accent"], fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, padx=20, pady=6, cursor="hand2",
            activebackground="#106ebe", activeforeground="#ffffff",
            command=self._start_monitoring,
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = tk.Button(
            btn_frame, text="Monitoring Stoppen",
            bg="#555555", fg="#aaaaaa",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, padx=20, pady=6, cursor="hand2",
            activebackground="#666666", activeforeground="#ffffff",
            state=tk.DISABLED, command=self._stop_monitoring,
        )
        self.stop_btn.pack(side=tk.LEFT)

        self.scan_btn = tk.Button(
            btn_frame, text="Ports scannen",
            bg=self.COLORS["card_bg"], fg=self.COLORS["fg"],
            font=("Segoe UI", 10),
            relief=tk.FLAT, padx=15, pady=6, cursor="hand2",
            activebackground="#444444", activeforeground="#ffffff",
            command=self._refresh_port_list,
        )
        self.scan_btn.pack(side=tk.RIGHT)

        self.clear_btn = tk.Button(
            btn_frame, text="Log l\u00f6schen",
            bg=self.COLORS["card_bg"], fg=self.COLORS["fg"],
            font=("Segoe UI", 10),
            relief=tk.FLAT, padx=15, pady=6, cursor="hand2",
            activebackground="#444444", activeforeground="#ffffff",
            command=self._clear_log,
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=(0, 8))

        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self._log_info(f"{APP_NAME} v{VERSION} gestartet")
        self._log_info(f"Verfgbare Ports: {len(self.port_labels)}")

    def _refresh_port_list(self):
        for widget in self.ports_inner.winfo_children():
            widget.destroy()
        self.port_labels.clear()

        ports = get_available_ports()
        if not ports:
            no_port_frame = tk.Frame(self.ports_inner, bg=self.COLORS["card_bg"])
            no_port_frame.pack(fill=tk.X, padx=5, pady=10)
            tk.Label(
                no_port_frame, text="Keine COM-Ports gefunden",
                bg=self.COLORS["card_bg"], fg=self.COLORS["error"],
                font=("Segoe UI", 10)
            ).pack()
            self.status_bar.set_text("Keine COM-Ports gefunden")
            return

        for port_name in ports:
            port_frame = tk.Frame(self.ports_inner, bg=self.COLORS["card_bg"])
            port_frame.pack(fill=tk.X, padx=5, pady=2)

            status_dot = tk.Frame(port_frame, width=10, height=10, bg="#555555", highlightthickness=0)
            status_dot.pack(side=tk.LEFT, padx=(5, 8), pady=8)

            tk.Label(
                port_frame, text=port_name,
                fg=self.COLORS["accent"], bg=self.COLORS["card_bg"],
                font=("Consolas", 11, "bold"), width=8, anchor=tk.W
            ).pack(side=tk.LEFT)

            status_label = tk.Label(
                port_frame, text="Warte...",
                fg=self.COLORS["fg"], bg=self.COLORS["card_bg"],
                font=("Segoe UI", 9), anchor=tk.W
            )
            status_label.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

            self.port_labels[port_name] = {
                "frame": port_frame,
                "dot": status_dot,
                "status_label": status_label,
            }

        self.status_bar.set_text(f"{len(ports)} COM-Ports gefunden. Drcke F6 zum Starten.")

    def _on_port_status(self, port, status, message):
        def _update():
            if port not in self.port_labels:
                return

            labels = self.port_labels[port]
            if status == "starte":
                labels["dot"].config(bg=self.COLORS["warning"])
                labels["status_label"].config(text=message, fg=self.COLORS["fg"])
            elif status == "verboseunden":
                labels["dot"].config(bg=self.COLORS["success"])
                labels["status_label"].config(text=message, fg=self.COLORS["success"])
            elif status == "fehler":
                labels["dot"].config(bg=self.COLORS["error"])
                labels["status_label"].config(text=message, fg=self.COLORS["error"])
            elif status == "getrennt":
                labels["dot"].config(bg="#555555")
                labels["status_label"].config(text=message, fg="#888888")
            elif status == "info":
                self.status_bar.set_text(message)

        self.root.after(0, _update)

    def _on_port_data(self, port, data, timestamp):
        def _update():
            ts = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:11]
            self.log_text.insert(tk.END, f"[{ts}] ", "timestamp")
            self.log_text.insert(tk.END, f"{port}: ", "port")
            self.log_text.insert(tk.END, f"{data}\n", "data")
            self.log_text.see(tk.END)

            if port in self.port_labels:
                labels = self.port_labels[port]
                labels["dot"].config(bg=self.COLORS["info"])
                labels["status_label"].config(text="Daten empfangen", fg=self.COLORS["info"])
                self.root.after(2000, lambda l=labels: l["dot"].config(bg=self.COLORS["success"]))
                self.root.after(2000, lambda l=labels: l["status_label"].config(
                    text="Empfängt Daten", fg=self.COLORS["success"]))

            self.status_bar.set_text(f"Daten empfangen auf {port}")
            self._auto_scroll_log()

        self.root.after(0, _update)

    def _log_info(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", "header")

    def _log_error(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", "error")

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def _auto_scroll_log(self):
        self.log_text.see(tk.END)

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
            "timeout": 0.1,
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
            self.start_btn.config(state=tk.DISABLED, bg="#555555", fg="#888888")
            self.stop_btn.config(state=tk.NORMAL, bg=self.COLORS["error"], fg="#ffffff",
                                 activebackground="#d32f2f")
            self.scan_btn.config(state=tk.DISABLED)
            self.status_bar.set_text(f"berwache {len(ports)} Ports...")
            self._log_info(f"Monitoring gestartet auf {len(ports)} Port(s) mit {self.baudrate_var.get()} Baud")
        else:
            messagebox.showerror("Fehler", "Monitoring konnte nicht gestartet werden.")

    def _stop_monitoring(self):
        if not self.monitoring:
            return

        self.monitor.stop()
        self.monitoring = False

        self.start_btn.config(state=tk.NORMAL, bg=self.COLORS["accent"], fg="#ffffff",
                              activebackground="#106ebe")
        self.stop_btn.config(state=tk.DISABLED, bg="#555555", fg="#aaaaaa")
        self.scan_btn.config(state=tk.NORMAL)

        for port, labels in self.port_labels.items():
            labels["dot"].config(bg="#555555")
            labels["status_label"].config(text="Gestoppt", fg="#888888")

        self.status_bar.set_text("Monitoring gestoppt")
        self._log_info("Monitoring gestoppt")

    def _check_update(self):
        self.status_bar.set_text("Suche nach Updates...")

        def _check():
            try:
                result = check_for_update()
                if result is None:
                    self.root.after(0, lambda: self._show_no_update())
                else:
                    source, version, message = result
                    self.root.after(0, lambda: self._show_update_available(version, message))
            except Exception as e:
                self.root.after(0, lambda: self._log_error(f"Update-Fehler: {e}"))
                self.root.after(0, lambda: self.status_bar.set_text("Update-Prfung fehlgeschlagen"))

        threading.Thread(target=_check, daemon=True).start()

    def _show_no_update(self):
        messagebox.showinfo("Update", f"Keine neuere Version verfbar.\n\nAktuelle Version: v{VERSION}")
        self.status_bar.set_text("Kein Update verfbar")

    def _show_update_available(self, version, message):
        result = messagebox.askyesno(
            "Update verfbar",
            f"Neue Version {version} gefunden!\n\n"
            f"Mchten Sie das Update jetzt installieren?\n\n"
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
                self.root.after(0, lambda: self.status_bar.set_text("Update fehlgeschlagen"))

        run_update(version, on_progress, on_done)

    def _show_about(self):
        messagebox.showinfo(
            f"ber {APP_NAME}",
            f"{APP_NAME} v{VERSION}\n\n"
            f"{APP_DESCRIPTION}\n\n"
            f"Entwickelt von {APP_AUTHOR}\n\n"
            f"Eine Daten berwachen Sie alle COM-Ports gleichzeitig\n"
            f"und empfangen Daten von Ihrem Addimat-Kellnerschloss."
        )
