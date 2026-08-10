#!/usr/bin/env python3
"""SessionStart hook for deepseek-vision plugin.

Idempotent. Safe to run repeatedly.
Checks for a configured OpenAI API key. If missing, prints setup instructions.
Does NOT block session startup — always exits 0.

API key resolution order:
  1. DEEPSEEK_VISION_API_KEY env var
  2. ~/.claude/settings.json env.DEEPSEEK_VISION_API_KEY
"""

import json
import os
import sys

SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
ENV_VAR = "DEEPSEEK_VISION_API_KEY"


def find_api_key():
    """Check all sources for an API key. Returns (key_found, source_description)."""
    key = os.environ.get(ENV_VAR, "")
    if key:
        return True, f"${ENV_VAR} environment variable"

    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                settings = json.load(f)
            key = settings.get("env", {}).get(ENV_VAR, "")
            if key:
                return True, f"~/.claude/settings.json (env.{ENV_VAR})"
        except (json.JSONDecodeError, OSError):
            pass

    return False, ""


def mask_key(key):
    """Show only first 7 and last 4 chars of a key."""
    if len(key) <= 12:
        return key[:3] + "..." + key[-3:]
    return key[:7] + "..." + key[-4:]


def main():
    found, source = find_api_key()

    if found:
        print(f"deepseek-vision: configured ({source})")
        return

    print(f"\n  deepseek-vision: No API key configured.", file=sys.stderr)
    print(f"  /vision and /generate need an OpenAI API key.", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"  Get a key: https://platform.openai.com/api-keys", file=sys.stderr)
    print(f"  Then set it up:", file=sys.stderr)
    print(f"    export DEEPSEEK_VISION_API_KEY=sk-...", file=sys.stderr)
    print(f"  Or ask me: 'set up deepseek-vision' for guided setup.", file=sys.stderr)
    print(f"", file=sys.stderr)


if __name__ == "__main__":
    main()
