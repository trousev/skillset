---
name: browser-debug
description: "Looks at real web pages through the Chrome DevTools MCP server running against a local browser — navigate, click, fill forms, take screenshots, run JavaScript, and read console errors, network requests, DOM snapshots and performance traces. Use whenever something must be checked, tested or debugged in a browser instead of guessed from source: open it in the browser, check the console, why is the page blank, the layout is broken, inspect the DOM, take a screenshot of the page, click through the flow — and in Russian: открой в браузере, посмотри в браузере, проверь в хроме, что в консоли, сделай скриншот страницы, почему не работает на странице, отладка фронтенда. Never claim you cannot see the browser."
---

# /browser-debug — Look at the page, don't guess

You have a real browser. When a question is about what a page actually does — its DOM,
its console, its network, how it looks — open it and look. Reading source and inferring
is a fallback, not a first move.

**Never answer that you cannot see the browser.** If the tools below are missing from
your tool list, say exactly that, and ask the user to check `/mcp` for the
`chrome-devtools` server.

## The tools

The server exposes ~29 tools under the prefix `mcp__plugin_chrome-devtools_chrome-devtools__`.
Core ones:

| Tool | Use it for |
|------|------------|
| `list_pages` | Enumerate open pages — **always the first call** |
| `new_page` / `close_page` / `select_page` | Manage tabs |
| `navigate_page` | Go to a URL, back, forward, reload |
| `take_snapshot` | Text snapshot of the a11y tree — cheap, precise, gives element `uid`s |
| `take_screenshot` | Image of the page or an element — for the human, or for visual bugs |
| `evaluate_script` | Run a JS function in the page, get JSON back |
| `click` / `fill` / `fill_form` / `hover` / `type_text` / `press_key` / `drag` | Interact |
| `wait_for` | Wait for text to appear |
| `list_console_messages` / `get_console_message` | Console output, including errors |
| `list_network_requests` / `get_network_request` | Network activity and response bodies |
| `resize_page` / `emulate` | Viewport and device emulation |
| `performance_start_trace` / `performance_stop_trace` / `performance_analyze_insight` | Performance work |
| `lighthouse_audit` | Accessibility, SEO, best practices |
| `take_heapsnapshot` | Memory leaks |

## The pageId rule

**`pageId` is a number — the index shown by `list_pages`.** For a listing like
`1: about:blank [selected]`, the `pageId` is `1`.

This is the single most common hard failure. Passing a string, a URL, or a target id
gives `MCP error -32602: Input validation error ... Required at pageId` on
`navigate_page`, `evaluate_script`, `take_screenshot` and every other page-scoped tool.

So: **call `list_pages` first, every time**, and re-list after `new_page` or `close_page`
— indices shift.

## The local browser contract

The plugin starts its **own** browser instance with a **persistent profile**. Logins and
cookies made in it survive a restart, so if a page needs authentication, have the user log
in once and it stays logged in.

Window mode is fixed when the MCP server starts, so it cannot be flipped per call:

- **Default: headless.** No window, nothing to see on screen.
- **On request: a visible window.** Reach for it when the user asks to watch a flow, or asks
  for something inherently visual. You cannot switch it unilaterally — the reconnect below is
  the user's action — so offer it and let them decide.

To switch to a visible window, run this, then **ask the user to reconnect the server**
(they open `/mcp`, pick `chrome-devtools`, and choose Reconnect) — the mode is read when
the server restarts:

```bash
mkdir -p "${XDG_STATE_HOME:-$HOME/.local/state}/chrome-devtools-mcp"
printf headed  > "${XDG_STATE_HOME:-$HOME/.local/state}/chrome-devtools-mcp/display"
```

Back to headless: write `headless` instead. Check the current setting by reading that file;
**if it does not exist, the mode is headless.**

To find out which mode you actually got, without asking anyone:

```
evaluate_script → () => navigator.userAgent
```

`HeadlessChrome` in the string means headless. Say which mode is active before reporting a
visual problem that "looks wrong".

Environment overrides, if the user wants them (they take effect on the next session):
`CHROME_DEVTOOLS_BROWSER`, `CHROME_DEVTOOLS_USER_DATA_DIR`, `CHROME_DEVTOOLS_HEADLESS=1|0`,
`CHROME_DEVTOOLS_MCP_VERSION`. Diagnostics from the launcher go to stderr — they appear in
`/mcp` server details, not in your context.

## Core loop

