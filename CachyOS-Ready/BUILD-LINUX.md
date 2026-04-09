# Build a Linux executable

This project can be turned into a single Linux executable or an AppImage on a Linux machine such as CachyOS.

## 1. Install base tools on CachyOS

```bash
sudo pacman -S --needed python tk python-pip python-virtualenv base-devel
```

`appimagetool` is only needed if you want an AppImage:

```bash
yay -S --needed appimagetool
```

## 2. Build a single-file Linux executable

```bash
cd /path/to/CachyOS-Ready
chmod +x build-linux-binary.sh
./build-linux-binary.sh
```

Result:

```bash
./Linux-Build/cachy-helper
```

## 3. Build an AppImage

```bash
cd /path/to/CachyOS-Ready
chmod +x build-linux-appimage.sh
./build-linux-appimage.sh
```

Result:

```bash
./CachyOS-Control-Center-x86_64.AppImage
```

## Notes

- The Linux binary must be built on Linux for best compatibility.
- Building it from Windows into a real Linux executable is not supported by this setup.
- The standalone executable is the closest Linux equivalent to an `exe`.
