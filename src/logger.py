import os
import logging
from datetime import datetime
from src.version import APP_NAME


class Logger:
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

        log_dir = self._get_log_dir()
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"{APP_NAME}.log")
        self._file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        self._file_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%d.%m.%Y %H:%M:%S")
        )

        self._logger = logging.getLogger(APP_NAME)
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()
        self._logger.addHandler(self._file_handler)

        self._log_path = log_file
        self.info(f"{APP_NAME} Logger gestartet")

    def _get_log_dir(self):
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME, "logs")

    @property
    def log_path(self):
        return self._log_path

    def info(self, message):
        self._logger.info(message)

    def warning(self, message):
        self._logger.warning(message)

    def error(self, message):
        self._logger.error(message)

    def debug(self, message):
        self._logger.debug(message)

    def open_log(self):
        os.startfile(self._log_path)
