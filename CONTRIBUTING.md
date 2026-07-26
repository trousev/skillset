# Contributing to Skillset Marketplace

Thanks for contributing! This document covers everything you need to know: skill format, plugin structure, quality bar, PR process, and security requirements.

## Quick Start

```bash
# 1. Fork & clone
git clone git@github.com:YOUR_USERNAME/skillset.git
cd skillset

# 2. Create your plugin
mkdir -p plugins/my-skill/skills/my-skill

# 3. Write SKILL.md (see format below)
# 4. Validate
python3 evals/runner/validate.py plugins/my-skill

# 5. Commit & PR
git checkout -b add/my-skill
git add plugins/my-skill
git commit -m "feat: add my-skill plugin"
git push origin add/my-skill
```

## Directory Structure

```
plugins/<plugin-name>/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest (required)
├── skills/
│   └── <skill-name>/
│       └── SKILL.md         # Skill definition (required)
├── agents/                  # Sub-agent definitions (optional)
├── commands/                # Slash commands (optional)
├── hooks/                   # Lifecycle hooks (optional)
└── README.md                # Plugin documentation (required)
```

## Plugin Manifest (`plugin.json`)

Every plugin MUST have `.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Clear description of what this plugin provides and when to use it.",
  "author": {
    "name": "your-github-handle"
  },
  "license": "MIT",
  "keywords": ["category", "use-case"]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | ✅ | kebab-case, lowercase letters/numbers/hyphens, max 64 chars |
| `version` | ✅ | SemVer (`x.y.z`) |
| `description` | ✅ | What it does AND when to use it, max 1024 chars |
| `author` | ✅ | Object with `name` (required) and optional `email` |
| `license` | ✅ | SPDX identifier (MIT, Apache-2.0, etc.) |
| `keywords` | ✅ | Help users discover your plugin |

## Skill Format (`SKILL.md`)

Every skill is a markdown file with YAML frontmatter:

```markdown
---
name: my-skill
description: One sentence on what this skill does AND when Claude should use it. Be specific about the triggering conditions so the skill activates at the right time.
argument-hint: [optional-argument-name]
---

Detailed instructions for Claude. Be opinionated and actionable.
```

### Frontmatter Rules

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | ✅ | kebab-case, lowercase only, max 64 chars. Must match directory name. |
| `description` | ✅ | Max 1024 chars. Describe WHAT it does AND WHEN to trigger. This is how Claude decides to use your skill — write it as a dispatch rule. |
| `argument-hint` | ❌ | Hint shown in slash-command autocomplete (e.g., `[feature-name]`) |
| `model` | ❌ | Override Claude model for this skill (rarely needed) |
| `allowed-tools` | ❌ | Comma-separated tool allowlist |

**Forbidden in frontmatter**: `license`, `metadata`, `version`, `author`, `triggers`, `compatibility` — these go in `plugin.json`, not the skill.

### Reserved Words

Do NOT use these in skill names: `anthropic`, `claude`, `codex`, `copilot`. XML tags are also prohibited.

### Content Guidelines

1. **Keep it under 500 lines.** Move reference material, long examples, or scripts to sibling files (`references/`, `examples.md`, `scripts/`).
2. **Be opinionated.** Claude must be able to execute, not just advise. Use imperative mood: "Search the codebase", "Ask the user", "Write to file".
3. **Include anti-patterns.** A "What NOT to do" section catches common mistakes.
4. **Cross-reference related skills.** Link sibling skills when relevant.
5. **Use `$ARGUMENTS`** for explicit-invocation args in the skill body.

### Good vs Bad Descriptions

| ❌ Bad | ✅ Good |
|--------|---------|
| "Helps with code review" | "Reviews code changes for bugs, security issues, and style violations. Use when the user asks for a code review, PR review, or to check their changes." |
| "A git helper" | "Guides the user through interactive rebase, squash, and fixup workflows. Use when the user asks about rebasing, squashing commits, or cleaning up git history." |
| "Database tools" | "Generates SQL migration files, validates schema changes, and runs safe migrations. Use when the user asks to create a migration, change the database schema, or run DB operations." |

## Quality Bar

Before submitting, ensure your skill:

- [ ] Has a valid `plugin.json` with all required fields
- [ ] Has a `SKILL.md` under 500 lines
- [ ] Uses correct frontmatter (no forbidden fields)
- [ ] Description clearly states WHEN to trigger
- [ ] Instructions are actionable ("do X", not "consider X")
- [ ] Includes anti-patterns section
- [ ] Has a README.md with usage examples
- [ ] Passes `python3 evals/runner/validate.py plugins/<your-plugin>`
- [ ] Contains NO hardcoded secrets, API keys, or tokens
- [ ] Contains NO `curl | bash` or similar unsafe patterns

## Security Requirements

**This is a PUBLIC repository.** We take security seriously.

### Prohibited Content

- ❌ API keys, tokens, or secrets of any kind
- ❌ `curl | bash` or `curl | sh` patterns
- ❌ `eval()` on untrusted input
- ❌ Hardcoded credentials or auth headers
- ❌ Shell injection vectors (`os.system(user_input)`, etc.)
- ❌ Exfiltration attempts (sending data to external servers)
- ❌ Obfuscated or minified code (must be readable)

### If Your Skill Needs API Access

Use MCP server configuration in `.mcp.json` — never hardcode keys. Users provide their own credentials:

```json
{
  "mcpServers": {
    "my-service": {
      "command": "npx",
      "args": ["-y", "@myservice/mcp"],
      "env": {
        "MY_SERVICE_API_KEY": "${MY_SERVICE_API_KEY}"
      }
    }
  }
}
```

### Secrets in Skills

If your skill references environment variables, use `${VAR_NAME}` syntax. Never write the actual value.

## Testing & Validation

### Schema Validation (runs on every PR)

```bash
python3 evals/runner/validate.py plugins/<your-plugin>
```

This checks:
- YAML frontmatter is valid
- Required fields present
- Field format constraints (kebab-case, length limits)
- No forbidden fields
- plugin.json schema
- File structure conventions

### Eval Scenarios (for plugin authors)

Create `evals/<your-plugin>/scenarios.md` with test cases:

```markdown
# Eval Scenarios: my-plugin

## Scenario 1: Basic usage
**Prompt**: "User says: do X with Y"
**Expected behavior**:
- Skill activates
- Claude asks clarifying question about Z
- Output contains section "Foo"

## Scenario 2: Edge case
...
```

See `evals/product-planning/scenarios.md` for an example.

## PR Process

1. **Fork the repo** and create a feature branch
2. **Write your plugin** following this guide
3. **Validate locally**: `python3 evals/runner/validate.py plugins/<name>`
4. **Add eval scenarios** if your plugin has complex behavior
5. **Open a PR** with a descriptive title
6. **CI checks**: Schema validation runs automatically
7. **Review**: A maintainer reviews your contribution
8. **Merge**: Once approved and CI passes

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When |
|--------|------|
| `feat:` | New plugin or skill |
| `fix:` | Bug fix in existing plugin |
| `docs:` | Documentation changes |
| `refactor:` | Restructuring without behavior change |
| `test:` | Adding or updating evals |
| `chore:` | CI, validation, tooling |

### PR Titles

- `feat: add deployment-automation plugin` — new plugin
- `fix: correct edge case in product-planning step 3` — bug fix
- `docs: improve CONTRIBUTING.md with examples` — docs

## Code of Conduct

- Be respectful and constructive in reviews
- Skills are opinionated — that's the point. Disagree with respect.
- Report security issues privately to maintainers — do NOT open a public issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Questions? Open an issue or start a discussion.
