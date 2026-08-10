---
name: generate
description: "Generate an image from a text prompt using OpenAI's image generation API. Use when the user asks to create an image, generate a mockup, make a visual, design a logo/icon/illustration, or produce any image from a description. Saves the result locally and returns the file path."
argument-hint: "<prompt>"
---

# /generate — OpenAI Image Generation

Generates images from text descriptions using OpenAI's image generation models (`gpt-image-1`, `gpt-image-2`, or `dall-e-3`). Useful for creating design mockups, placeholder images, icons, illustrations, and visual references — all from within Claude Code.

## When to Use

Trigger this skill when:
- The user asks to "generate an image of...", "create a mockup...", "make a visual..."
- The user wants a quick design reference or wireframe visual
- The user wants to create an image to later analyze with `/vision`
- The user says "draw", "render", "illustrate", "visualize"

Do NOT use for:
- Analyzing existing images (use `/vision`)
- Photo editing/manipulation (generation only, no editing)

## Usage

```
/generate "A clean SaaS dashboard with cards, sidebar nav, and a data table"
/generate "A minimalist login page with a gradient background" --size 1024x1536
/generate "A blue rounded button with white text" --quality high
```

## How It Works

1. **Build prompt** — Your description is sent to OpenAI's image generation API.
2. **Generate** — The model produces an image (PNG, returned as base64).
3. **Save** — The image is decoded and saved to a local file.
4. **Return path** — The file path is returned so you can use it directly or pipe it to `/vision`.

## Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--size` | `1024x1024`, `1024x1536`, `1536x1024` | `1024x1024` | Image dimensions (square / portrait / landscape) |
| `--quality` | `standard`, `high` | `standard` | Output quality |
| `--model` | `gpt-image-1`, `gpt-image-1-mini`, `gpt-image-2`, `dall-e-3` | `gpt-image-1` | Model to use |
| `--output` / `-o` | file path | `generated-<timestamp>.png` | Where to save the image |

## Output

The skill:
1. Generates the image
2. Saves it to the specified path (or auto-named with timestamp)
3. Reports the file path and size

Example output:
```
Image saved to: generated-20260810-143522.png (1127 KB)
```

## Error Handling

| Situation | Behavior |
|-----------|----------|
| No API key | Clear error with setup instructions |
| Content policy violation | Shows OpenAI's refusal reason; suggest rephrasing |
| Rate limit | Reported with retry advice |
| Network error | Reports, suggests retry |
| Empty prompt | Immediately rejected |

## API Key Setup

Same key as `/vision`. See `/vision`'s setup section or run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vision_api.py" setup sk-...
```

## Implementation (for Claude)

When invoked, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vision_api.py" generate \
  "the user's prompt" \
  --size 1024x1024 \
  --output ./generated-$(date +%Y%m%d-%H%M%S).png
```

The script outputs JSON and saves the image locally. Present the output path to the user. If the JSON contains an `error` key, handle per the error table.

## Pro Tips

- **Be specific:** "A blue rounded button with white text 'Sign Up' on a light gray background with subtle shadow" is better than "a button"
- **Iterate with `/vision`:** Generate a mockup, then use `/vision` to analyze it: `/vision generated-dashboard.png "Critique this design"`
- **Portrait for mobile:** Use `--size 1024x1536` for mobile screen mockups
- **Landscape for dashboards:** Use `--size 1536x1024` for wide layouts like dashboards
- **Cost:** Standard quality = ~$0.04/image