1. `list_pages` → note the numeric `pageId`. If nothing is open, `new_page`.
2. `navigate_page` → wait for the page to settle.
3. Prefer `take_snapshot` for understanding structure and getting `uid`s to click. It is
   cheaper and more precise than an image.
4. `evaluate_script` for facts: element counts, computed styles, `window.__STATE__`,
   `localStorage`, response objects.
5. `list_console_messages` and `list_network_requests` — most "it's broken" reports are
   answered here.
6. Report **what you observed**, quoting the actual console line, status code or value.
   "The console shows `TypeError: x is undefined` at `app.js:42`" beats "there seems to be
   an error".

Screenshots: write large ones to a file with `filePath` rather than pulling a huge base64
blob into context, and keep the path under the project directory or `/tmp`.

## Debug playbooks

**Blank page or nothing renders** — `list_console_messages` first, then
`list_network_requests` for a failed bundle (404, or a CORS/blocked entry). Check
`evaluate_script → () => document.body.innerHTML.length`.

**Element not found or click does nothing** — `take_snapshot`, confirm the element exists
and read its `uid`. Check whether it's covered by an overlay, or inside an iframe the
snapshot doesn't reach.

**Layout or styling wrong** — `take_screenshot` for the visual, then `evaluate_script` for
the computed style and box of the specific element. Compare against what the CSS says
should happen.

**Form flow** — `fill_form` for several fields at once, then `click`, then `wait_for` the
expected text. Read the resulting network request to confirm the payload.

**Slow page** — `performance_start_trace`, interact, `performance_stop_trace`, then
`performance_analyze_insight`.

## Troubleshooting

| Error you see | Cause | Fix |
|---|---|---|
| Server missing from `/mcp`, or `Connection closed` | First run downloads the package; the cold start can outlive the connect timeout | Warm it once: `npx -y chrome-devtools-mcp@1.9.0 --help`, then Reconnect in `/mcp` |
| `MCP error -32602 ... Required at pageId` | `pageId` sent as a string, or omitted | It is a **number** from `list_pages` |
| `Failed to create ProcessSingleton ... File exists` | The profile directory collides with an already-running browser using it | The default profile is dedicated, so this means `CHROME_DEVTOOLS_USER_DATA_DIR` was pointed at a real browser profile — point it elsewhere |
| `SingletonLock: Permission denied` | Profile directory is a hidden (dot) path and the browser is confined (snap) | Move the profile out of any dot-directory |
| `Target closed` | The browser never started | Usually a visible window requested with no display; check `CHROME_DEVTOOLS_HEADLESS` |
| `Cannot find module` / `ERR_MODULE_NOT_FOUND` | Corrupt npm cache | `rm -rf ~/.npm/_npx` and reconnect (this also drops other npx tools) |
| Only ~9 read-only tools instead of ~29 | The client is gating tools in plan/read-only mode | Leave read-only mode; the server is fine |
| A tool call times out on a heavy page | Per-call timeout | Raise `MCP_TOOL_TIMEOUT` |

## Going deeper

Upstream ships maintained skills for specialised work. Read them rather than guessing — they
live next to the installed package:

```bash
find ~/.npm/_npx -maxdepth 5 -type d -name skills -path '*chrome-devtools-mcp*'
```

`troubleshooting`, `a11y-debugging`, `debug-optimize-lcp`, `cookie-debugging`,
`memory-leak-debugging`, `chrome-devtools-cli`. Also at
<https://github.com/ChromeDevTools/chrome-devtools-mcp>.

## Anti-Patterns

- ❌ **Answering "I can't see the browser"**: you can. Call `list_pages` and look.
- ❌ **Guessing at the DOM from source**: `take_snapshot` takes seconds and is authoritative.
- ❌ **`pageId` as a string, a URL, or a target id**: it is the numeric index from `list_pages`.
- ❌ **Calling a page-scoped tool without `list_pages` first**: especially after opening or closing a tab, when indices shift.
- ❌ **Screenshot as primary evidence**: a snapshot is cheaper, searchable and more precise. Use images for the human, or for genuinely visual bugs.
- ❌ **Reaching for a visible window by default**: it is headless for a reason, and the switch costs the user a reconnect. Offer it; do not make it your first move.
- ❌ **Pointing the profile at the user's real browser profile**: that collides with their running browser and risks their session.
- ❌ **Using this skill for static HTML on disk**: reading the file is faster.
- ❌ **Reporting "it works" from a screenshot alone**: read the console and the network too — silent errors do not show up in a picture.
