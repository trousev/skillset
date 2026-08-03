# deepseek-fix

Fixes Claude Code security classifier hanging when using DeepSeek API as an Anthropic-compatible backend.

## Problem

When using `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`, any "risky" Bash command (`scp`, `ssh`, `docker compose`, `iptables`, etc.) triggers Claude Code's built-in security classifier. The classifier sends a **non-streaming** (`stream: false`) request to DeepSeek. Since `deepseek-v4-pro` is a reasoning model that defaults to `thinking=enabled`, the time-to-first-byte for non-streaming calls equals full reasoning time (~30 seconds at typical classifier payload sizes). Claude Code's ~30-second client-side timeout is exceeded → timeout → retry → infinite loop.

**Root cause**: [deepseek-ai/DeepSeek-V3#1464](https://github.com/deepseek-ai/DeepSeek-V3/issues/1464)

## Fix

This plugin installs a local HTTP proxy (Python, stdlib-only, zero dependencies) that:

1. Listens on `localhost:18920`
2. Forwards all requests to `https://api.deepseek.com/anthropic`
3. For **non-streaming** `POST /v1/messages` (the classifier path): injects `"thinking": {"type": "disabled"}`, dropping latency from ~32s to ~3s
4. For **streaming** requests (the main agent loop): passes through unchanged — full reasoning preserved
5. All other endpoints: pass through unchanged

## Install

```bash
# Add the marketplace (one-time)
claude marketplace add trousev/skillset

# Install the plugin
claude plugin install deepseek-fix@trousev-skillset
```

## What happens after install

1. **First restart** (prompted by plugin install): The SessionStart hook detects that `ANTHROPIC_BASE_URL` is not yet configured. It writes `env.ANTHROPIC_BASE_URL = "http://localhost:18920"` to `~/.claude/settings.json` and starts the proxy daemon. You'll see a message: "Restart Claude Code to apply."

2. **Second restart**: `ANTHROPIC_BASE_URL` takes effect. All API calls now go through the proxy. The SessionStart hook auto-starts the proxy. Security classifier works — no more hangs.

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
2. Restore original `ANTHROPIC_BASE_URL` in `~/.claude/settings.json` (or restore from `settings.json.deepseek-fix.bak`)
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
