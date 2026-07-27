import json
import os
import subprocess
import sys
import tempfile
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError
from src.version import VERSION, APP_NAME

GITHUB_REPO = "soendi/COMchecker"
API_RELEASES = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=10"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/version.json"


def parse_version(version_str):
    parts = version_str.strip("vV").split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def compare_versions(v1, v2):
    v1_parts = parse_version(v1)
    v2_parts = parse_version(v2)
    if v1_parts is None or v2_parts is None:
        return None
    if v1_parts > v2_parts:
        return 1
    elif v1_parts < v2_parts:
        return -1
    return 0


def get_current_version():
    return VERSION


def check_for_update(progress_callback=None):
    try:
        req = Request(API_RELEASES, headers={"User-Agent": f"{APP_NAME}/{VERSION}"})
        with urlopen(req, timeout=10) as resp:
            releases = json.loads(resp.read().decode("utf-8"))

        latest_version = None
        for release in releases:
            if release.get("prerelease") or release.get("draft"):
                continue
            tag = release.get("tag_name", "")
            ver = tag.strip("vV")
            if parse_version(ver) is not None:
                if latest_version is None or compare_versions(ver, latest_version) == 1:
                    latest_version = ver

        if latest_version and compare_versions(latest_version, VERSION) == 1:
            return ("api", latest_version, f"Neue Version {latest_version} verf\u00fcgbar")

        return None

    except URLError:
        pass
    except Exception:
        pass

    try:
        req = Request(VERSION_URL, headers={"User-Agent": f"{APP_NAME}/{VERSION}"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ver = data.get("version", "")

        if ver and compare_versions(ver, VERSION) == 1:
            return ("fallback", ver, f"Neue Version {ver} verf\u00fcgbar")

        return None

    except Exception:
        return None


def download_installer(version, progress_callback=None):
    temp_dir = os.path.join(tempfile.gettempdir(), f"{APP_NAME}Update")
    os.makedirs(temp_dir, exist_ok=True)

    installer_name = f"{APP_NAME}-Setup.exe"
    installer_path = os.path.join(temp_dir, installer_name)

    download_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/{installer_name}"

    try:
        req = Request(download_url, headers={"User-Agent": f"{APP_NAME}/{VERSION}"})
        with urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 8192

            with open(installer_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0 and progress_callback:
                        progress_callback(downloaded / total)

        return installer_path

    except Exception as e:
        raise RuntimeError(f"Download fehlgeschlagen: {e}")


def run_update(version, progress_callback=None, done_callback=None):

    def _do_update():
        try:
            progress_callback(0.0)
            installer_path = download_installer(version, progress_callback)
            progress_callback(1.0)

            if done_callback:
                done_callback(True, None)

            exe_path = os.path.abspath(sys.argv[0])

            ps_cmd = (
                f'Start-Sleep -Seconds 3; '
                f'Start-Process "{installer_path}" -ArgumentList "/SILENT" -Wait -Verb RunAs; '
                f'Start-Process "{exe_path}"'
            )

            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-Command", ps_cmd],
                shell=False,
                creationflags=0x08000000,
            )

            sys.exit(0)

        except Exception as e:
            if done_callback:
                done_callback(False, str(e))

    threading.Thread(target=_do_update, daemon=True).start()
