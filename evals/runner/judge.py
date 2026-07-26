#!/usr/bin/env python3
"""LLM-as-judge for Claude Code skill evals.

Reads an eval scenario, runs the skill via Claude Code CLI, and judges the output
using DeepSeek's Anthropic-compatible API.

Usage:
    python3 judge.py --scenario evals/product-planning/scenarios.md --skill product-planning

Environment:
    DEEPSEEK_API_KEY    DeepSeek API key (required)
    DEEPSEEK_BASE_URL   Defaults to https://api.deepseek.com/anthropic

Exit codes:
    0 - all scenarios passed
    1 - one or more scenarios failed
    2 - configuration error
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error


# ── Configuration ────────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic")

# DeepSeek Anthropic-compatible endpoint
MESSAGES_URL = f"{DEEPSEEK_BASE_URL}/v1/messages"

JUDGE_MODEL = "deepseek-v4-pro[1m]"


# ── Scenario parser ──────────────────────────────────────────────────────────

def parse_scenarios(scenario_file: str) -> list[dict]:
    """Parse eval scenarios from markdown file.

    Expected format:
        ## Scenario: <name>
        **Prompt**: <what the user says>
        **Expected behaviors**:
        - <behavior 1>
        - <behavior 2>

        ## Scenario: <name>
        ...
    """
    scenarios = []
    current = None

    with open(scenario_file, "r") as f:
        for line in f:
            line = line.rstrip()

            # New scenario
            if line.startswith("## Scenario:"):
                if current:
                    scenarios.append(current)
                current = {
                    "name": line.replace("## Scenario:", "").strip(),
                    "prompt": "",
                    "expected": [],
                }

            elif current is not None:
                if line.startswith("**Prompt**:"):
                    current["prompt"] = line.replace("**Prompt**:", "").strip()
                elif line.startswith("- "):
                    current["expected"].append(line.replace("- ", "").strip())
                elif line.startswith("**Expected") and "**:" in line:
                    # Alternative format: **Expected behavior**: text
                    pass

    if current:
        scenarios.append(current)

    return scenarios


# ── DeepSeek API client ──────────────────────────────────────────────────────

def call_deepseek(system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
    """Call the DeepSeek Anthropic-compatible Messages API."""
    if not DEEPSEEK_API_KEY:
        print("ERROR: DEEPSEEK_API_KEY environment variable is not set", file=sys.stderr)
        sys.exit(2)

    body = {
        "model": JUDGE_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_message}
        ],
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        MESSAGES_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": DEEPSEEK_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            # Anthropic-compatible response format
            content = result.get("content", [])
            if isinstance(content, list):
                return "".join(
                    block.get("text", "")
                    for block in content
                    if block.get("type") == "text"
                )
            return str(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API HTTP {e.code}: {body}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"API connection error: {e.reason}", file=sys.stderr)
        raise


# ── Judgment logic ───────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are an evaluator for Claude Code skills. Your job is to judge whether a skill's output meets the expected behaviors defined in an eval scenario.

You will receive:
1. The scenario description (what the user asked)
2. The expected behaviors
3. The actual skill output

Judge PASS or FAIL. Be fair but strict:
- PASS: the output clearly demonstrates all expected behaviors
- FAIL: one or more expected behaviors are missing, incorrect, or insufficiently demonstrated

Respond with ONLY a JSON object:
{"verdict": "PASS"|"FAIL", "reasoning": "<one paragraph explaining your judgment>"}"""


def judge_output(scenario: dict, skill_output: str) -> dict:
    """Use LLM to judge whether skill output meets expectations."""
    user_message = f"""## Scenario
{scenario['name']}

## User Prompt
{scenario['prompt']}

## Expected Behaviors
{chr(10).join(f'- {e}' for e in scenario['expected'])}

## Actual Skill Output
{skill_output[:4000]}

Judge whether the actual output demonstrates all expected behaviors."""

    try:
        result = call_deepseek(JUDGE_SYSTEM_PROMPT, user_message, max_tokens=512)
        # Try to parse JSON from response
        # Find JSON object in response
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
        return {"verdict": "FAIL", "reasoning": f"Could not parse judge response: {result[:200]}"}
    except Exception as e:
        return {"verdict": "FAIL", "reasoning": f"Judge API call failed: {str(e)}"}


