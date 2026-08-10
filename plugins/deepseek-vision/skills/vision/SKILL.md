---
name: vision
description: "Analyze images using GPT-4o vision. Use when the user provides an image (screenshot, mockup, photo) and asks what's in it, what's wrong, how it compares to another image, or any visual analysis question. Essential for DeepSeek sessions which lack native vision. Supports up to 10 images per call for comparison."
argument-hint: "<image...> <prompt>"
---

# /vision — GPT-4o Image Analysis

Sends images to GPT-4o for visual analysis with research-backed system prompts optimized for web design critique, comparison, and reference-based review.

## When to Use

Trigger when:
- The user attaches an image and asks about it ("what's wrong with this layout?", "review this design")
- Multiple images for comparison ("what's different between the mockup and the implementation?")
- Reference-based review ("does this match the design?" with a reference image)
- Any image is pasted/dropped into a DeepSeek session (which cannot see it natively)

Do NOT use for: image generation (use `/generate`), text analysis (the main model handles that).

## Usage

```
/vision screenshot.png "What's wrong with the spacing in this UI?"
/vision mockup.png implementation.png "What are the differences?"
/vision reference.png my-work.png "Does my implementation match the reference?"
```

## Analysis Modes

The skill auto-detects the mode from your prompt and image count:

| Mode | Images | Trigger words | What it does |
|------|--------|---------------|--------------|
| **critique** | 1 | "review", "analyze", "what's wrong" | Full design review: layout, spacing, typography, color, accessibility |
| **compare** | 2+ | "compare", "diff", "difference" | Side-by-side diff table: design vs implementation |
| **reference** | 2+ | "reference", "match this", "should be like" | Extract design system from reference → evaluate against it |

You can override with `--mode critique|compare|reference`.

## System Prompts

Each mode uses a research-backed system prompt that enforces:
- **Inventory-first, judge-second** — GPT-4o lists what it sees before critiquing (reduces hallucinations)
- **Evidence rule** — every claim cites a specific element and location
- **Relative measurements** — never states absolute pixels (spatial reasoning is a known weakness)
- **Structured output** — Markdown with Summary, Issues (P0/P1/P2), What Works, and Actionable Fixes

For compare/reference modes, output includes a comparison table with Verdict (missing/major drift/minor drift/matches) and concrete fix instructions.

## How It Works

1. Resolve image paths → verify each file exists (PNG, JPEG, GIF, WebP, ≤20MB)
2. Auto-detect mode from prompt language + image count
3. Build API request with mode-specific system prompt + labeled images
4. Call GPT-4o via `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vision_api.py" vision`
5. Return the Markdown analysis to the user

## Error Handling

| Situation | Behavior |
|-----------|----------|
| No API key | Clear error with setup link |
| Image not found | Names the missing file |
| Image >20MB | Rejection with resize suggestion |
| API error | Shows OpenAI's error message |
| Network error | Reports, suggests retry |
| >10 images | Rejected (API limit) |

## Setup

First time? Set your OpenAI API key:

```bash
export DEEPSEEK_VISION_API_KEY=sk-...
```

Or for persistent storage:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vision_api.py" setup sk-...
```

Get a key: https://platform.openai.com/api-keys

## Tips

- **Name files descriptively** — GPT-4o references images by their filenames
- **For comparison, order matters** — first image = design/ground truth
- **Be specific in your prompt** — "What are the spacing differences?" beats "compare"
- **Iterate with /generate** — generate a mockup, then review it with /vision
- **Cost**: ~$0.01-0.03 per call at high detail (~765-1105 tokens per 1080p image)
