# SnapKey

**SnapKey — Lightning fast screenshots for Linux with Windows-like shortcuts.**

## Project overview

SnapKey is a lightweight Linux capture utility focused on speed and keyboard-first workflows. It provides a unified launcher and hotkey experience for screenshots, recordings, and optional GIF capture across common desktop environments.

The project targets users who want a consistent “press shortcut, capture now” flow regardless of whether they run Wayland or X11.

## Architecture summary

At a high level, SnapKey is organized into a few cooperating pieces:

- **Hotkey layer**: Binds global key combinations (for example via desktop keybindings or compositor/window-manager bindings).
- **Capture engine adapter**: Dispatches screenshot/recording commands to the appropriate backend based on session type (`WAYLAND_DISPLAY` vs `DISPLAY`) and installed tools.
- **Overlay/UI controls**: Presents region-selection overlay and recording control panel where supported.
- **Output manager**: Normalizes filenames, timestamps, and save locations.
- **Installer/bootstrap scripts**: Installs dependencies, registers shortcuts, and sets up optional user services.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `SUPER+SHIFT+S` | Screenshot region |
| `SUPER+SHIFT+R` | Open/start recording controls |
| `SUPER+SHIFT+Q` | Stop recording |
| `SUPER+SHIFT+G` | GIF capture (optional) |

## Dependency matrix (Wayland vs X11)

| Capability | Wayland (examples) | X11 (examples) | Notes |
| --- | --- | --- | --- |
| Region screenshot | `grim` + `slurp` | `maim` / `import` | Pick one backend per session type. |
| Screen recording | `wf-recorder` | `ffmpeg` + `x11grab` | Hardware acceleration optional. |
| Clipboard copy | `wl-copy` | `xclip` / `xsel` | Optional but recommended. |
| Notifications | `notify-send` | `notify-send` | Provided by `libnotify` on most distros. |
| Global hotkeys | DE/compositor bindings | DE/WM bindings | Config path differs by environment. |

> Tip: if you run XWayland-only apps on Wayland, keep native Wayland capture tools installed for best compatibility.

## Installation

From the project root:

```bash
cd snapkey
chmod +x install.sh
./install.sh
```

Typical `install.sh` responsibilities:

1. Detect Wayland vs X11 session.
2. Install/verify required capture dependencies.
3. Register SnapKey hotkeys.
4. Create output directories.
5. Optionally enable user-level service/timer units.

## Autostart and service management

Use `systemctl --user` for SnapKey background helpers:

```bash
systemctl --user status snapkey.service
systemctl --user restart snapkey.service
systemctl --user disable snapkey.service
```

If your setup uses a timer or alternative unit name, replace `snapkey.service` accordingly.

## Output directory behavior

SnapKey stores generated media in user-friendly defaults:

- Screenshots: `~/Pictures/SnapKey`
- Recordings/GIFs: `~/Videos/SnapKey`

Directories are created automatically when first needed.

## Screenshots

Current implementation is terminal/background-first and relies on your desktop
notifications (`notify-send`) for status feedback. There is no dedicated GUI
panel yet.

- Region capture: uses native capture backend (`grim`/`maim`/`scrot`).
- Recording toggle: start/stop status is reported via desktop notifications.

## Current limitations

- GIF capture shortcut is wired, but GIF generation is not yet implemented.
- GNOME/KDE manual keybinding setup is still required when compositor-level
  CLI binding APIs are unavailable.

## Troubleshooting by desktop environment / WM

### GNOME

- Prefer GNOME Settings → Keyboard for binding custom shortcuts.
- Disable conflicting built-in screenshot shortcuts if SnapKey bindings do not trigger.

### KDE Plasma

- Configure shortcuts in System Settings → Shortcuts.
- If conflicts occur, remove Spectacle default bindings or remap SnapKey combos.

### XFCE

- Use Settings → Keyboard → Application Shortcuts.
- Ensure command paths are absolute if shortcuts fail silently.

### Openbox

- Add keybindings in `~/.config/openbox/rc.xml` and reload Openbox.
- Verify no overlapping bindings in external hotkey daemons.

### i3

- Add bindings to `~/.config/i3/config` with `bindsym`.
- Use `--release` for certain combos if press/repeat behavior is problematic.

### Hyprland

- Add `bind`/`bindr` entries in `~/.config/hypr/hyprland.conf`.
- Verify compositor-specific permission and portal configuration for screen capture.

If hotkeys still do not work, test capture commands directly in a terminal first, then wire them back into your environment’s keybinding system.
