# Copilot Key Handler

Remaps the Windows Copilot key (found on ASUS ROG and other modern laptops) to launch [Claude Code](https://docs.anthropic.com/en/docs/claude-code) on Linux.

## How it works

The Copilot key generates a `Shift+Super+F23` keypress at the hardware level. This daemon listens for the `KEY_F23` event using Python's `evdev` library and opens a terminal running Claude Code.

If a terminal window is focused when the key is pressed, Claude Code opens in that terminal's working directory. Otherwise, it opens in the user's home directory.

## Installation

### From PPA (recommended)

```bash
sudo add-apt-repository ppa:jedijamez/copilot-key-handler
sudo apt update
sudo apt install copilot-key-handler
```

Then enable the service:

```bash
sudo systemctl enable --now copilot-key-handler
```

### Manual installation

```bash
# Install system dependencies
sudo apt install python3-evdev python3-yaml xdotool x11-utils

# Clone and install
git clone https://github.com/jedijamez/copilot-key-handler.git
cd copilot-key-handler
sudo install -D -m 0755 main.py /usr/lib/copilot-key-handler/main.py
sudo install -D -m 0644 config.yaml.default /etc/copilot-key-handler/config.yaml
sudo install -D -m 0644 copilot-key-handler.service /lib/systemd/system/copilot-key-handler.service
sudo systemctl daemon-reload
sudo systemctl enable --now copilot-key-handler
```

## Configuration

Edit `/etc/copilot-key-handler/config.yaml` to customize:

- **device** — Input device path (default: `auto` — scans for KEY_F23 support)
- **terminal** — Terminal emulator: `gnome-terminal`, `kitty`, or `alacritty` (default: `gnome-terminal`)
- **claude_path** — Path to the `claude` binary (default: `auto` — searches common locations)
- **user** — Linux username (default: `auto` — detected from system)
- **display** — X11 display (default: `:0`)

After editing, restart the service:

```bash
sudo systemctl restart copilot-key-handler
```

## Usage

Once installed and enabled, press the Copilot key to launch Claude Code.

To check the service status:

```bash
sudo systemctl status copilot-key-handler
```

To view logs:

```bash
journalctl -u copilot-key-handler -f
```

## Dependencies

- Python 3.10+
- python3-evdev
- python3-yaml
- xdotool
- x11-utils (xprop)
- A supported terminal emulator (GNOME Terminal, Kitty, or Alacritty)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed

## License

MIT
