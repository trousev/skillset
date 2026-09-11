#!/usr/bin/env python3
"""Launch chrome-devtools-mcp against a local browser.

Claude Code spawns this as the plugin's MCP stdio server. It resolves a local
browser binary and a confinement-safe profile directory, then execs the server
and hands over stdio.

IMPORTANT: stdout is the JSON-RPC channel. Every diagnostic goes to stderr. A
single stray print() to stdout corrupts the MCP handshake, and the resulting
error looks nothing like its cause.

Why a launcher instead of static args in .mcp.json:

1. The browser path has to be discovered. Puppeteer's `--channel` only knows
   Google Chrome channels (canary/dev/beta/stable); chromium and anything else
   must go through `--executablePath`, and that value is machine-dependent.
2. The profile path has to be computed. .mcp.json substitutes ${VAR} and
   ${VAR:-default}, but the default branch is a literal -- it does not expand
   $HOME, so `:-$HOME/x` would be passed through verbatim.
"""

import os
import shutil
import subprocess
import sys

# Pinned deliberately. `@latest` costs a registry round-trip on every single
# server start, and an upstream release that renames one of the flags below
# would surface as "server started, then died" with an empty tool list and no
# explanation. Bumping this is routine maintenance.
DEFAULT_MCP_VERSION = "1.9.0"

