# Building FreeWili Updater as a Flatpak

## Prerequisites

Install the required tools and runtimes:

```bash
# Install flatpak-builder
sudo pacman -S flatpak flatpak-builder  # Arch Linux
# or: sudo apt install flatpak flatpak-builder  # Debian/Ubuntu

# Add Flathub repository if not already added
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install required runtimes and SDKs
flatpak install flathub org.gnome.Platform//49 org.gnome.Sdk//49 \
    org.freedesktop.Sdk.Extension.rust-stable//25.08 \
    org.freedesktop.Sdk.Extension.llvm21//25.08 -y
```

## Building

### Initial Build

For the first build or when you want a clean build:

```bash
flatpak-builder --force-clean build-dir com.freewili.updater.yml
```

### Incremental Build

For faster rebuilds when only changing source code:

```bash
flatpak-builder build-dir com.freewili.updater.yml
```

### Testing

Test run directly from the build directory:

```bash
flatpak-builder --run build-dir com.freewili.updater.yml freewili-updater
```

## Installing Locally

Install the Flatpak to your user account:

```bash
flatpak-builder --user --install --force-clean build-dir com.freewili.updater.yml
```

Then run it:

```bash
flatpak run com.freewili.updater
```

## Creating a Distributable Package

To create a `.flatpak` bundle file for distribution:

```bash
# Build and export to a repository
flatpak-builder --repo=repo --force-clean build-dir com.freewili.updater.yml

# Create a single-file bundle
flatpak build-bundle repo freewili-updater.flatpak com.freewili.updater
```

Users can then install the bundle with:

```bash
flatpak install freewili-updater.flatpak
```

## Permissions

The Flatpak has the following permissions:

- **Display**: Wayland and X11 access for GUI
- **GPU**: Hardware acceleration for rendering
- **USB**: Full device access for firmware flashing
- **Network**: Internet access (for updates if needed)
- **File System**: Access to `/media`, `/run/media`, and `/mnt` for mounted drives (UF2 mode)
- **System Info**: Access to `/sys` and `/run/udev` for USB device enumeration
- **Theme**: Access to dconf for dark mode and system theme support

## Troubleshooting

### Icon is too large error

The icon must be 512x512 or smaller. Run this to resize:

```bash
magick icons/icon.png -resize 512x512 icons/icon-512.png
```

### Cargo rebuild on every build

Don't use `--force-clean` unless necessary. Only use it when:
- Making a first build
- Changing build commands in the manifest
- You need a completely fresh build

For permission changes or metadata updates, omit `--force-clean`.

### USB devices not detected

Make sure you have the required permissions. The app needs access to `/dev/ttyACM*` devices and mounted drives for UF2 flashing.

### Dark mode not working

Ensure you have dconf access enabled in the manifest and your system theme is properly configured.

## Notes

- The build downloads Rust dependencies during the build process (requires network access)
- First build will take several minutes; subsequent builds are much faster
- The `libxdo` library is built as a dependency for X11 automation features
