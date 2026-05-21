#!/usr/bin/env bash
# Run on IdeaPad via: ssh <user>@<host> 'bash -s' < install_wezterm_ideapad.sh
set -euo pipefail

echo "[IdeaPad] WezTerm install — detecting distro"
DISTRO=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
echo "Distro: $DISTRO"

if command -v apt-get &>/dev/null; then
  echo "[APT path]"
  curl -fsSL https://apt.fury.io/wez/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/wezterm-fury.gpg
  echo "deb [signed-by=/usr/share/keyrings/wezterm-fury.gpg] https://apt.fury.io/wez/ * *" \
    | sudo tee /etc/apt/sources.list.d/wezterm.list > /dev/null
  sudo apt-get update -qq && sudo apt-get install -y wezterm

elif command -v dnf &>/dev/null; then
  echo "[DNF path]"
  sudo dnf copr enable wezfurlong/wezterm-nightly -y
  sudo dnf install -y wezterm

elif command -v pacman &>/dev/null; then
  echo "[Pacman path]"
  sudo pacman -S --noconfirm wezterm

else
  echo "ERROR: No supported package manager found (apt/dnf/pacman)" >&2
  exit 1
fi

# Alternatives
sudo update-alternatives --install /usr/bin/x-terminal-emulator x-terminal-emulator "$(which wezterm)" 50 2>/dev/null || true
sudo update-alternatives --set x-terminal-emulator "$(which wezterm)" 2>/dev/null || true

# GNOME
gsettings set org.gnome.desktop.default-applications.terminal exec 'wezterm' 2>/dev/null || true

# mimeapps
MIMEAPPS="$HOME/.config/mimeapps.list"
mkdir -p "$HOME/.config"
touch "$MIMEAPPS"
if ! grep -q 'wezterm' "$MIMEAPPS" 2>/dev/null; then
  if grep -q '\[Default Applications\]' "$MIMEAPPS"; then
    sed -i '/\[Default Applications\]/a x-scheme-handler\/terminal=wezterm.desktop' "$MIMEAPPS"
  else
    printf '[Default Applications]\nx-scheme-handler/terminal=wezterm.desktop\n' >> "$MIMEAPPS"
  fi
fi

# Config
mkdir -p "$HOME/.config/wezterm"
if [ ! -f "$HOME/.config/wezterm/wezterm.lua" ]; then
  cat > "$HOME/.config/wezterm/wezterm.lua" << 'LUA'
local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.font = wezterm.font('JetBrains Mono', { weight = 'Regular' })
config.font_size = 12.0
config.color_scheme = 'nord'
config.window_padding = { left = 8, right = 8, top = 8, bottom = 8 }
config.window_close_confirmation = 'NeverPrompt'
config.enable_tab_bar = true
config.hide_tab_bar_if_only_one_tab = true
config.scrollback_lines = 10000
config.default_prog = { '/bin/bash', '-l' }
return config
LUA
  chmod 644 "$HOME/.config/wezterm/wezterm.lua"
fi

echo ""
echo "=== DONE ==="
echo "Binary : $(which wezterm)"
echo "Version: $(wezterm --version)"
