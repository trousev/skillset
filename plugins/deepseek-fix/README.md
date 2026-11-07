# deepseek-fix

Fixes Claude Code security classifier problems when using DeepSeek API as an Anthropic-compatible backend.

## Problem

**1. Classifier hangs.** When using `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`, any "risky" Bash command (`scp`, `ssh`, `docker compose`, `iptables`, etc.) triggers Claude Code's built-in security classifier. The classifier sends a **non-streaming** (`stream: false`) request to DeepSeek. Since `deepseek-v4-pro` is a reasoning model that defaults to `thinking=enabled`, the time-to-first-byte for non-streaming calls equals full reasoning time (~30 seconds at typical classifier payload sizes). Claude Code's ~30-second client-side timeout is exceeded → timeout → retry → infinite loop.

**Root cause**: [deepseek-ai/DeepSeek-V3#1464](https://github.com/deepseek-ai/DeepSeek-V3/issues/1464)

**2. Recurring classifier billing notice.** Claude Code v2.1.278+ asks the API to run auto mode's classifier checks server-side. DeepSeek can't provide those checks, so auto mode falls back to Claude Code's own classifier requests and shows a notice once a day: *"We're changing auto mode to no longer charge for classifier requests… this session isn't eligible because your requests go through 127.0.0.1:18920."* Setting `CLAUDE_CODE_AUTO_MODE_SERVER=0` selects the same fallback up front and suppresses the notice ([docs](https://code.claude.com/docs/en/auto-mode-classifier-billing)).

## Fix

This plugin installs a local HTTP proxy (Python, stdlib-only, zero dependencies) that:

1. Listens on `localhost:18920`
2. Forwards all requests to `https://api.deepseek.com/anthropic`
3. For **non-streaming** `POST /v1/messages` (the classifier path): injects `"thinking": {"type": "disabled"}`, dropping latency from ~32s to ~3s
4. For **streaming** requests (the main agent loop): passes through unchanged — full reasoning preserved
5. All other endpoints: pass through unchanged

It also sets `CLAUDE_CODE_AUTO_MODE_SERVER=0` in `~/.claude/settings.json`, so auto mode uses Claude Code's own classifier requests (which the proxy serves) instead of showing the gateway billing notice every 24 hours.

## Install

```bash
# Add the marketplace (one-time)
claude marketplace add trousev/skillset

# Install the plugin
claude plugin install deepseek-fix@trousev-skillset
```

## What happens after install

1. **First restart** (prompted by plugin install): The SessionStart hook detects that `ANTHROPIC_BASE_URL` is not yet configured. It writes `env.ANTHROPIC_BASE_URL = "http://localhost:18920"` and `env.CLAUDE_CODE_AUTO_MODE_SERVER = "0"` to `~/.claude/settings.json` and starts the proxy daemon. You'll see a message: "Restart Claude Code to apply."

2. **Second restart**: `ANTHROPIC_BASE_URL` takes effect. All API calls now go through the proxy. The SessionStart hook auto-starts the proxy. Security classifier works — no more hangs, and no auto mode classifier billing notice.

3. **All subsequent sessions**: The proxy auto-starts. Everything works.

Your shell `export ANTHROPIC_BASE_URL` in `.zshrc` is automatically overridden by the settings-file value — no manual edits needed.

## Verify

```bash
# Check proxy health
curl -s http://localhost:18920/health | python3 -m json.tool

# Test a risky command in Claude Code
# scp, ssh, docker compose — should resolve in seconds, not hang
```

## Manual control

```bash
# Start proxy (installed to Bash PATH while plugin enabled)
python3 ~/.claude/plugins/cache/deepseek-fix-*/bin/proxy &

# Check status
curl -s http://localhost:18920/health

# Stop proxy
pkill -f "bin/proxy"

# Check logs
tail -50 ~/.claude/plugins/data/deepseek-fix-*/proxy.log
```

## Uninstall

1. Stop proxy: `pkill -f "bin/proxy"`
2. Restore original settings in `~/.claude/settings.json` (or restore from `settings.json.deepseek-fix.bak`): remove `ANTHROPIC_BASE_URL` and `CLAUDE_CODE_AUTO_MODE_SERVER` from the `env` key.
3. Disable/uninstall plugin: `claude plugin disable deepseek-fix`
4. Restart Claude Code

## Requirements

- Python 3.7+
- DeepSeek API access (any model)
- Linux or macOS

## How it works

```
Claude Code → localhost:18920 (proxy) → api.deepseek.com/anthropic
                                │
                  stream:false → inject thinking:disabled
                  stream:true  → passthrough (SSE streaming)
```

## License

MIT
