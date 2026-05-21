#!/usr/bin/env bash
set -euo pipefail

echo "[b450] WezTerm install — Ubuntu 24.04 x86_64"

# 1. GPG key
echo "[1/5] Import GPG key"
curl -fsSL https://apt.fury.io/wez/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/wezterm-fury.gpg

# 2. Repo
echo "[2/5] Add repo"
echo "deb [signed-by=/usr/share/keyrings/wezterm-fury.gpg] https://apt.fury.io/wez/ * *" \
  | sudo tee /etc/apt/sources.list.d/wezterm.list > /dev/null

# 3. Install
echo "[3/5] apt update + install"
sudo apt-get update -qq
sudo apt-get install -y wezterm

# 4. update-alternatives
echo "[4/5] Register x-terminal-emulator alternative"
sudo update-alternatives --install /usr/bin/x-terminal-emulator x-terminal-emulator "$(which wezterm)" 50
sudo update-alternatives --set x-terminal-emulator "$(which wezterm)"

# 5. GNOME / mimeapps
echo "[5/5] Set GNOME default terminal + mimeapps"
gsettings set org.gnome.desktop.default-applications.terminal exec 'wezterm' 2>/dev/null || true
gsettings set org.gnome.desktop.default-applications.terminal exec-arg '' 2>/dev/null || true

MIMEAPPS="$HOME/.config/mimeapps.list"
touch "$MIMEAPPS"
if ! grep -q 'x-terminal-emulator' "$MIMEAPPS" 2>/dev/null; then
  if grep -q '\[Default Applications\]' "$MIMEAPPS"; then
    sed -i '/\[Default Applications\]/a x-scheme-handler\/terminal=wezterm.desktop' "$MIMEAPPS"
  else
    printf '[Default Applications]\nx-scheme-handler/terminal=wezterm.desktop\n' >> "$MIMEAPPS"
  fi
fi

echo ""
echo "=== DONE ==="
echo "Binary : $(which wezterm)"
echo "Version: $(wezterm --version)"
echo "Config : $HOME/.config/wezterm/wezterm.lua"
echo "Alt    : $(update-alternatives --display x-terminal-emulator 2>/dev/null | grep 'link currently' || echo 'check manually')"
