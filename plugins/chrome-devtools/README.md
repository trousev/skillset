# chrome-devtools

Wires the [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) server
to a **local** browser, so the AI can actually look at a page instead of guessing from source.

It ships one skill, `/browser-debug`, that teaches the workflow — navigate, snapshot,
evaluate, screenshot, read console and network — and one launcher that finds your browser and
gives it a profile it can write to.

## Installation

```bash
claude marketplace add trousev/skillset
claude plugin install chrome-devtools@trousev-skillset
```

The MCP server starts automatically when the plugin is enabled.

## What it can do

Navigate and interact with pages, take accessibility-tree snapshots and screenshots, run
JavaScript, read console messages and network requests, emulate devices and viewports, run
Lighthouse audits, record performance traces, and capture heap snapshots — about 29 tools.

## Requirements

- **Node.js** `^20.19.0 || ^22.12.0 || >=23` (the server's own requirement — `npx` comes with it)
- **A browser**: chromium, or Google Chrome as a fallback
- Python 3.8+ (stdlib only — the launcher is plain Python)

## Which browser gets used

First match wins:

| Order | Candidate |
|-------|-----------|
| 1 | `$CHROME_DEVTOOLS_BROWSER` |
| 2 | `chromium`, `chromium-browser`, `/snap/bin/chromium` |
| 3 | `google-chrome`, `google-chrome-stable`, `chrome`, `/opt/google/chrome/chrome`, `/Applications/Google Chrome.app/...` |

Chromium is preferred deliberately; Chrome is the fallback. If `CHROME_DEVTOOLS_BROWSER` is set
but is not executable, the launcher **stops** rather than silently using a different browser —
a typo should be visible, not papered over.

## The profile directory

The plugin runs its **own** browser instance with a persistent profile so that logins and
cookies survive a restart. By default that profile lives at:

```
$HOME/chrome-devtools-mcp-profile
```

Yes, that is a visible directory in your home. It is not an accident.

Confined browsers — snap chromium in particular — are denied write access to **hidden**
paths under `$HOME`. Point a snap chromium at `~/.cache/...` and it fails with
`SingletonLock: Permission denied`, or quietly falls back to its own profile and collides
with your running browser. A non-hidden path works for every browser, so the launcher always
uses one and never has to guess whether your browser is confined.

Override it with `CHROME_DEVTOOLS_USER_DATA_DIR` if you want it elsewhere — but keep it out
of any dot-directory, or a confined browser will refuse to start.

> The profile is the browser's, not a cache. Deleting it logs you out of everything you
> signed into while debugging.

## Window mode

**Headless by default** — no window, nothing to watch, fastest.

To get a visible window, write the mode to the state file and reconnect the server:

```bash
mkdir -p "${XDG_STATE_HOME:-$HOME/.local/state}/chrome-devtools-mcp"
printf headed > "${XDG_STATE_HOME:-$HOME/.local/state}/chrome-devtools-mcp/display"
```

Then open `/mcp`, pick `chrome-devtools`, and choose **Reconnect**. The mode is read when the
server starts, so the change applies on reconnect — no need to restart Claude Code. Write
`headless` to go back.

The skill knows this procedure and will offer it when a bug is genuinely visual. It is
headless by default on purpose: a window that opens on its own and steals focus is unwelcome.

If a visible window is requested but `DISPLAY` and `WAYLAND_DISPLAY` are both unset, the
launcher falls back to headless with a warning to stderr rather than failing — the browser
tools stay usable either way.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHROME_DEVTOOLS_BROWSER` | auto-detected | Path to the browser to drive |
| `CHROME_DEVTOOLS_USER_DATA_DIR` | `$HOME/chrome-devtools-mcp-profile` | Profile directory (must not be a dot-path) |
| `CHROME_DEVTOOLS_HEADLESS` | `1` | `1` headless, `0` visible window |
| `CHROME_DEVTOOLS_MCP_VERSION` | `1.9.0` | Version of `chrome-devtools-mcp` to run |

These are read when the MCP server starts, i.e. when Claude Code launches. To change one, set
it in the environment Claude Code itself starts from, then restart Claude Code.

The MCP package version is **pinned on purpose**. `@latest` costs a registry request on every
server start, and an upstream release that renames a flag would leave the server dead with no
tool list and no explanation. Set `CHROME_DEVTOOLS_MCP_VERSION=latest` if you would rather
float, and treat bumping the pin as maintenance.

## First run

The first start downloads the package, which can take longer than the client's connect
timeout. If the server does not appear in `/mcp`, warm the cache once and reconnect:

```bash
npx -y chrome-devtools-mcp@1.9.0 --help
```

## Privacy

- **CrUX is disabled** (`--no-performance-crux`). Without it, URLs from performance traces are
  sent to Google's CrUX API — that is your data leaving your machine as a side effect of an
  ordinary debugging action, so it is off by default.
- **Usage statistics are left at the upstream default (on).** That is the tool's own
  aggregated telemetry, disclosed by its authors; silently opting users out of it is not this
  plugin's call. Opt out with `CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS=1` or `CI=1`.
- The browser is driven over the DevTools protocol on your machine. Nothing is sent anywhere
  except by the pages you navigate to.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Server absent from `/mcp`, or `Connection closed` | Cold npm cache on first run | Warm it (above), then Reconnect |
| `SingletonLock: Permission denied` | Profile is inside a dot-directory | Move it (see *The profile directory*) |
| `Failed to create ProcessSingleton ... File exists` | Profile points at a browser profile that is already open | Use a dedicated directory |
| `Target closed` | Browser did not start | Check the launcher's stderr in `/mcp` server details |
| `Cannot find module` | Corrupt npm cache | `rm -rf ~/.npm/_npx`, then reconnect |
| Only ~9 tools instead of ~29 | Client is in read-only/plan mode | Leave read-only mode |

Launcher diagnostics go to **stderr** by design: stdout is the MCP JSON-RPC channel, and
writing anything else there breaks the handshake. Look for `chrome-devtools:` lines in the
server's details in `/mcp`.

## Uninstall

```bash
claude plugin uninstall chrome-devtools@trousev-skillset
```

The browser profile is left in place — remove `$HOME/chrome-devtools-mcp-profile` yourself if
you want the disk space back. The npm cache under `~/.npm/_npx` is shared and safe to leave.

## License

MIT
