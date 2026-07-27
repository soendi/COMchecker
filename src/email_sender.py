import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from src.settings import Settings


class EmailSender:
    def __init__(self):
        self.settings = Settings()

    def get_config(self):
        return {
            "server": self.settings.get("email_server", ""),
            "port": self.settings.get("email_port", 587),
            "encryption": self.settings.get("email_encryption", "STARTTLS"),
            "username": self.settings.get("email_username", ""),
            "password": self.settings.get("email_password", ""),
            "sender": self.settings.get("email_sender", ""),
        }

    def save_config(self, config):
        for key, value in config.items():
            self.settings.set(f"email_{key}", value)

    def test_connection(self):
        config = self.get_config()
        if not config["server"] or not config["username"] or not config["password"]:
            return False, "Server, Benutzername und Passwort müssen angegeben werden."

        try:
            if config["encryption"] == "SSL":
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(config["server"], config["port"], context=context, timeout=10)
            else:
                server = smtplib.SMTP(config["server"], config["port"], timeout=10)
                if config["encryption"] == "STARTTLS":
                    server.starttls(context=ssl.create_default_context())

            server.login(config["username"], config["password"])
            server.quit()
            return True, "Verbindung erfolgreich!"
        except Exception as e:
            return False, str(e)

    def send_log(self, log_path, recipient=None):
        config = self.get_config()
        if recipient is None:
            recipient = config.get("sender", "")

        if not recipient:
            return False, "Kein Empfänger angegeben."

        if not os.path.exists(log_path):
            return False, "Logdatei nicht gefunden."

        msg = MIMEMultipart()
        msg["From"] = config["sender"]
        msg["To"] = recipient
        msg["Subject"] = f"COMchecker Logdatei"

        body = MIMEText("Anbei die Logdatei von COMchecker.", "plain", "utf-8")
        msg.attach(body)

        with open(log_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(log_path)}")
            msg.attach(part)

        try:
            if config["encryption"] == "SSL":
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(config["server"], config["port"], context=context, timeout=10)
            else:
                server = smtplib.SMTP(config["server"], config["port"], timeout=10)
                if config["encryption"] == "STARTTLS":
                    server.starttls(context=ssl.create_default_context())

            server.login(config["username"], config["password"])
            server.send_message(msg)
            server.quit()
            return True, "Logdatei erfolgreich gesendet!"
        except Exception as e:
            return False, str(e)

    def send_text(self, recipient, subject, text):
        config = self.get_config()
        if not recipient:
            return False, "Kein Empfänger angegeben."

        msg = MIMEText(text, "plain", "utf-8")
        msg["From"] = config["sender"]
        msg["To"] = recipient
        msg["Subject"] = subject

        try:
            if config["encryption"] == "SSL":
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(config["server"], config["port"], context=context, timeout=10)
            else:
                server = smtplib.SMTP(config["server"], config["port"], timeout=10)
                if config["encryption"] == "STARTTLS":
                    server.starttls(context=ssl.create_default_context())

            server.login(config["username"], config["password"])
            server.send_message(msg)
            server.quit()
            return True, "E-Mail erfolgreich gesendet!"
        except Exception as e:
            return False, str(e)
