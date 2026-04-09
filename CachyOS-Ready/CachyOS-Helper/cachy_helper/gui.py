from __future__ import annotations

import queue
import shlex
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .commands import ActionSpec, maintenance_actions, open_paths, toolbox_actions
from .system_data import (
    command_exists,
    is_linux,
    launch_in_terminal,
    network_summary,
    open_path,
    shell_quote,
    system_summary,
)


class CommandRunner:
    def __init__(self) -> None:
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()

    def log(self, message: str) -> None:
        self.events.put(("log", message))

    def status(self, message: str) -> None:
        self.events.put(("status", message))

    def run_shell_capture(self, title: str, command: str) -> None:
        self.log(f"\n$ {command}\n")
        worker = threading.Thread(target=self._capture_worker, args=(title, command), daemon=True)
        worker.start()

    def _capture_worker(self, title: str, command: str) -> None:
        if not is_linux():
            self.log("This command runner works only on Linux.\n")
            self.status("Linux environment required for command execution.")
            return
        self.status(f"Running: {title}")
        try:
            completed = subprocess.run(
                ["/bin/bash", "-lc", command],
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            self.log("Command timed out after 600 seconds.\n")
            self.status(f"Timed out: {title}")
            return
        except OSError as exc:
            self.log(f"Failed to run command: {exc}\n")
            self.status(f"Execution failed: {title}")
            return
        if completed.stdout:
            self.log(completed.stdout.rstrip() + "\n")
        if completed.stderr:
            self.log("[stderr]\n" + completed.stderr.rstrip() + "\n")
        self.log(f"[exit code] {completed.returncode}\n")
        self.status(f"Finished: {title}")

    def run_terminal_action(self, title: str, command: str) -> None:
        self.log(f"\n$ {command}\n")
        success, message = launch_in_terminal(command, title)
        self.status(message)
        if not success:
            self.log(message + "\n")


class CachyHelperApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CachyOS Control Center")
        self.geometry("1200x820")
        self.minsize(980, 720)

        self.runner = CommandRunner()
        self.status_var = tk.StringVar(value="Ready")
        self.custom_command_var = tk.StringVar()
        self.package_query_var = tk.StringVar()
        self.service_name_var = tk.StringVar(value="NetworkManager.service")
        self.ping_host_var = tk.StringVar(value="1.1.1.1")
        self.dns_query_var = tk.StringVar(value="archlinux.org")
        self.summary_vars: dict[str, tk.StringVar] = {}
        self.network_vars: dict[str, tk.StringVar] = {}

        self._configure_style()
        self._build_layout()
        self.refresh_dashboard()
        self.after(150, self._poll_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.configure(bg="#edf2ef")
        style.configure("Root.TFrame", background="#edf2ef")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("Header.TFrame", background="#144d3d")
        style.configure("HeaderTitle.TLabel", background="#144d3d", foreground="#ffffff", font=("Segoe UI", 21, "bold"))
        style.configure("HeaderBody.TLabel", background="#144d3d", foreground="#d7efe8", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#ffffff", foreground="#144d3d", font=("Segoe UI", 12, "bold"))
        style.configure("Key.TLabel", background="#ffffff", foreground="#4b5a56", font=("Segoe UI", 10, "bold"))
        style.configure("Value.TLabel", background="#ffffff", foreground="#1f2a27", font=("Segoe UI", 10))
        style.configure("Status.TLabel", background="#edf2ef", foreground="#395049", font=("Segoe UI", 9))
        style.configure("Notebook.TNotebook", background="#edf2ef", borderwidth=0)
        style.configure("Notebook.TNotebook.Tab", padding=(12, 8), font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        root = ttk.Frame(self, style="Root.TFrame", padding=14)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Header.TFrame", padding=(18, 18))
        header.pack(fill="x")
        ttk.Label(header, text="CachyOS Control Center", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "A desktop helper for Linux and CachyOS: updates, package search, services, "
                "network tools, quick diagnostics, and one-click launchers."
            ),
            style="HeaderBody.TLabel",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Panedwindow(root, orient="vertical")
        body.pack(fill="both", expand=True, pady=(14, 0))

        top_frame = ttk.Frame(body, style="Root.TFrame")
        bottom_frame = ttk.Frame(body, style="Root.TFrame")
        body.add(top_frame, weight=4)
        body.add(bottom_frame, weight=2)

        self.notebook = ttk.Notebook(top_frame, style="Notebook.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self._build_dashboard_tab()
        self._build_maintenance_tab()
        self._build_packages_tab()
        self._build_services_tab()
        self._build_network_tab()
        self._build_toolbox_tab()

        self.log_box = scrolledtext.ScrolledText(
            bottom_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#111715",
            fg="#d8f4ea",
            insertbackground="#d8f4ea",
            relief="flat",
            padx=10,
            pady=10,
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.insert(
            "end",
            "Command output will appear here.\n"
            "Read-only commands run inside the app. Root or interactive actions open in a terminal.\n",
        )
        self.log_box.configure(state="disabled")

        footer = ttk.Frame(root, style="Root.TFrame")
        footer.pack(fill="x", pady=(8, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").pack(side="left")
        ttk.Button(footer, text="Refresh Dashboard", command=self.refresh_dashboard).pack(side="right")

        if not is_linux():
            self.status_var.set("Running outside Linux. The UI opens, but command execution is disabled.")

    def _new_tab(self, title: str) -> ttk.Frame:
        frame = ttk.Frame(self.notebook, style="Root.TFrame", padding=12)
        self.notebook.add(frame, text=title)
        return frame

    def _build_dashboard_tab(self) -> None:
        tab = self._new_tab("Dashboard")

        top = ttk.Frame(tab, style="Root.TFrame")
        top.pack(fill="x")

        summary_card = ttk.Frame(top, style="Card.TFrame", padding=16)
        summary_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ttk.Label(summary_card, text="System Overview", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        summary_keys = [
            "Distribution",
            "Kernel",
            "Hostname",
            "User",
            "Desktop",
            "Shell",
            "CPU",
            "Uptime",
            "Memory",
            "Root Disk",
            "Home Disk",
            "Package Tools",
            "Terminal Support",
        ]
        for index, key in enumerate(summary_keys, start=1):
            self.summary_vars[key] = tk.StringVar(value="Loading...")
            ttk.Label(summary_card, text=f"{key}:", style="Key.TLabel").grid(row=index, column=0, sticky="nw", pady=4, padx=(0, 12))
            ttk.Label(summary_card, textvariable=self.summary_vars[key], style="Value.TLabel", wraplength=500, justify="left").grid(
                row=index, column=1, sticky="nw", pady=4
            )

        quick_card = ttk.Frame(top, style="Card.TFrame", padding=16)
        quick_card.pack(side="left", fill="y")
        ttk.Label(quick_card, text="Quick Actions", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            quick_card,
            text="These are good first checks on a fresh CachyOS install or when troubleshooting.",
            style="Value.TLabel",
            wraplength=260,
            justify="left",
        ).pack(anchor="w", pady=(6, 10))

        quick_actions = [
            ActionSpec("Check Failed Services", "List systemd failures.", "systemctl --failed --no-pager", availability=("systemctl",)),
            ActionSpec("Show Journal Errors", "Read recent error-level logs.", "journalctl -p 3 -xb --no-pager", availability=("journalctl",)),
            ActionSpec("Show Block Devices", "Inspect mounted drives and filesystems.", "lsblk -f", availability=("lsblk",)),
            ActionSpec("Run System Update", "Launch pacman update in terminal.", "sudo pacman -Syu", needs_terminal=True, availability=("pacman",)),
        ]
        for spec in quick_actions:
            ttk.Button(quick_card, text=spec.label, command=lambda action=spec: self.run_action(action)).pack(fill="x", pady=4)

        network_card = ttk.Frame(tab, style="Card.TFrame", padding=16)
        network_card.pack(fill="x", pady=(12, 0))
        ttk.Label(network_card, text="Network Snapshot", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        for index, key in enumerate(["Addresses", "Default Route", "DNS", "Socket Hostname"], start=1):
            self.network_vars[key] = tk.StringVar(value="Loading...")
            ttk.Label(network_card, text=f"{key}:", style="Key.TLabel").grid(row=index, column=0, sticky="nw", pady=4, padx=(0, 12))
            ttk.Label(network_card, textvariable=self.network_vars[key], style="Value.TLabel", wraplength=760, justify="left").grid(
                row=index, column=1, sticky="nw", pady=4
            )

        actions = ttk.Frame(tab, style="Root.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Copy System Report", command=self.copy_report).pack(side="left")

    def _build_maintenance_tab(self) -> None:
        tab = self._new_tab("Maintenance")
        ttk.Label(tab, text="Update and cleanup actions", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            tab,
            text="Read-only checks print inside the app. Tasks that need sudo or password prompts open in your terminal emulator.",
            style="Value.TLabel",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(4, 12))

        grid = ttk.Frame(tab, style="Root.TFrame")
        grid.pack(fill="both", expand=True)

        for index, spec in enumerate(maintenance_actions()):
            card = ttk.Frame(grid, style="Card.TFrame", padding=16)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)
            grid.columnconfigure(index % 2, weight=1)
            ttk.Label(card, text=spec.label, style="Section.TLabel").pack(anchor="w")
            ttk.Label(card, text=spec.description, style="Value.TLabel", wraplength=420, justify="left").pack(anchor="w", pady=(6, 10))
            ttk.Button(card, text="Run", command=lambda action=spec: self.run_action(action)).pack(anchor="w")

    def _build_packages_tab(self) -> None:
        tab = self._new_tab("Packages")
        query_card = ttk.Frame(tab, style="Card.TFrame", padding=16)
        query_card.pack(fill="x")

        ttk.Label(query_card, text="Package Center", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            query_card,
            text="Search repositories, inspect a package, then install or remove it in a real terminal.",
            style="Value.TLabel",
            wraplength=860,
            justify="left",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 10))

        ttk.Label(query_card, text="Package name or search query:", style="Key.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(query_card, textvariable=self.package_query_var, width=48).grid(row=2, column=1, sticky="ew", padx=(10, 10))
        query_card.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(query_card, style="Card.TFrame")
        button_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        buttons = [
            ("Search Pacman", self.search_pacman),
            ("Search AUR", self.search_aur),
            ("Package Info", self.package_info),
            ("Install", self.install_package),
            ("Remove", self.remove_package),
        ]
        for index, (label, callback) in enumerate(buttons):
            ttk.Button(button_frame, text=label, command=callback).grid(row=index // 3, column=index % 3, sticky="ew", pady=4, padx=4)
            button_frame.columnconfigure(index % 3, weight=1)

        note_card = ttk.Frame(tab, style="Card.TFrame", padding=16)
        note_card.pack(fill="x", pady=(12, 0))
        ttk.Label(note_card, text="Hints", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            note_card,
            text=(
                "Use exact package names for install/remove. Multiple packages are supported for install/remove "
                "if you separate them with spaces. AUR search needs yay."
            ),
            style="Value.TLabel",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

    def _build_services_tab(self) -> None:
        tab = self._new_tab("Services")
        card = ttk.Frame(tab, style="Card.TFrame", padding=16)
        card.pack(fill="x")

        ttk.Label(card, text="Service Manager", style="Section.TLabel").grid(row=0, column=0, columnspan=5, sticky="w")
        ttk.Label(
            card,
            text="Enter a systemd service name such as NetworkManager.service or sshd.service.",
            style="Value.TLabel",
            wraplength=860,
            justify="left",
        ).grid(row=1, column=0, columnspan=5, sticky="w", pady=(6, 10))

        ttk.Label(card, text="Service:", style="Key.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(card, textvariable=self.service_name_var, width=40).grid(row=2, column=1, sticky="ew", padx=(10, 14))
        card.columnconfigure(1, weight=1)

        service_buttons = [
            ("Status", self.service_status),
            ("Logs", self.service_logs),
            ("Start", self.service_start),
            ("Restart", self.service_restart),
            ("Stop", self.service_stop),
            ("Enable", self.service_enable),
            ("Disable", self.service_disable),
            ("List Running", self.list_running_services),
            ("List Failed", self.list_failed_services),
        ]
        button_grid = ttk.Frame(tab, style="Root.TFrame")
        button_grid.pack(fill="x", pady=(12, 0))
        for index, (label, callback) in enumerate(service_buttons):
            ttk.Button(button_grid, text=label, command=callback).grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
            button_grid.columnconfigure(index % 3, weight=1)

    def _build_network_tab(self) -> None:
        tab = self._new_tab("Network")

        ping_card = ttk.Frame(tab, style="Card.TFrame", padding=16)
        ping_card.pack(fill="x")
        ttk.Label(ping_card, text="Connectivity Tools", style="Section.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(ping_card, text="Host to ping:", style="Key.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(ping_card, textvariable=self.ping_host_var, width=28).grid(row=1, column=1, sticky="w", padx=(10, 16), pady=(8, 0))
        ttk.Label(ping_card, text="DNS query:", style="Key.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(ping_card, textvariable=self.dns_query_var, width=28).grid(row=1, column=3, sticky="w", padx=(10, 0), pady=(8, 0))

        net_buttons = [
            ("Refresh Snapshot", self.refresh_dashboard),
            ("Ping Host", self.ping_host),
            ("DNS Lookup", self.lookup_dns),
            ("Show Routes", self.show_routes),
            ("Show Interfaces", self.show_interfaces),
            ("Show Sockets", self.show_sockets),
        ]
        controls = ttk.Frame(tab, style="Root.TFrame")
        controls.pack(fill="x", pady=(12, 0))
        for index, (label, callback) in enumerate(net_buttons):
            ttk.Button(controls, text=label, command=callback).grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
            controls.columnconfigure(index % 3, weight=1)

    def _build_toolbox_tab(self) -> None:
        tab = self._new_tab("Toolbox")
        upper = ttk.Frame(tab, style="Root.TFrame")
        upper.pack(fill="x")

        path_card = ttk.Frame(upper, style="Card.TFrame", padding=16)
        path_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        ttk.Label(path_card, text="Open Common Paths", style="Section.TLabel").pack(anchor="w")
        ttk.Label(path_card, text="Jump directly to config files and folders.", style="Value.TLabel").pack(anchor="w", pady=(6, 10))
        for label, path in open_paths():
            ttk.Button(path_card, text=label, command=lambda target=path: self.open_common_path(target)).pack(fill="x", pady=4)

        custom_card = ttk.Frame(upper, style="Card.TFrame", padding=16)
        custom_card.pack(side="left", fill="both", expand=True)
        ttk.Label(custom_card, text="Custom Command", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            custom_card,
            text="Run any custom Linux command either inside the app or in a real terminal.",
            style="Value.TLabel",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(6, 10))
        ttk.Entry(custom_card, textvariable=self.custom_command_var).pack(fill="x")
        buttons = ttk.Frame(custom_card, style="Card.TFrame")
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Run Here", command=self.run_custom_capture).pack(side="left")
        ttk.Button(buttons, text="Run In Terminal", command=self.run_custom_terminal).pack(side="left", padx=(8, 0))

        lower = ttk.Frame(tab, style="Root.TFrame")
        lower.pack(fill="both", expand=True, pady=(12, 0))
        for index, spec in enumerate(toolbox_actions()):
            card = ttk.Frame(lower, style="Card.TFrame", padding=16)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)
            lower.columnconfigure(index % 2, weight=1)
            ttk.Label(card, text=spec.label, style="Section.TLabel").pack(anchor="w")
            ttk.Label(card, text=spec.description, style="Value.TLabel", wraplength=430, justify="left").pack(anchor="w", pady=(6, 10))
            ttk.Button(card, text="Run", command=lambda action=spec: self.run_action(action)).pack(anchor="w")

    def _append_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _poll_events(self) -> None:
        while True:
            try:
                kind, payload = self.runner.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._append_log(payload)
            elif kind == "status":
                self.status_var.set(payload)
        self.after(150, self._poll_events)

    def refresh_dashboard(self) -> None:
        summary = system_summary()
        for key, variable in self.summary_vars.items():
            variable.set(summary.get(key, "Unavailable"))

        network = network_summary()
        for key, variable in self.network_vars.items():
            variable.set(network.get(key, "Unavailable"))

        if is_linux():
            self.status_var.set("Dashboard refreshed")
        else:
            self.status_var.set("Dashboard loaded in compatibility mode")

    def copy_report(self) -> None:
        lines = ["CachyOS Control Center report", ""]
        for key, variable in self.summary_vars.items():
            lines.append(f"{key}: {variable.get()}")
        lines.append("")
        for key, variable in self.network_vars.items():
            lines.append(f"{key}: {variable.get()}")
        report = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(report)
        self.status_var.set("System report copied to clipboard")

    def _ensure_available(self, spec: ActionSpec) -> bool:
        if not is_linux():
            messagebox.showwarning("Linux required", "This action can only run on Linux.")
            return False
        missing = [name for name in spec.availability if not command_exists(name)]
        if missing:
            messagebox.showwarning(
                "Missing command",
                f"This action needs: {', '.join(missing)}",
            )
            return False
        return True

    def run_action(self, spec: ActionSpec) -> None:
        if not self._ensure_available(spec):
            return
        if spec.needs_terminal:
            self.runner.run_terminal_action(spec.label, spec.command)
        else:
            self.runner.run_shell_capture(spec.label, spec.command)

    def _package_query(self) -> str:
        query = self.package_query_var.get().strip()
        if not query:
            messagebox.showinfo("Package query", "Enter a package name or search query first.")
            return ""
        return query

    def _package_tokens(self) -> list[str]:
        query = self._package_query()
        if not query:
            return []
        try:
            return shlex.split(query)
        except ValueError:
            messagebox.showerror("Invalid package text", "The package list could not be parsed.")
            return []

    def search_pacman(self) -> None:
        query = self._package_query()
        if not query:
            return
        if not command_exists("pacman"):
            messagebox.showwarning("Missing pacman", "pacman was not found on this system.")
            return
        self.runner.run_shell_capture("Search Pacman", f"pacman -Ss {shell_quote(query)}")

    def search_aur(self) -> None:
        query = self._package_query()
        if not query:
            return
        if not command_exists("yay"):
            messagebox.showwarning("Missing yay", "yay is required for AUR searches.")
            return
        self.runner.run_shell_capture("Search AUR", f"yay -Ss {shell_quote(query)}")

    def package_info(self) -> None:
        query = self._package_query()
        if not query:
            return
        if not command_exists("pacman"):
            messagebox.showwarning("Missing pacman", "pacman was not found on this system.")
            return
        self.runner.run_shell_capture("Package Info", f"pacman -Si {shell_quote(query)}")

    def install_package(self) -> None:
        tokens = self._package_tokens()
        if not tokens:
            return
        if not command_exists("pacman"):
            messagebox.showwarning("Missing pacman", "pacman was not found on this system.")
            return
        quoted = " ".join(shell_quote(token) for token in tokens)
        self.runner.run_terminal_action("Install Package", f"sudo pacman -S --needed {quoted}")

    def remove_package(self) -> None:
        tokens = self._package_tokens()
        if not tokens:
            return
        if not command_exists("pacman"):
            messagebox.showwarning("Missing pacman", "pacman was not found on this system.")
            return
        quoted = " ".join(shell_quote(token) for token in tokens)
        self.runner.run_terminal_action("Remove Package", f"sudo pacman -Rns {quoted}")

    def _service_name(self) -> str:
        raw = self.service_name_var.get().strip()
        if not raw:
            messagebox.showinfo("Service name", "Enter a service name first.")
            return ""
        if "." not in raw:
            return raw + ".service"
        return raw

    def service_status(self) -> None:
        service = self._service_name()
        if service:
            self.runner.run_shell_capture("Service Status", f"systemctl status {shell_quote(service)} --no-pager")

    def service_logs(self) -> None:
        service = self._service_name()
        if service:
            self.runner.run_shell_capture("Service Logs", f"journalctl -u {shell_quote(service)} -b -n 120 --no-pager")

    def service_start(self) -> None:
        self._service_terminal_action("Start Service", "start")

    def service_restart(self) -> None:
        self._service_terminal_action("Restart Service", "restart")

    def service_stop(self) -> None:
        self._service_terminal_action("Stop Service", "stop")

    def service_enable(self) -> None:
        self._service_terminal_action("Enable Service", "enable")

    def service_disable(self) -> None:
        self._service_terminal_action("Disable Service", "disable")

    def _service_terminal_action(self, title: str, action: str) -> None:
        service = self._service_name()
        if not service:
            return
        if not command_exists("systemctl"):
            messagebox.showwarning("Missing systemctl", "systemctl was not found on this system.")
            return
        self.runner.run_terminal_action(title, f"sudo systemctl {action} {shell_quote(service)}")

    def list_running_services(self) -> None:
        self.runner.run_shell_capture(
            "Running Services",
            "systemctl list-units --type=service --state=running --no-pager",
        )

    def list_failed_services(self) -> None:
        self.runner.run_shell_capture("Failed Services", "systemctl --failed --no-pager")

    def ping_host(self) -> None:
        host = self.ping_host_var.get().strip()
        if not host:
            messagebox.showinfo("Host", "Enter a host or IP address to ping.")
            return
        if not command_exists("ping"):
            messagebox.showwarning("Missing ping", "Install inetutils to use ping.")
            return
        self.runner.run_shell_capture("Ping Host", f"ping -c 4 {shell_quote(host)}")

    def lookup_dns(self) -> None:
        target = self.dns_query_var.get().strip()
        if not target:
            messagebox.showinfo("DNS query", "Enter a hostname first.")
            return
        if command_exists("resolvectl"):
            self.runner.run_shell_capture("DNS Lookup", f"resolvectl query {shell_quote(target)}")
            return
        if command_exists("getent"):
            self.runner.run_shell_capture("DNS Lookup", f"getent ahosts {shell_quote(target)}")
            return
        messagebox.showwarning("No DNS tool", "Install systemd-resolved or use getent.")

    def show_routes(self) -> None:
        self.runner.run_shell_capture("Routes", "ip route")

    def show_interfaces(self) -> None:
        self.runner.run_shell_capture("Interfaces", "ip -brief address")

    def show_sockets(self) -> None:
        self.runner.run_shell_capture("Sockets", "ss -tulpn")

    def open_common_path(self, path: str) -> None:
        success, message = open_path(path)
        self.status_var.set(message)
        if not success:
            self._append_log(message + "\n")

    def run_custom_capture(self) -> None:
        command = self.custom_command_var.get().strip()
        if not command:
            messagebox.showinfo("Custom command", "Enter a command first.")
            return
        self.runner.run_shell_capture("Custom Command", command)

    def run_custom_terminal(self) -> None:
        command = self.custom_command_var.get().strip()
        if not command:
            messagebox.showinfo("Custom command", "Enter a command first.")
            return
        self.runner.run_terminal_action("Custom Command", command)


def main() -> int:
    app = CachyHelperApp()
    app.mainloop()
    return 0