# ── Skill runner ─────────────────────────────────────────────────────────────

def run_skill(skill_name: str, prompt: str) -> str:
    """Run a skill using Claude Code CLI and capture output."""
    plugin_dir = os.path.join(REPO_ROOT, "plugins", skill_name)

    if not os.path.isdir(plugin_dir):
        print(f"ERROR: plugin directory not found: {plugin_dir}", file=sys.stderr)
        sys.exit(2)

    # Check if claude CLI is available
    try:
        subprocess.run(["claude", "--version"], capture_output=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("WARNING: 'claude' CLI not found. Running in dry-run mode.", file=sys.stderr)
        return _dry_run_skill(skill_name, prompt)

    # Run claude with the plugin
    try:
        result = subprocess.run(
            [
                "claude",
                "--plugin-dir", plugin_dir,
                "-p", prompt,
                "--output-format", "text",
                "--max-turns", "15",
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes
            env={**os.environ, "CLAUDE_CODE_SKIP_HOOKS": "1"},
        )
        return result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return "[TIMEOUT] Skill execution exceeded 5 minutes"
    except Exception as e:
        return f"[ERROR] Failed to run skill: {str(e)}"


def _dry_run_skill(skill_name: str, prompt: str) -> str:
    """Return a placeholder when claude CLI is not available."""
    skill_md = os.path.join(REPO_ROOT, "plugins", skill_name, "skills", skill_name, "SKILL.md")
    with open(skill_md, "r") as f:
        content = f.read()
    return f"""[DRY RUN MODE - claude CLI not available]

Skill: {skill_name}
Prompt: {prompt}
SKILL.md length: {len(content)} chars

Skill frontmatter and content validated separately via validate.py.
LLM-based eval requires 'claude' CLI installed with API access.
"""


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run LLM-based evals for a skill")
    parser.add_argument("--scenario", required=True, help="Path to scenario markdown file")
    parser.add_argument("--skill", required=True, help="Skill name (plugin directory name)")
    parser.add_argument("--dry-run", action="store_true", help="Parse scenarios without running")
    args = parser.parse_args()

    scenarios = parse_scenarios(args.scenario)
    if not scenarios:
        print(f"No scenarios found in {args.scenario}")
        sys.exit(2)

    print(f"📋 Found {len(scenarios)} scenario(s) in {args.scenario}")
    print(f"🎯 Testing skill: {args.skill}\n")

    passed = 0
    failed = 0

    for i, scenario in enumerate(scenarios, 1):
        print(f"{'─'*60}")
        print(f"Scenario {i}/{len(scenarios)}: {scenario['name']}")
        print(f"  Prompt: {scenario['prompt'][:100]}...")
        print(f"  Expected: {len(scenario['expected'])} behavior(s)")

        if args.dry_run:
            print("  ⏭️  DRY RUN - skipping execution\n")
            continue

        # Run the skill
        print("  ⏳ Running skill...")
        output = run_skill(args.skill, scenario["prompt"])
        print(f"  Output: {len(output)} chars")

        # Judge the output
        print("  ⚖️  Judging...")
        verdict = judge_output(scenario, output)
        print(f"  Verdict: {verdict.get('verdict', 'FAIL')}")
        print(f"  Reason: {verdict.get('reasoning', 'N/A')[:200]}")

        if verdict.get("verdict") == "PASS":
            passed += 1
        else:
            failed += 1

        # Rate limit: wait between scenarios
        if i < len(scenarios):
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {len(scenarios)} total")
    print(f"{'='*60}")

    if failed > 0:
        sys.exit(1)
    else:
        print("🎉 All scenarios passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
