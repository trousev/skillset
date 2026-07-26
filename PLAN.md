# Marketplace Implementation Plan

## Architecture

```
skillset/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace manifest
├── .github/
│   ├── workflows/
│   │   ├── validate.yml          # Schema validation on every PR
│   │   └── evals.yml             # LLM-based evals (trusted forks only)
│   └── CODEOWNERS                # Restrict evals to trusted contributors
├── plugins/
│   └── product-planning/
│       ├── .claude-plugin/
│       │   └── plugin.json       # Plugin manifest
│       ├── skills/
│       │   └── product-planning/
│       │       └── SKILL.md      # Ported from OpenCode feature-planning
│       └── README.md
├── evals/
│   ├── runner/
│   │   ├── eval.sh               # Eval runner script
│   │   └── judge.py              # LLM-based judge (stdlib-only)
│   └── product-planning/
│       ├── scenarios.md          # Eval scenarios
│       └── expected/             # Expected outputs
├── CONTRIBUTING.md               # Contribution guidelines
├── PLAN.md                       # This file
├── LICENSE
└── README.md
```

## Tasks

### 1. Marketplace Foundation
- Create `.claude-plugin/marketplace.json`
- Create `plugins/product-planning/.claude-plugin/plugin.json`
- Write CONTRIBUTING.md with guidelines from research
- Update README.md with install instructions

### 2. Port product-planning skill
- Adapt OpenCode `feature-planning` SKILL.md → Claude Code `product-planning` SKILL.md
- Adjust frontmatter format (OpenCode → Claude Code)
- Keep the 4-step interview process intact

### 3. Evals System
- Design eval format: scenario → run skill → judge output
- Create `judge.py` — stdlib-only Python, calls DeepSeek API for LLM-as-judge
- Create eval scenarios for product-planning
- GitHub Actions: `validate.yml` (schema check) + `evals.yml` (LLM evals, trusted only)

### 4. Security (CRITICAL — repo is PUBLIC)
- Evals workflow: runs ONLY on `pull_request_target` from trusted forks
- Or: `workflow_run` pattern — validation runs on PR, evals run after merge to main
- API key is stored as GitHub Secret, NEVER echoed/logged
- Validate PR author is in trusted list before running LLM evals
- `CODEOWNERS` restricts workflow changes

## Key Decisions
- **Eval trigger**: Run on push to main and on `workflow_dispatch` only. PRs from forks NEVER trigger LLM evals. Contributors see eval results after merge.
- **LLM backend**: DeepSeek API (Anthropic-compatible endpoint) — matches user's setup
- **Skill format**: Claude Code native `skills/<name>/SKILL.md` with YAML frontmatter
