#!/usr/bin/env python3
"""SessionStart hook handler for deepseek-fix plugin.

Idempotent. Safe to run multiple times per session.

Responsibilities:
1. Bootstrap: ensure ANTHROPIC_BASE_URL is set in ~/.claude/settings.json
2. Lifecycle: ensure proxy daemon is running on localhost:18920

Always exits 0 — SessionStart hooks should not block session startup.
Warnings go to stderr (visible to Claude); config messages go to stdout.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

VERSION = "1.0.0"
PROXY_PORT = int(os.environ.get("DEEPSEEK_FIX_PORT", "18920"))
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}"
PROXY_HEALTH = f"{PROXY_URL}/health"

CLAUDE_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
CLAUDE_PLUGIN_DATA = os.environ.get("CLAUDE_PLUGIN_DATA", "")
CLAUDE_CONFIG_DIR = os.path.expanduser(
    os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")
)

SETTINGS_PATH = os.path.join(CLAUDE_CONFIG_DIR, "settings.json")
BACKUP_PATH = SETTINGS_PATH + ".deepseek-fix.bak"
PROXY_BIN = os.path.join(CLAUDE_PLUGIN_ROOT, "bin", "proxy") if CLAUDE_PLUGIN_ROOT else None


# ── Settings file management ─────────────────────────────────────────────────

def read_settings():
    """Read settings.json, returning (dict, raw_text)."""
    if not os.path.exists(SETTINGS_PATH):
        return {}, ""
    with open(SETTINGS_PATH, "r") as f:
        raw = f.read()
    try:
        return json.loads(raw), raw
    except json.JSONDecodeError:
        # Back up corrupted file and start fresh
        ts = int(time.time())
        backup = f"{SETTINGS_PATH}.invalid-{ts}"
        os.rename(SETTINGS_PATH, backup)
        print(f"deepseek-fix: {SETTINGS_PATH} was invalid JSON — backed up to {backup}",
              file=sys.stderr)
        return {}, ""


def write_settings(settings):
    """Atomically write settings.json."""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    content = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    tmp = SETTINGS_PATH + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, SETTINGS_PATH)


def ensure_env_base_url():
    """Ensure ANTHROPIC_BASE_URL points to our proxy in settings.json.

    Returns True if settings were modified (user should restart).
    """
    settings, raw = read_settings()

    env = settings.get("env", {})
    current = env.get("ANTHROPIC_BASE_URL", "")

    if current == PROXY_URL:
        return False  # Already configured

    # Safety guard: refuse to override a non-DeepSeek base URL
    if current and "deepseek" not in current:
        print(
            f"deepseek-fix: ANTHROPIC_BASE_URL is '{current}' — "
            f"not a DeepSeek endpoint. Refusing to redirect. "
            f"Set DEEPSEEK_FIX_PORT if you still want to use the proxy.",
            file=sys.stderr,
        )
        return False

    # One-time backup of original settings
    if os.path.exists(SETTINGS_PATH) and not os.path.exists(BACKUP_PATH):
        with open(SETTINGS_PATH, "r") as src:
            with open(BACKUP_PATH, "w") as dst:
                dst.write(src.read())

    # Merge env key, preserving all other settings
    settings["env"] = {**env, "ANTHROPIC_BASE_URL": PROXY_URL}
    write_settings(settings)

    print(
        f"deepseek-fix: Set ANTHROPIC_BASE_URL={PROXY_URL} in {SETTINGS_PATH}.\n"
        f"  This overrides any shell export of ANTHROPIC_BASE_URL.\n"
        f"  Restart Claude Code to apply. Original settings backed up to {BACKUP_PATH}."
    )
    return True


# ── Proxy lifecycle ──────────────────────────────────────────────────────────

def health_check():
    """Check if proxy is healthy. Returns (healthy: bool, version: str|None)."""
    try:
        req = urllib.request.Request(PROXY_HEALTH)
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
            marker = data.get("marker", "")
            ver = data.get("version", "")
            if marker == "deepseek-fix":
                return True, ver
            else:
                # Something else on our port
                print(
                    f"deepseek-fix: Port {PROXY_PORT} is occupied by "
                    f"a non-deepseek-fix process (marker={marker!r}).",
                    file=sys.stderr,
                )
                return False, None
    except (urllib.error.URLError, OSError, json.JSONDecodeError,
            ConnectionRefusedError, socket.timeout):
        return False, None


def is_pid_alive(pid):
    """Check if a process with given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def read_pid():
    """Read proxy PID from pid file."""
    pid_file = os.path.join(CLAUDE_PLUGIN_DATA, "proxy.pid") if CLAUDE_PLUGIN_DATA else None
    if not pid_file or not os.path.exists(pid_file):
        return None
    try:
        with open(pid_file) as f:
            return int(f.read().strip())
    except (ValueError, OSError):
        return None


def start_proxy():
    """Start the proxy daemon. Returns True if successful."""
    if not PROXY_BIN or not os.path.exists(PROXY_BIN):
        print(
            f"deepseek-fix: Proxy binary not found at {PROXY_BIN}",
            file=sys.stderr,
        )
        return False

    log_file = os.path.join(CLAUDE_PLUGIN_DATA, "proxy.log") if CLAUDE_PLUGIN_DATA else None

    # Truncate log if >10MB
    if log_file and os.path.exists(log_file) and os.path.getsize(log_file) > 10_000_000:
        with open(log_file, "w") as f:
            f.write("")

    try:
        kwargs = {
            "start_new_session": True,
        }
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            kwargs["stdout"] = open(log_file, "a")
            kwargs["stderr"] = subprocess.STDOUT

        subprocess.Popen(
            [sys.executable, PROXY_BIN],
            **kwargs,
        )
    except Exception as e:
        print(f"deepseek-fix: Failed to start proxy: {e}", file=sys.stderr)
        return False

    # Wait for health check
    for _ in range(30):  # 3 seconds max
        time.sleep(0.1)
        healthy, _ = health_check()
        if healthy:
            return True

    print(
        f"deepseek-fix: Proxy started but health check failed after 3s. "
        f"Check {log_file or 'logs'} for details.",
        file=sys.stderr,
    )
    return False


def stop_proxy():
    """Stop a running proxy daemon."""
    pid = read_pid()
    if pid and is_pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if is_pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def ensure_proxy_running():
    """Ensure the proxy daemon is running. Restart if version mismatch."""
    healthy, proxy_version = health_check()

    if healthy:
        if proxy_version != VERSION:
            # Plugin updated — restart with new version
            print(
                f"deepseek-fix: Proxy version {proxy_version} is outdated "
                f"(plugin version {VERSION}). Restarting...",
                file=sys.stderr,
            )
            stop_proxy()
            time.sleep(0.5)
            return start_proxy()
        return True  # Already running, correct version

    # Not healthy — check for stale process
    pid = read_pid()
    if pid and is_pid_alive(pid):
        # Process exists but not responding — kill it
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        time.sleep(0.3)

    return start_proxy()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Step 1: Bootstrap ANTHROPIC_BASE_URL in settings
    modified = ensure_env_base_url()

    if modified:
        # Settings were just written — proxy isn't needed yet
        # (ANTHROPIC_BASE_URL won't take effect until restart).
        # Start proxy anyway so it's ready for the next session.
        ensure_proxy_running()
        return

    # Step 2: Ensure proxy is running
    ensure_proxy_running()


if __name__ == "__main__":
    main()
