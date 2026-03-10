#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/snapkey"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="snapkey.service"
SERVICE_SRC="${SCRIPT_DIR}/${SERVICE_NAME}"
SERVICE_DEST="${SYSTEMD_USER_DIR}/${SERVICE_NAME}"

REQUIRED_BINS=(
  grim
  slurp
  maim
  scrot
  ffmpeg
  wf-recorder
  wl-copy
  xclip
  notify-send
)

log() {
  printf '[snapkey] %s\n' "$*"
}

err() {
  printf '[snapkey] ERROR: %s\n' "$*" >&2
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

detect_pkg_manager() {
  for pm in apt-get dnf pacman zypper apk xbps-install; do
    if command_exists "$pm"; then
      printf '%s' "$pm"
      return 0
    fi
  done
  return 1
}

pkg_name() {
  local pm="$1"
  local bin="$2"

  case "$pm:$bin" in
    *:wl-copy) printf 'wl-clipboard' ;;
    apt-get:notify-send) printf 'libnotify-bin' ;;
    dnf:notify-send|zypper:notify-send|apk:notify-send|xbps-install:notify-send) printf 'libnotify' ;;
    *) printf '%s' "$bin" ;;
  esac
}

run_with_privilege() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command_exists sudo; then
    sudo "$@"
  else
    err "Need root privileges for package install, but sudo is unavailable."
    return 1
  fi
}

install_packages() {
  local pm="$1"
  shift
  local pkgs=("$@")

  if [ "${#pkgs[@]}" -eq 0 ]; then
    return 0
  fi

  log "Installing missing dependencies via ${pm}: ${pkgs[*]}"

  case "$pm" in
    apt-get)
      run_with_privilege "$pm" update
      run_with_privilege "$pm" install -y "${pkgs[@]}"
      ;;
    dnf)
      run_with_privilege "$pm" install -y "${pkgs[@]}"
      ;;
    pacman)
      run_with_privilege "$pm" -Sy --noconfirm "${pkgs[@]}"
      ;;
    zypper)
      run_with_privilege "$pm" --non-interactive install "${pkgs[@]}"
      ;;
    apk)
      run_with_privilege "$pm" add "${pkgs[@]}"
      ;;
    xbps-install)
      run_with_privilege "$pm" -Sy "${pkgs[@]}"
      ;;
    *)
      err "Unsupported package manager: ${pm}"
      return 1
      ;;
  esac
}

validate_dependencies() {
  local missing_bins=()
  local pkg_mgr

  for bin in "${REQUIRED_BINS[@]}"; do
    if ! command_exists "$bin"; then
      missing_bins+=("$bin")
    fi
  done

  if [ "${#missing_bins[@]}" -eq 0 ]; then
    log "All required binaries are already installed."
    return 0
  fi

  log "Missing binaries: ${missing_bins[*]}"

  if ! pkg_mgr="$(detect_pkg_manager)"; then
    err "No supported package manager detected. Install dependencies manually: ${missing_bins[*]}"
    return 1
  fi

  local pkg_list=()
  local bin
  for bin in "${missing_bins[@]}"; do
    pkg_list+=("$(pkg_name "$pkg_mgr" "$bin")")
  done

  install_packages "$pkg_mgr" "${pkg_list[@]}"

  local still_missing=()
  for bin in "${missing_bins[@]}"; do
    if ! command_exists "$bin"; then
      still_missing+=("$bin")
    fi
  done

  if [ "${#still_missing[@]}" -ne 0 ]; then
    err "Dependency installation incomplete. Still missing: ${still_missing[*]}"
    return 1
  fi

  log "Dependency validation complete."
}

install_snapkey_files() {
  mkdir -p "$INSTALL_DIR"

  mkdir -p "$INSTALL_DIR/src"
  cp -a "$SCRIPT_DIR/src/." "$INSTALL_DIR/src/"

  while IFS= read -r file; do
    cp -f "$file" "$INSTALL_DIR/"
  done < <(find "$SCRIPT_DIR" -maxdepth 1 -type f ! -name "install.sh" ! -name "$SERVICE_NAME" ! -name "README.md")

  chmod -R u+rwX "$INSTALL_DIR"
  chmod u+rx "$INSTALL_DIR/src/daemon.py"
  log "Installed SnapKey files to $INSTALL_DIR"
}

install_service_file() {
  mkdir -p "$SYSTEMD_USER_DIR"

  if [ ! -f "$SERVICE_SRC" ]; then
    err "Service source file not found: $SERVICE_SRC"
    return 1
  fi

  cp -f "$SERVICE_SRC" "$SERVICE_DEST"
  log "Installed user systemd unit to $SERVICE_DEST"
}

enable_and_start_service() {
  systemctl --user daemon-reload
  systemctl --user enable --now "$SERVICE_NAME"
  log "Service enabled and started: $SERVICE_NAME"
}

print_help() {
  cat <<EOT

SnapKey installation complete.

Installed paths:
  - SnapKey files: $INSTALL_DIR
  - User service:  $SERVICE_DEST

Useful commands:
  systemctl --user status $SERVICE_NAME
  systemctl --user restart $SERVICE_NAME
  journalctl --user -u $SERVICE_NAME -f

If the service does not start at login, enable lingering once:
  loginctl enable-linger "$USER"

EOT
}

main() {
  validate_dependencies
  install_snapkey_files
  install_service_file
  enable_and_start_service
  print_help
}

main "$@"
