import sqlite3
import os
import shutil
from datetime import datetime
from src.version import APP_NAME
from src.logger import Logger


class Database:
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

        db_dir = self._get_db_dir()
        os.makedirs(db_dir, exist_ok=True)
        self._db_path = os.path.join(db_dir, f"{APP_NAME}.db")
        self._log = Logger()
        self._init_db()

    def _get_db_dir(self):
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)

    @property
    def db_path(self):
        return self._db_path

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS received_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    port TEXT NOT NULL,
                    data TEXT NOT NULL,
                    raw_hex TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)
            conn.commit()
            self._log.info(f"Datenbank initialisiert: {self._db_path}")
        finally:
            conn.close()

    def save_data(self, port, data, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO received_data (timestamp, port, data, raw_hex) VALUES (?, ?, ?, ?)",
                (timestamp, port, data, data.encode("utf-8").hex())
            )
            conn.commit()
        finally:
            conn.close()

    def save_event(self, level, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (timestamp, level, message) VALUES (?, ?, ?)",
                (timestamp, level, message)
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_data(self, limit=100):
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, port, data FROM received_data ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def get_events(self, limit=100):
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, level, message FROM events ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def backup(self, target_path=None):
        if target_path is None:
            target_path = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                APP_NAME,
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
        shutil.copy2(self._db_path, target_path)
        self._log.info(f"Datenbank-Backup erstellt: {target_path}")
        return target_path

    def restore(self, source_path):
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Backup-Datei nicht gefunden: {source_path}")
        conn = sqlite3.connect(source_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM received_data")
            count = cursor.fetchone()[0]
        finally:
            conn.close()
        shutil.copy2(source_path, self._db_path)
        self._log.info(f"Datenbank wiederhergestellt: {source_path} ({count} Datensätze)")
        return count
