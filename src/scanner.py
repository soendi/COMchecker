import serial
from serial.tools import list_ports
import threading
import time
import queue

PORT_CONFIG = {
    "baudrate": 9600,
    "bytesize": serial.EIGHTBITS,
    "parity": serial.PARITY_NONE,
    "stopbits": serial.STOPBITS_ONE,
    "timeout": 0.1,
}


def get_available_ports():
    return [port.device for port in list_ports.comports()]


def monitor_port(port_name, config, data_queue, stop_event, status_callback):
    ser = None
    try:
        ser = serial.Serial(port_name, **config)
        status_callback(port_name, "verboseunden", f"Verbunden ({ser.baudrate} Baud)")
    except serial.SerialException as e:
        status_callback(port_name, "fehler", f"Fehler: {e}")
        return

    try:
        while not stop_event.is_set():
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                try:
                    decoded = data.decode("ascii", errors="replace")
                except Exception:
                    decoded = data.hex()
                data_queue.put((port_name, decoded, time.time()))
            else:
                time.sleep(0.05)
    except serial.SerialException as e:
        status_callback(port_name, "fehler", f"Verbindungsfehler: {e}")
    finally:
        try:
            ser.close()
        except Exception:
            pass
        status_callback(port_name, "getrennt", "Getrennt")


class PortMonitor:
    def __init__(self):
        self.threads = {}
        self.stop_events = {}
        self.data_queue = queue.Queue()
        self.config = PORT_CONFIG.copy()
        self.status_callbacks = []
        self.data_callbacks = []
        self._running = False

    def on_status(self, callback):
        self.status_callbacks.append(callback)

    def on_data(self, callback):
        self.data_callbacks.append(callback)

    def _notify_status(self, port, status, message):
        for cb in self.status_callbacks:
            cb(port, status, message)

    def _notify_data(self, port, data, timestamp):
        for cb in self.data_callbacks:
            cb(port, data, timestamp)

    @property
    def is_running(self):
        return self._running

    def start(self, ports=None):
        if self._running:
            return False

        if ports is None:
            ports = get_available_ports()

        if not ports:
            self._notify_status("", "info", "Keine COM-Ports gefunden")
            return False

        self._running = True
        self.data_queue = queue.Queue()

        for port_name in ports:
            stop_event = threading.Event()
            self.stop_events[port_name] = stop_event

            t = threading.Thread(
                target=monitor_port,
                args=(port_name, self.config, self.data_queue, stop_event, self._notify_status),
                daemon=True,
            )
            t.start()
            self.threads[port_name] = t
            self._notify_status(port_name, "starte", "Warte auf Daten...")

        self._poll_thread = threading.Thread(target=self._poll_data, daemon=True)
        self._poll_thread.start()
        return True

    def stop(self):
        if not self._running:
            return
        self._running = False
        for port_name, stop_event in self.stop_events.items():
            stop_event.set()
        self.threads.clear()
        self.stop_events.clear()

    def _poll_data(self):
        while self._running:
            try:
                port_name, data, timestamp = self.data_queue.get(timeout=0.2)
                self._notify_data(port_name, data, timestamp)
            except queue.Empty:
                continue
            except Exception:
                break

    def get_active_port_count(self):
        return len([p for p, t in self.threads.items() if t.is_alive()])
