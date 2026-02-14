#!/usr/bin/env python3
import sys
import evdev
from evdev import InputDevice, categorize, ecodes
import subprocess
import os
import re
import glob
import pwd
import yaml


CONFIG_PATH = '/etc/copilot-key-handler/config.yaml'
DEFAULT_CONFIG = {
    'device': 'auto',
    'terminal': 'gnome-terminal',
    'claude_path': 'auto',
    'user': 'auto',
    'display': ':0',
}


def load_config():
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            user_config = yaml.safe_load(f)
            if user_config:
                config.update(user_config)
    return config


def get_home_dir(user):
    """Get the home directory for a user from the passwd database."""
    try:
        return pwd.getpwnam(user).pw_dir
    except KeyError:
        return f'/home/{user}'


def detect_user():
    """Detect the logged-in desktop user."""
    user = os.environ.get('SUDO_USER')
    if user:
        return user
    try:
        output = subprocess.check_output(
            ['loginctl', 'list-users', '--no-legend'],
        ).decode().strip()
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                uid = int(parts[0])
                if uid >= 1000:
                    return parts[1]
    except Exception:
        pass
    return 'root'


def detect_claude_path(user):
    """Find the claude binary in common locations."""
    home = get_home_dir(user)
    candidates = [
        os.path.join(home, '.local', 'bin', 'claude'),
        os.path.join(home, '.claude', 'local', 'claude'),
        '/usr/local/bin/claude',
        '/usr/bin/claude',
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    # Try which as a last resort
    try:
        return subprocess.check_output(
            ['sudo', '-u', user, 'which', 'claude'],
        ).decode().strip()
    except Exception:
        return os.path.join(home, '.local', 'bin', 'claude')


def detect_device():
    """Find the keyboard input device that generates KEY_F23.
    Prefers vendor-specific keyboards over the generic AT keyboard."""
    candidates = []
    for path in sorted(glob.glob('/dev/input/event*')):
        try:
            dev = InputDevice(path)
            name = dev.name.lower()
            caps = dev.capabilities(verbose=True)
            has_f23 = False
            for (etype, _), keys in caps.items():
                if etype == 'EV_KEY':
                    key_names = []
                    for k in keys:
                        if isinstance(k, tuple):
                            key_names.extend(k)
                        else:
                            key_names.append(k)
                    if 'KEY_F23' in key_names:
                        has_f23 = True
                        break
            dev.close()
            if has_f23:
                candidates.append((path, name))
        except (PermissionError, OSError):
            continue
    # Prefer vendor-specific keyboards (USB/HID) over generic AT keyboard
    for path, name in candidates:
        if 'keyboard' in name and 'at translated' not in name:
            return path
    # Fall back to any keyboard
    for path, name in candidates:
        if 'keyboard' in name:
            return path
    if candidates:
        return candidates[0][0]
    return None


def get_active_terminal_cwd(user, display):
    """Get the CWD of the focused terminal tab from the window title."""
    try:
        win_id = subprocess.check_output(
            ['sudo', '-u', user, 'env', f'DISPLAY={display}',
             'xdotool', 'getactivewindow'],
        ).decode().strip()

        wm_class = subprocess.check_output(
            ['sudo', '-u', user, 'env', f'DISPLAY={display}',
             'xprop', '-id', win_id, 'WM_CLASS'],
        ).decode().strip().lower()

        if 'terminal' not in wm_class and 'kitty' not in wm_class and 'alacritty' not in wm_class:
            return None

        title = subprocess.check_output(
            ['sudo', '-u', user, 'env', f'DISPLAY={display}',
             'xdotool', 'getactivewindow', 'getwindowname'],
        ).decode().strip()

        home = get_home_dir(user)
        match = re.search(r':\s+(~?/.*)$', title)
        if match:
            path = match.group(1)
            if path.startswith('~'):
                path = home + path[1:]
            if os.path.isdir(path):
                return path

        return None
    except Exception:
        return None


def launch_terminal(user, display, terminal, cwd, claude_path):
    """Launch a terminal running Claude Code as the given user."""
    uid = pwd.getpwnam(user).pw_uid
    env_vars = {
        'DISPLAY': display,
        'DBUS_SESSION_BUS_ADDRESS': f'unix:path=/run/user/{uid}/bus',
    }

    if terminal == 'kitty':
        cmd = ['kitty', '--directory', cwd, claude_path]
    elif terminal == 'alacritty':
        cmd = ['alacritty', '--working-directory', cwd, '-e', claude_path]
    else:
        cmd = ['gnome-terminal', f'--working-directory={cwd}', '--', claude_path]

    env_args = []
    for k, v in env_vars.items():
        env_args.append(f'{k}={v}')

    subprocess.Popen(['sudo', '-u', user, 'env'] + env_args + cmd)


def main():
    config = load_config()

    user = config['user']
    if user == 'auto':
        user = detect_user()

    claude_path = config['claude_path']
    if claude_path == 'auto':
        claude_path = detect_claude_path(user)

    display = config['display']

    device_path = config['device']
    if device_path == 'auto':
        device_path = detect_device()

    if not device_path:
        print('copilot-key-handler: no device with KEY_F23 found. '
              'Set device path in /etc/copilot-key-handler/config.yaml',
              file=sys.stderr, flush=True)
        sys.exit(1)

    terminal = config['terminal']
    home = get_home_dir(user)

    print(f'copilot-key-handler: user={user} device={device_path} '
          f'terminal={terminal} claude={claude_path} display={display}',
          flush=True)

    device = InputDevice(device_path)
    for event in device.read_loop():
        if event.type == ecodes.EV_KEY:
            key = categorize(event)
            keycode = key.keycode if isinstance(key.keycode, list) else [key.keycode]
            if 'KEY_F23' in keycode and key.keystate == key.key_down:
                cwd = get_active_terminal_cwd(user, display)
                if not cwd:
                    cwd = home

                launch_terminal(user, display, terminal, cwd, claude_path)


if __name__ == '__main__':
    main()