# chromium first, chrome as the fallback. Resolved via PATH first, then as an
# absolute path so a stripped PATH still finds the browser. Paths are used
# exactly as found -- never resolved with realpath, because the found path is
# what actually gets exec'd and normalizing it buys nothing.
BROWSER_CANDIDATES = [
    "chromium",
    "chromium-browser",
    "/snap/bin/chromium",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "/opt/google/chrome/chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

NODE_RANGE = "^20.19.0 || ^22.12.0 || >=23"

STATE_SUBDIR = "chrome-devtools-mcp"
STATE_FILENAME = "display"


def log(message):
    print(f"chrome-devtools: {message}", file=sys.stderr)


def warn(message):
    log(f"WARNING: {message}")


def die(message):
    log(f"ERROR: {message}")
    sys.exit(1)


def resolve_browser():
    """Return the path to the browser to drive."""
    override = os.environ.get("CHROME_DEVTOOLS_BROWSER")
    if override:
        if _is_executable(override):
            return override
        # Do not fall through to auto-detection: the user asked for this
        # browser specifically, and silently using another one hides the typo.
        die(
            f"CHROME_DEVTOOLS_BROWSER={override!r} is not an executable file. "
            "Fix the path or unset the variable to auto-detect."
        )

    for candidate in BROWSER_CANDIDATES:
        found = candidate if os.sep in candidate else shutil.which(candidate)
        if found and _is_executable(found):
            return found

    die(
        "no local browser found. Looked for: "
        + ", ".join(BROWSER_CANDIDATES)
        + ". Install chromium (e.g. `snap install chromium`) or point "
        "CHROME_DEVTOOLS_BROWSER at your browser."
    )


def _is_executable(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)


def profile_dir():
    """Return a persistent profile directory the browser can actually write to.

    Always a non-hidden path. Confined browsers (snap in particular) are denied
    dot-paths under $HOME, and chromium then fails with a bewildering
    "SingletonLock: Permission denied" or silently falls back to its own
    profile and collides with the user's running browser. A non-hidden path
    works for every browser, so there is no reason to detect confinement.

    The directory is stable across restarts, which is the point: cookies and
    logins made in the debugging browser survive.
    """
    raw = os.environ.get("CHROME_DEVTOOLS_USER_DATA_DIR") or os.path.join(
        "~", "chrome-devtools-mcp-profile"
    )
    path = os.path.abspath(os.path.expanduser(raw))

    if _has_hidden_component(path):
        warn(f"profile directory {path} is inside a hidden path.")
        warn(
            "confined browsers (snap chromium) cannot write there and will fail "
            "with 'SingletonLock: Permission denied'. If the browser fails to "
            "start, move the profile out of any dot-directory."
        )

    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        die(f"cannot create profile directory {path}: {exc}")

    return path


def _has_hidden_component(path):
    return any(
        part.startswith(".") and part not in (".", "..") for part in path.split(os.sep)
    )


def state_file():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join("~", ".local", "state")
    return os.path.join(os.path.expanduser(base), STATE_SUBDIR, STATE_FILENAME)


def want_headless():
    """Decide between a headless and a visible browser.

    Precedence: CHROME_DEVTOOLS_HEADLESS, then the state file, then headless.

    The state file exists because the MCP subprocess inherits Claude Code's
    environment -- there is no way to hand it a new variable mid-session, but
    a file is re-read whenever the server restarts. That is what lets the skill
    switch to a visible window on request. Default is headless.
    """
    raw = os.environ.get("CHROME_DEVTOOLS_HEADLESS")
    if raw is not None:
        parsed = _parse_bool(raw)
        if parsed is None:
            warn(f"unrecognized CHROME_DEVTOOLS_HEADLESS={raw!r}; ignoring it.")
        else:
            return parsed, "CHROME_DEVTOOLS_HEADLESS"

    path = state_file()
    try:
        with open(path) as handle:
            mode = handle.read().strip().lower()
    except OSError:
        return True, "default"

    if mode == "headed":
        return False, path
    if mode == "headless":
        return True, path
    if mode:
        warn(f"unrecognized mode {mode!r} in {path}; using the default.")
    return True, "default"


def _parse_bool(value):
    normalized = value.strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return None


def display_available():
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def check_node():
    if not shutil.which("npx"):
        die("npx not found. It ships with npm -- install Node.js to get both.")

    node = shutil.which("node")
    if not node:
        die(f"node not found. chrome-devtools-mcp requires Node {NODE_RANGE}.")

    try:
        result = subprocess.run(
            [node, "-p", "process.versions.node"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        version = result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return

    if version and not _node_supported(version):
        # A warning rather than a hard stop: the check could be wrong, and
        # refusing to start on a setup that actually works is worse.
        warn(f"Node {version} is outside the supported range ({NODE_RANGE}).")


def _node_supported(version):
    try:
        major, minor = (int(part) for part in version.split(".")[:2])
    except ValueError:
        return True
    if major >= 23:
        return True
    if major == 22:
        return minor >= 12
    if major == 20:
        return minor >= 19
    return False


def main():
    check_node()

    browser = resolve_browser()
    profile = profile_dir()
    headless, source = want_headless()

    if not headless and not display_available():
        warn(
            "a visible window was requested "
            f"(via {source}) but neither DISPLAY nor WAYLAND_DISPLAY is set."
        )
        warn("falling back to headless so the browser tools still work.")
        headless = True

    version = os.environ.get("CHROME_DEVTOOLS_MCP_VERSION", DEFAULT_MCP_VERSION)
    spec = f"chrome-devtools-mcp@{version}"

    extra = sys.argv[1:]
    if "--isolated" in extra:
        warn(
            "--isolated was passed: it uses a throwaway profile, so logins and "
            "cookies will not survive a restart."
        )

    args = [
        "-y",
        spec,
        "--no-performance-crux",
        "--executablePath",
        browser,
        "--userDataDir",
        profile,
    ]
    if headless:
        args.append("--headless")
    args.extend(extra)

    log(
        f"starting {spec} "
        f"[browser={browser}, profile={profile}, "
        f"mode={'headless' if headless else 'headed'}]"
    )

    # exec, so the server owns the inherited stdio directly: no wrapper process
    # lingers and SIGTERM from the client reaches the server.
    try:
        os.execvp("npx", ["npx", *args])
    except OSError as exc:
        die(f"could not exec npx: {exc}")


if __name__ == "__main__":
    main()
