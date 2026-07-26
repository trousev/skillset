#!/usr/bin/env python3
"""Schema validator for skillset plugins.

Validates:
- plugin.json schema
- SKILL.md frontmatter
- File structure conventions
- Security anti-patterns

Usage:
    python3 validate.py plugins/<plugin-name>
    python3 validate.py --all          # validate all plugins
    python3 validate.py --marketplace   # validate marketplace.json only

Exit codes:
    0 - all valid
    1 - validation errors found
    2 - usage error
"""

import json
import os
import re
import sys
import yaml  # type: ignore


# ── Configuration ────────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGINS_DIR = os.path.join(REPO_ROOT, "plugins")
MARKETPLACE_FILE = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")

MAX_SKILL_LINES = 500
MAX_DESCRIPTION_LENGTH = 1024
MAX_NAME_LENGTH = 64

FORBIDDEN_FRONTMATTER = {"license", "metadata", "version", "author", "triggers", "compatibility"}
RESERVED_WORDS = {"anthropic", "claude", "codex", "copilot"}

SECURITY_PATTERNS = [
    (r"curl\s+.*\|\s*(?:ba)?sh", "curl | bash pattern found"),
    (r'sk-[a-zA-Z0-9_-]{20,}', "possible API key in file"),
    (r'sk-or-v1-[a-zA-Z0-9_-]{20,}', "possible OpenRouter API key"),
    (r'tgp_v1-[a-zA-Z0-9_-]{20,}', "possible Together API key"),
    (r'hf_[a-zA-Z0-9_-]{20,}', "possible HuggingFace token"),
    (r'AIza[0-9A-Za-z_-]{35}', "possible Google API key"),
    (r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", "possible JWT token"),
    (r"BEGIN\s+(?:RSA|EC|DSA|OPENSSH)?\s*PRIVATE KEY", "private key in file"),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def error(msg: str) -> None:
    print(f"  ❌ {msg}")


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Parse YAML frontmatter from markdown content. Returns (metadata, body)."""
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content
    try:
        meta = yaml.safe_load(parts[1])
        return meta, parts[2]
    except yaml.YAMLError as e:
        print(f"  ❌ YAML parse error in frontmatter: {e}")
        return None, content


def check_security(filepath: str, content: str) -> list[str]:
    """Check file content for security issues. Returns list of findings."""
    findings = []
    for pattern, msg in SECURITY_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Mask the match for safe printing
            masked = match[:8] + "..." if len(match) > 8 else match
            findings.append(f"{msg}: {masked}")
    return findings


# ── Validators ───────────────────────────────────────────────────────────────

def validate_marketplace() -> bool:
    """Validate .claude-plugin/marketplace.json"""
    print(f"\n📦 Validating marketplace: {MARKETPLACE_FILE}")
    all_ok = True

    if not os.path.exists(MARKETPLACE_FILE):
        error(f"File not found: {MARKETPLACE_FILE}")
        return False

    try:
        data = json.loads(read_file(MARKETPLACE_FILE))
    except json.JSONDecodeError as e:
        error(f"Invalid JSON: {e}")
        return False

    # Required fields
    for field in ["name", "owner", "plugins"]:
        if field not in data:
            error(f"Missing required field: '{field}'")
            all_ok = False

    if "name" in data:
        if not re.match(r"^[a-z0-9-]+$", data["name"]):
            error(f"Marketplace name '{data['name']}' must be kebab-case")
            all_ok = False
        else:
            ok(f"name: {data['name']}")

    if "owner" in data:
        if isinstance(data["owner"], dict):
            if "name" not in data["owner"]:
                error("owner.name is required")
                all_ok = False
            else:
                ok(f"owner: {data['owner']['name']}")
        else:
            ok(f"owner: {data['owner']}")

    if "plugins" in data:
        if not isinstance(data["plugins"], list):
            error("'plugins' must be an array")
            all_ok = False
        else:
            ok(f"plugins: {len(data['plugins'])} plugin(s)")
            for i, plugin in enumerate(data["plugins"]):
                if not isinstance(plugin, dict):
                    error(f"plugin[{i}] is not an object")
                    all_ok = False
                    continue
                if "name" not in plugin:
                    error(f"plugin[{i}] missing 'name'")
                    all_ok = False
                if "source" not in plugin:
                    error(f"plugin[{i}] missing 'source'")
                    all_ok = False

    return all_ok


def validate_plugin_json(plugin_dir: str) -> bool:
    """Validate .claude-plugin/plugin.json"""
    plugin_json = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    print(f"\n📋 Validating: {plugin_json}")
    all_ok = True

    if not os.path.exists(plugin_json):
        error(f"File not found: {plugin_json}")
        return False

    try:
        data = json.loads(read_file(plugin_json))
    except json.JSONDecodeError as e:
        error(f"Invalid JSON: {e}")
        return False

    # Required fields
    required = {
        "name": str,
        "version": str,
        "description": str,
        "author": str,
        "license": str,
    }
    for field, ftype in required.items():
        if field not in data:
            error(f"Missing required field: '{field}'")
            all_ok = False
        elif not isinstance(data[field], ftype):
            error(f"'{field}' must be a {ftype.__name__}")
            all_ok = False

    if "name" in data:
        if not re.match(r"^[a-z0-9-]+$", data["name"]):
            error(f"Plugin name '{data['name']}' must be kebab-case")
            all_ok = False
        if len(data["name"]) > MAX_NAME_LENGTH:
            error(f"Plugin name too long ({len(data['name'])} > {MAX_NAME_LENGTH})")
            all_ok = False
        ok(f"name: {data['name']}")

    if "version" in data:
        if not re.match(r"^\d+\.\d+\.\d+$", data["version"]):
            error(f"Version '{data['version']}' must be SemVer (x.y.z)")
            all_ok = False
        else:
            ok(f"version: {data['version']}")

    if "description" in data:
        if len(data["description"]) > MAX_DESCRIPTION_LENGTH:
            error(f"Description too long ({len(data['description'])} > {MAX_DESCRIPTION_LENGTH})")
            all_ok = False
        ok(f"description: {len(data['description'])} chars")

    if "license" in data:
        ok(f"license: {data['license']}")

    return all_ok


def validate_skill_md(skill_dir: str) -> bool:
    """Validate skills/<name>/SKILL.md"""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    print(f"\n📝 Validating: {skill_md}")
    all_ok = True

    if not os.path.exists(skill_md):
        error(f"File not found: {skill_md}")
        return False

    content = read_file(skill_md)
    lines = content.split("\n")

    # Line count
    if len(lines) > MAX_SKILL_LINES:
        error(f"SKILL.md too long ({len(lines)} > {MAX_SKILL_LINES} lines)")
        all_ok = False
    else:
        ok(f"length: {len(lines)} lines")

    # Security scan
    security_findings = check_security(skill_md, content)
    for finding in security_findings:
        error(f"Security: {finding}")
        all_ok = False
    if not security_findings:
        ok("security scan: clean")

    # Frontmatter
    meta, body = parse_frontmatter(content)
    if meta is None:
        error("Missing or invalid YAML frontmatter")
        return False

    # Required frontmatter fields
    if "name" not in meta:
        error("frontmatter missing 'name'")
        all_ok = False
    else:
        name = meta["name"]
        if not re.match(r"^[a-z0-9-]+$", name):
            error(f"Skill name '{name}' must be kebab-case")
            all_ok = False
        if len(name) > MAX_NAME_LENGTH:
            error(f"Skill name too long ({len(name)} > {MAX_NAME_LENGTH})")
            all_ok = False
        # Check reserved words
        for word in RESERVED_WORDS:
            if word in name.lower():
                error(f"Skill name contains reserved word: '{word}'")
                all_ok = False
        # Check XML tags
        if re.search(r"<[^>]+>", name):
            error("Skill name contains XML tags")
            all_ok = False
        ok(f"name: {name}")

    if "description" not in meta:
        error("frontmatter missing 'description'")
        all_ok = False
    else:
        desc = meta["description"]
        if len(desc) > MAX_DESCRIPTION_LENGTH:
            error(f"Description too long ({len(desc)} > {MAX_DESCRIPTION_LENGTH})")
            all_ok = False
        ok(f"description: {len(desc)} chars")

    # Forbidden frontmatter fields
    for field in FORBIDDEN_FRONTMATTER:
        if field in meta:
            error(f"Forbidden frontmatter field: '{field}' (belongs in plugin.json)")
            all_ok = False

    return all_ok


def validate_plugin(plugin_dir: str) -> bool:
    """Validate an entire plugin directory."""
    plugin_name = os.path.basename(plugin_dir)
    print(f"\n{'='*60}")
    print(f"🔍 Validating plugin: {plugin_name}")
    print(f"{'='*60}")

    all_ok = True

    # Validate plugin.json
    if not validate_plugin_json(plugin_dir):
        all_ok = False

    # Find and validate all SKILL.md files
    skills_dir = os.path.join(plugin_dir, "skills")
    if os.path.isdir(skills_dir):
        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name)
            if os.path.isdir(skill_path):
                if not validate_skill_md(skill_path):
                    all_ok = False
    else:
        warn(f"No skills/ directory found in {plugin_dir}")

    # Check for README.md
    readme = os.path.join(plugin_dir, "README.md")
    if os.path.exists(readme):
        ok("README.md: present")
    else:
        warn("No README.md found (recommended)")

    return all_ok


def validate_all() -> bool:
    """Validate entire marketplace."""
    all_ok = True

    if not validate_marketplace():
        all_ok = False

    if not os.path.isdir(PLUGINS_DIR):
        error(f"Plugins directory not found: {PLUGINS_DIR}")
        return False

    plugins = [
        d for d in os.listdir(PLUGINS_DIR)
        if os.path.isdir(os.path.join(PLUGINS_DIR, d))
        and not d.startswith(".")
    ]

    if not plugins:
        warn("No plugins found")
        return all_ok

    for plugin_name in sorted(plugins):
        plugin_dir = os.path.join(PLUGINS_DIR, plugin_name)
        if not validate_plugin(plugin_dir):
            all_ok = False

    return all_ok


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    arg = sys.argv[1]

    if arg == "--all":
        ok_ = validate_all()
    elif arg == "--marketplace":
        ok_ = validate_marketplace()
    else:
        plugin_dir = arg
        if not os.path.isdir(plugin_dir):
            print(f"Error: not a directory: {plugin_dir}")
            sys.exit(2)
        ok_ = validate_plugin(plugin_dir)

    print(f"\n{'='*60}")
    if ok_:
        print("🎉 All validations passed!")
        sys.exit(0)
    else:
        print("💥 Validation errors found. Fix them before submitting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
