# deepseek-vision

Brings vision and image generation to DeepSeek-powered Claude Code sessions via OpenAI.

DeepSeek models are text-only — every screenshot, mockup, or design reference pasted into a session is invisible. This plugin bridges that gap with two skills:

- **`/vision`** — GPT-4o image analysis with research-backed system prompts for web design critique, comparison, and reference-based review
- **`/generate`** — OpenAI image generation (`gpt-image-1`) from text prompts, saved locally

## Installation

```bash
claude marketplace add trousev/skillset
claude plugin install deepseek-vision@trousev-skillset
```

## Setup

You need an OpenAI API key. The plugin uses its own key (`DEEPSEEK_VISION_API_KEY`) — separate from any existing `OPENAI_API_KEY` to avoid surprise bills.

**Option 1: Environment variable**
```bash
export DEEPSEEK_VISION_API_KEY=sk-...
# Add to ~/.zshrc for persistence
```

**Option 2: Claude Code settings**
```bash
python3 ~/.claude/plugins/cache/trousev-skillset/deepseek-vision/*/scripts/vision_api.py setup sk-...
```
This validates the key, then stores it in `~/.claude/settings.json`.

**Get a key:** https://platform.openai.com/api-keys

On session start, the plugin checks for a key and prints setup instructions if missing.

## Skills

### /vision — Image Analysis

Analyze one or more images using GPT-4o. Auto-detects the analysis mode from your prompt:

- **Critique** (1 image): Full design review — layout, spacing, typography, color, accessibility. Outputs prioritized issues (P0/P1/P2) with concrete fixes.
- **Compare** (2+ images): Mockup vs implementation diff table with verdicts (missing/major drift/minor drift/matches).
- **Reference** (2+ images): Extracts the design system from a reference image, evaluates the implementation against it.

```
/vision screenshot.png "What's wrong with the spacing?"
/vision mockup.png implementation.png "What are the differences?"
/vision reference.png my-work.png "Does this match the reference?"
```

### /generate — Image Generation

Generate images from text prompts using OpenAI's image generation API.

```
/generate "A clean SaaS dashboard with cards and data table"
/generate "A minimalist login form" --size 1024x1536
```

Options: `--size` (1024x1024|1024x1536|1536x1024), `--quality` (standard|high), `--model` (gpt-image-1|gpt-image-1-mini|gpt-image-2|dall-e-3).

## How They Work Together

Generate a mockup, then review it:

```bash
/generate "A modern settings page with toggle switches" -o settings-mockup.png
/vision settings-mockup.png "Review this design for accessibility issues"
```

Or compare a generated reference against your implementation:

```bash
/generate "A blue card component with drop shadow" -o card-reference.png
/vision card-reference.png src/components/Card.tsx "Does my card match the reference?"
```

## Privacy

Images are sent to OpenAI's API for processing. Don't use for proprietary designs you can't share externally. The plugin never logs or stores images — they're encoded inline in the API request and discarded after the response.

## Requirements

- OpenAI API key with access to GPT-4o and DALL-E 3
- Python 3.8+ (stdlib only — no pip dependencies)

## Uninstall

```bash
claude plugin uninstall deepseek-vision@trousev-skillset
# Remove the stored key:
python3 -c "
import json, os
p = os.path.expanduser('~/.claude/settings.json')
if os.path.exists(p):
    s = json.load(open(p))
    s.get('env', {}).pop('DEEPSEEK_VISION_API_KEY', None)
    if not s['env']: del s['env']
    json.dump(s, open(p, 'w'), indent=2)
    print('Key removed')
"
```
