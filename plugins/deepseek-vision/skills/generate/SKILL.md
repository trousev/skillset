---
name: generate
description: "Generate an image from a text prompt using DALL-E 3. Use when the user asks to create an image, generate a mockup, make a visual, design a logo/icon/illustration, or produce any image from a description. Saves the result locally and returns the file path."
argument-hint: "<prompt>"
---

# /generate — DALL-E 3 Image Generation

Generates images from text descriptions using OpenAI's DALL-E 3. Useful for creating design mockups, placeholder images, icons, illustrations, and visual references — all from within Claude Code.

## When to Use

Trigger this skill when:
- The user asks to "generate an image of...", "create a mockup...", "make a visual..."
- The user wants a quick design reference or wireframe visual
- The user wants to create an image to later analyze with `/vision`
- The user says "draw", "render", "illustrate", "visualize"

Do NOT use for:
- Analyzing existing images (use `/vision`)
- Photo editing/manipulation (DALL-E only generates, it doesn't edit)

## Usage

```
/generate "A clean SaaS dashboard with cards, sidebar nav, and a data table"
/generate "A minimalist login page with email/password fields and a gradient background" --size 1792x1024
/generate "A blue rounded button with white text saying 'Get Started'" --size 1024x1024 --style natural
```

## How It Works

1. **Build prompt** — Your description is sent to DALL-E 3. DALL-E automatically rewrites brief prompts for better results (the revised prompt is shown).
2. **Generate** — DALL-E produces a 1024x1024 (or landscape/portrait) image.
3. **Download & save** — The image is downloaded from the OpenAI CDN and saved to a local file.
4. **Return path** — The file path is returned so you can reference it or pipe it to `/vision`.

## Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--size` | `1024x1024`, `1792x1024`, `1024x1792` | `1024x1024` | Image dimensions (square / landscape / portrait) |
| `--quality` | `standard`, `hd` | `standard` | HD gives more detail but costs more |
| `--style` | `vivid`, `natural` | `vivid` | Vivid = dramatic/hyper-real; Natural = more realistic/plain |
| `--output` / `-o` | file path | auto-generated | Where to save the image |

## Output

The skill:
1. Prints the revised prompt (what DALL-E actually generated from)
2. Downloads the generated image
3. Saves it to a timestamped file in the current directory: `dalle-<timestamp>.png`
4. Returns the file path

Example output:
```
Generated: dalle-20260810-143522.png
Prompt: "A clean modern SaaS dashboard with sidebar navigation..."
Size: 1024x1024 | Quality: standard | Style: vivid
```

## Error Handling

| Situation | Behavior |
|-----------|----------|
| No API key | Clear error with setup instructions |
| Content policy violation | Shows OpenAI's refusal reason; suggest rephrasing |
| Rate limit | Reported with retry advice |
| Network error | Retry once, then report |
| Empty prompt | Immediately rejected |
| Download failure | Image URL still shown so user can download manually |

## API Key Setup

Same key as `/vision`. See `/vision`'s setup section or run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ensure.py" --interactive
```

## Implementation (for Claude)

When invoked, run:

```bash
# Generate the image
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vision_api.py" generate \
  "the user's prompt" \
  --size 1024x1024 \
  --output ./dalle-$(date +%Y%m%d-%H%M%S).png
```

The script outputs JSON with `url`, `revised_prompt`, and saves the image locally. Present the output path and revised prompt to the user. If the JSON contains an `error` key, handle per the error table.

**Important:** Pass the user's exact prompt through. DALL-E 3 will auto-rewrite it for better generation — the revised version is shown alongside the result.

## Pro Tips

- **Be specific:** "A blue rounded button with white text 'Sign Up' on a light gray background with subtle shadow" is better than "a button"
- **Iterate with `/vision`:** Generate a mockup, then use `/vision` to analyze it: `/vision dalle-20260810.png "Critique this design"`
- **Style matters:** Use `--style natural` for realistic references, `--style vivid` for creative/artistic outputs
- **Landscape for dashboards:** Use `--size 1792x1024` for wide layouts like dashboards and landing pages
- **Portrait for mobile:** Use `--size 1024x1792` for mobile screen mockups
- **Cost:** Standard quality = ~$0.04/image; HD = ~$0.08/image
