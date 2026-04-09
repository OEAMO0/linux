# CachyOS Control Center

A desktop helper written in Python for Linux and especially Arch/CachyOS systems.

## What it includes

- System dashboard with distro, kernel, CPU, memory, disks, and quick network snapshot
- Maintenance actions for `pacman`, `yay`, `paccache`, `journalctl`, `systemctl`, and Btrfs
- Package center for searching repositories, reading package info, and opening install/remove actions in a real terminal
- Service manager for `systemd`
- Network tools for ping, routes, interfaces, sockets, and DNS lookup
- Toolbox for opening common config paths and running custom commands

## Why this is CachyOS-friendly

- It uses Python standard library only for the UI
- It avoids extra Python dependencies
- Root actions open in a terminal so `sudo` prompts work normally
- The setup script installs recommended Arch/CachyOS runtime packages

## Folder layout

- `app.py` root launcher for easier local startup
- `CachyOS-Helper/` application source
- `run-cachy-helper.sh` run directly from this folder
- `setup-cachy-helper.sh` install for the current user with launcher and desktop entry
- `uninstall-cachy-helper.sh` remove the local installation
- `build-linux-binary.sh` build a single Linux executable
- `build-linux-appimage.sh` build an AppImage

## Quick start on CachyOS

```bash
cd /path/to/CachyOS-Ready
chmod +x run-cachy-helper.sh setup-cachy-helper.sh uninstall-cachy-helper.sh
./run-cachy-helper.sh
```

You can also launch it directly with:

```bash
python app.py
```

## Install locally for one user

```bash
cd /path/to/CachyOS-Ready
chmod +x setup-cachy-helper.sh
./setup-cachy-helper.sh
```

After installation you can start it from the app menu or by running:

```bash
cachy-helper
```

## Recommended packages on CachyOS

```bash
sudo pacman -S --needed python tk xdg-utils inetutils bind pacman-contrib
```

`yay` is optional but recommended if you want AUR search and AUR updates.

## Build a Linux executable

If you want a Linux file that behaves more like an `.exe`, use the build scripts:

```bash
cd /path/to/CachyOS-Ready
chmod +x build-linux-binary.sh build-linux-appimage.sh
./build-linux-binary.sh
```

That generates:

```bash
./Linux-Build/cachy-helper
```

For a single portable AppImage file:

```bash
./build-linux-appimage.sh
```

Full build details are in `BUILD-LINUX.md`.

## Notes

- The app can open on non-Linux systems for inspection, but command execution is Linux-only.
- Interactive tasks rely on a terminal emulator such as `kitty`, `konsole`, `gnome-terminal`, `alacritty`, `wezterm`, `qterminal`, `foot`, or `xterm`.
