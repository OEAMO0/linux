from __future__ import annotations

import getpass
import os
import pathlib
import shutil
import socket
import subprocess
from typing import Iterable


def is_linux() -> bool:
    return os.name == "posix" and pathlib.Path("/proc").exists()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def read_text(path: str) -> str:
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def run_quick(command: list[str], timeout: int = 4) -> str:
    if not is_linux():
        return "Linux only"
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return "Unavailable"
    output = (completed.stdout or completed.stderr or "").strip()
    return output or "Unavailable"


def parse_os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    for line in read_text("/etc/os-release").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def format_bytes(amount: int) -> str:
    size = float(amount)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024.0 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{amount} B"


def cpu_model() -> str:
    for line in read_text("/proc/cpuinfo").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "Unavailable"


def uptime_human() -> str:
    raw = read_text("/proc/uptime").strip().split()
    if not raw:
        return "Unavailable"
    try:
        total_seconds = int(float(raw[0]))
    except ValueError:
        return "Unavailable"
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def memory_summary() -> str:
    values: dict[str, int] = {}
    for line in read_text("/proc/meminfo").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        chunks = value.strip().split()
        if not chunks:
            continue
        try:
            values[key] = int(chunks[0]) * 1024
        except ValueError:
            continue
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(total - available, 0)
    if not total:
        return "Unavailable"
    return f"{format_bytes(used)} / {format_bytes(total)} used"


def disk_summary(path: str) -> str:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return "Unavailable"
    used = usage.used
    total = usage.total
    percent = (used / total) * 100 if total else 0
    return f"{format_bytes(used)} / {format_bytes(total)} used ({percent:.0f}%)"


def first_line(text: str, fallback: str = "Unavailable") -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return fallback


def joined_non_empty(values: Iterable[str], fallback: str = "Unavailable") -> str:
    items = [value for value in values if value]
    return ", ".join(items) if items else fallback


def default_route() -> str:
    output = run_quick(["ip", "route", "show", "default"])
    return first_line(output)


def dns_summary() -> str:
    resolvectl = run_quick(["resolvectl", "dns"])
    if resolvectl not in {"Unavailable", "Linux only"}:
        return first_line(resolvectl)
    servers: list[str] = []
    for line in read_text("/etc/resolv.conf").splitlines():
        if line.startswith("nameserver"):
            _, _, address = line.partition(" ")
            servers.append(address.strip())
    return joined_non_empty(servers)


def package_helpers() -> str:
    helpers = []
    if command_exists("pacman"):
        helpers.append("pacman")
    if command_exists("yay"):
        helpers.append("yay")
    if command_exists("paru"):
        helpers.append("paru")
    if command_exists("paccache"):
        helpers.append("paccache")
    return joined_non_empty(helpers)


def terminal_support() -> str:
    emulators = [
        "kitty",
        "konsole",
        "gnome-terminal",
        "alacritty",
        "wezterm",
        "xterm",
        "foot",
        "qterminal",
    ]
    present = [name for name in emulators if command_exists(name)]
    return joined_non_empty(present)


def system_summary() -> dict[str, str]:
    release = parse_os_release()
    hostname = socket.gethostname()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "Unknown"
    shell = os.environ.get("SHELL", "Unknown")
    return {
        "Distribution": release.get("PRETTY_NAME", "Unavailable"),
        "Kernel": run_quick(["uname", "-r"]),
        "Hostname": hostname,
        "User": getpass.getuser(),
        "Desktop": desktop,
        "Shell": shell,
        "CPU": cpu_model(),
        "Uptime": uptime_human(),
        "Memory": memory_summary(),
        "Root Disk": disk_summary("/"),
        "Home Disk": disk_summary("/home" if pathlib.Path("/home").exists() else "/"),
        "Package Tools": package_helpers(),
        "Terminal Support": terminal_support(),
    }


def network_summary() -> dict[str, str]:
    return {
        "Addresses": first_line(run_quick(["ip", "-brief", "address"])),
        "Default Route": default_route(),
        "DNS": dns_summary(),
        "Socket Hostname": socket.gethostname(),
    }


def shell_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


def launch_in_terminal(command: str, title: str) -> tuple[bool, str]:
    if not is_linux():
        return False, "Terminal launch is only available on Linux."
    wrapped = (
        f"{command}; status=$?; echo; "
        "printf 'Press Enter to close...'; "
        "read -r _; exit $status"
    )
    candidates = []
    if command_exists("kitty"):
        candidates.append(["kitty", "--title", title, "bash", "-lc", wrapped])
    if command_exists("konsole"):
        candidates.append(["konsole", "-p", f"tabtitle={title}", "-e", "bash", "-lc", wrapped])
    if command_exists("gnome-terminal"):
        candidates.append(["gnome-terminal", f"--title={title}", "--", "bash", "-lc", wrapped])
    if command_exists("alacritty"):
        candidates.append(["alacritty", "--title", title, "-e", "bash", "-lc", wrapped])
    if command_exists("wezterm"):
        candidates.append(["wezterm", "start", "--", "bash", "-lc", wrapped])
    if command_exists("qterminal"):
        candidates.append(["qterminal", "-T", title, "-e", f"bash -lc {shell_quote(wrapped)}"])
    if command_exists("foot"):
        candidates.append(["foot", "-T", title, "bash", "-lc", wrapped])
    if command_exists("xterm"):
        candidates.append(["xterm", "-T", title, "-e", "bash", "-lc", wrapped])
    for command_line in candidates:
        try:
            subprocess.Popen(command_line)
            return True, f"Opened terminal action: {title}"
        except OSError:
            continue
    return False, "No supported terminal emulator was found."


def open_path(path: str) -> tuple[bool, str]:
    expanded = os.path.expanduser(path)
    if not pathlib.Path(expanded).exists():
        return False, f"Path not found: {expanded}"
    if not is_linux():
        return False, "Opening paths is only available on Linux."
    if not command_exists("xdg-open"):
        return False, "xdg-open is not installed."
    try:
        subprocess.Popen(["xdg-open", expanded])
        return True, f"Opened: {expanded}"
    except OSError as exc:
        return False, f"Failed to open path: {exc}"
