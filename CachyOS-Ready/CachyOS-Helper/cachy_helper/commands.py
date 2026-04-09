from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActionSpec:
    label: str
    description: str
    command: str
    needs_terminal: bool = False
    availability: tuple[str, ...] = field(default_factory=tuple)


def maintenance_actions() -> list[ActionSpec]:
    return [
        ActionSpec(
            label="Full System Update",
            description="Run pacman system upgrade in a real terminal.",
            command="sudo pacman -Syu",
            needs_terminal=True,
            availability=("pacman",),
        ),
        ActionSpec(
            label="AUR Update",
            description="Upgrade AUR packages with yay when available.",
            command="yay -Sua --devel",
            needs_terminal=True,
            availability=("yay",),
        ),
        ActionSpec(
            label="Clean Package Cache",
            description="Remove old package cache copies with paccache.",
            command="sudo paccache -rk2",
            needs_terminal=True,
            availability=("paccache",),
        ),
        ActionSpec(
            label="Remove Orphans",
            description="Remove orphaned packages if any are installed.",
            command="orphans=$(pacman -Qtdq); if [ -n \"$orphans\" ]; then sudo pacman -Rns $orphans; else echo 'No orphan packages found.'; fi",
            needs_terminal=True,
            availability=("pacman",),
        ),
        ActionSpec(
            label="Show Failed Services",
            description="List services that failed during the current boot.",
            command="systemctl --failed --no-pager",
            availability=("systemctl",),
        ),
        ActionSpec(
            label="Boot Analysis",
            description="Inspect services slowing boot time.",
            command="systemd-analyze blame",
            availability=("systemd-analyze",),
        ),
        ActionSpec(
            label="Journal Errors",
            description="Show boot errors from the system journal.",
            command="journalctl -p 3 -xb --no-pager",
            availability=("journalctl",),
        ),
        ActionSpec(
            label="Recent Pacman Log",
            description="Display the latest package manager operations.",
            command="tail -n 80 /var/log/pacman.log",
        ),
        ActionSpec(
            label="Btrfs Usage",
            description="Summarize Btrfs filesystem usage when available.",
            command="btrfs filesystem usage /",
            availability=("btrfs",),
        ),
    ]


def toolbox_actions() -> list[ActionSpec]:
    return [
        ActionSpec(
            label="Block Devices",
            description="Show disks, filesystems, and mount points.",
            command="lsblk -f",
            availability=("lsblk",),
        ),
        ActionSpec(
            label="Memory Overview",
            description="Display RAM and swap usage.",
            command="free -h",
            availability=("free",),
        ),
        ActionSpec(
            label="Top Memory Processes",
            description="List the heaviest memory users.",
            command="ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n 20",
            availability=("ps",),
        ),
        ActionSpec(
            label="Large Home Cache Entries",
            description="Inspect the largest files under ~/.cache.",
            command="du -sh ~/.cache/* 2>/dev/null | sort -h | tail -n 25",
            availability=("du", "sort", "tail"),
        ),
        ActionSpec(
            label="Open TCP/UDP Sockets",
            description="Show listening ports and owning processes.",
            command="ss -tulpn",
            availability=("ss",),
        ),
        ActionSpec(
            label="Last 200 Journal Lines",
            description="Read the most recent journal entries.",
            command="journalctl -b -n 200 --no-pager",
            availability=("journalctl",),
        ),
    ]


def open_paths() -> list[tuple[str, str]]:
    return [
        ("Open /etc", "/etc"),
        ("Open Home", "~"),
        ("Open ~/.config", "~/.config"),
        ("Open pacman.conf", "/etc/pacman.conf"),
        ("Open pacman.log", "/var/log/pacman.log"),
        ("Open fstab", "/etc/fstab"),
    ]
