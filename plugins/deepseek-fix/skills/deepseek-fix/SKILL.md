---
name: deepseek-fix
description: "Diagnose and fix the DeepSeek + Claude Code security classifier hang. Use when risky Bash commands (scp, ssh, docker compose) hang in a 'security classifier temporarily unavailable' retry loop, or to verify, restart, or uninstall the deepseek-fix proxy."
---

# deepseek-fix: Diagnostic & Recovery

This skill helps you verify, troubleshoot, and manage the deepseek-fix proxy that fixes Claude Code's security classifier hanging when using DeepSeek API.

## Quick Verification

Check if the fix is working:

```bash
# Check proxy status
curl -s http://localhost:18920/health | python3 -m json.tool

# Check if ANTHROPIC_BASE_URL is configured
python3 -c "
import json, os
s = json.load(open(os.path.expanduser('~/.claude/settings.json')))
print('ANTHROPIC_BASE_URL:', s.get('env', {}).get('ANTHROPIC_BASE_URL', 'NOT SET'))
"
```

Expected: `ANTHROPIC_BASE_URL` should be `http://localhost:18920`, and the health check should return `"status": "ok"`.

## Restart the Proxy

If the proxy has crashed or is unresponsive:

```bash
# Stop any stale process
pkill -f "bin/proxy" 2>/dev/null; sleep 1

# Start fresh
python3 "${CLAUDE_PLUGIN_ROOT}/bin/proxy" &

# Verify
curl -s http://localhost:18920/health
```

On the next Claude Code session, the SessionStart hook will auto-restart it.

## Check Logs

```bash
ls "${CLAUDE_PLUGIN_DATA}/proxy.log" 2>/dev/null && tail -50 "${CLAUDE_PLUGIN_DATA}/proxy.log"
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `curl localhost:18920/health` fails | Proxy not running | Restart the proxy |
| Port 18920 "address already in use" | Another process on the port | `DEEPSEEK_FIX_PORT=18921` env var to change port |
| Settings `ANTHROPIC_BASE_URL` not set | Bootstrap didn't run | Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure.py` manually |
| Shell `ANTHROPIC_BASE_URL` still active | Shell export overrides settings | Check `~/.zshrc` for `export ANTHROPIC_BASE_URL=...` — comment it out or remove it, then restart Claude Code |
| "Refusing to redirect a non-DeepSeek provider" | You're not using DeepSeek | This plugin is only for DeepSeek users. Disable it: `/plugin disable deepseek-fix` |
| Classifier still hangs after setup | ANTHROPIC_BASE_URL not taking effect | Must restart Claude Code after bootstrap. ANTHROPIC_BASE_URL is read once at startup. |

## Uninstall

To fully remove the deepseek-fix plugin:

1. **Stop the proxy**: `pkill -f "bin/proxy"`
2. **Restore settings**: Remove `ANTHROPIC_BASE_URL` from `~/.claude/settings.json` under the `env` key:
   ```bash
   python3 -c "
   import json, os
   path = os.path.expanduser('~/.claude/settings.json')
   s = json.load(open(path))
   s.get('env', {}).pop('ANTHROPIC_BASE_URL', None)
   if not s['env']: del s['env']
   json.dump(s, open(path, 'w'), indent=2)
   print('Restored')
   "
   ```
   Or restore from backup: `cp ~/.claude/settings.json.deepseek-fix.bak ~/.claude/settings.json`
3. **Re-enable shell export** (if you commented it out): Restore `export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic` in `~/.zshrc`.
4. **Disable/uninstall the plugin**: `/plugin disable deepseek-fix` or `/plugin uninstall deepseek-fix`.
5. **Restart** Claude Code.
