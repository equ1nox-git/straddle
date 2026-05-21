#!/usr/bin/env bash
# Run on MacBook (macOS). Requires Homebrew.
set -euo pipefail

echo "[MacBook] WezTerm install — macOS"

# 1. Homebrew
if ! command -v brew &>/dev/null; then
  echo "[1/4] Installing Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "[1/4] Homebrew present: $(brew --version | head -1)"
fi

# 2. WezTerm cask
echo "[2/4] brew install --cask wezterm"
brew install --cask wezterm

# 3. Config
echo "[3/4] Provision ~/.config/wezterm/wezterm.lua"
mkdir -p "$HOME/.config/wezterm"
if [ ! -f "$HOME/.config/wezterm/wezterm.lua" ]; then
  cat > "$HOME/.config/wezterm/wezterm.lua" << 'LUA'
local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.font = wezterm.font('JetBrains Mono', { weight = 'Regular' })
config.font_size = 13.0
config.color_scheme = 'nord'
config.window_padding = { left = 8, right = 8, top = 8, bottom = 8 }
config.window_close_confirmation = 'NeverPrompt'
config.enable_tab_bar = true
config.hide_tab_bar_if_only_one_tab = true
config.scrollback_lines = 10000
config.native_macos_fullscreen_mode = true
return config
LUA
  chmod 644 "$HOME/.config/wezterm/wezterm.lua"
  echo "Config written"
else
  echo "Config already exists — skipped"
fi

# 4. Default terminal (macOS has no system-level default terminal API)
echo "[4/4] Default terminal binding"
echo ""
echo "  macOS does not expose a CLI API to set the default terminal."
echo "  To make WezTerm the default:"
echo "  System Settings → Desktop & Dock → Default web browser"
echo "  — No equivalent for terminals. Instead:"
echo "  1. Right-click any .sh / .command file → Get Info → Open With → WezTerm → Change All"
echo "  2. In Terminal.app: Preferences → Startup → uncheck 'Open at login'"
echo "  3. Add WezTerm to Login Items: System Settings → General → Login Items → +"
if command -v duti &>/dev/null; then
  echo "  duti present — setting shell handler:"
  duti -s com.github.wez.wezterm public.unix-executable all 2>/dev/null && echo "  duti: ok" || echo "  duti: partial (shell scripts only)"
fi

echo ""
echo "=== DONE ==="
echo "Binary : $(which wezterm 2>/dev/null || ls /Applications/WezTerm.app/Contents/MacOS/wezterm 2>/dev/null || echo 'check /Applications')"
echo "Config : $HOME/.config/wezterm/wezterm.lua"
wezterm --version 2>/dev/null || echo "Version: run wezterm --version after opening a new shell"
