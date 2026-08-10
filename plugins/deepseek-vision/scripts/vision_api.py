#!/usr/bin/env python3
"""OpenAI API utilities for deepseek-vision plugin.

Provides:
  - check() -> bool          Validate API key
  - vision(image_paths, prompt, mode) -> str   GPT-4o image analysis
  - generate(prompt, ...) -> dict              DALL-E image generation

API key resolution order:
  1. DEEPSEEK_VISION_API_KEY env var
  2. ~/.claude/settings.json env.DEEPSEEK_VISION_API_KEY
Does NOT fall back to OPENAI_API_KEY — uses its own key to avoid surprise bills.
"""

import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error


def _load_api_key():
    """Resolve API key from env or settings.json. Returns (key, source)."""
    # 1. Dedicated env var
    key = os.environ.get("DEEPSEEK_VISION_API_KEY", "")
    if key:
        return key, "DEEPSEEK_VISION_API_KEY env var"

    # 2. Check settings.json
    settings_path = os.path.expanduser("~/.claude/settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path) as f:
                settings = json.load(f)
            key = settings.get("env", {}).get("DEEPSEEK_VISION_API_KEY", "")
            if key:
                return key, "~/.claude/settings.json"
        except (json.JSONDecodeError, OSError):
            pass

    return "", "none"


def _read_settings():
    """Read settings.json safely. Returns dict (empty on failure)."""
    settings_path = os.path.expanduser("~/.claude/settings.json")
    if not os.path.exists(settings_path):
        return {}
    try:
        with open(settings_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_settings(settings):
    """Atomically write settings.json."""
    settings_path = os.path.expanduser("~/.claude/settings.json")
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    content = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    tmp = settings_path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, settings_path)


def check():
    """Validate the API key with a cheap /v1/models call.

    Returns:
        dict with keys: valid (bool), message (str), source (str)
    """
    api_key, source = _load_api_key()
    if not api_key:
        return {
            "valid": False,
            "message": (
                "No API key found. Set DEEPSEEK_VISION_API_KEY:\n"
                "  export DEEPSEEK_VISION_API_KEY=sk-...\n"
                "  Or run: python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure.py --interactive"
            ),
            "source": "none",
        }

    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return {"valid": True, "message": f"API key is valid ({source})", "source": source}
            return {"valid": False, "message": f"Unexpected status {resp.status}", "source": source}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {
                "valid": False,
                "message": "API key rejected — check for typos or a revoked key.",
                "source": source,
            }
        return {"valid": False, "message": f"HTTP {e.code}: {e.reason}", "source": source}
    except urllib.error.URLError as e:
        return {"valid": False, "message": f"Network error: {e.reason}", "source": source}


def _image_to_data_url(path):
    """Convert an image file to a data URL for the OpenAI API.

    Supports png, jpeg, gif, webp. Auto-detects MIME type from extension.
    Images > 20MB are rejected.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/png")

    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > 20:
        raise ValueError(
            f"Image {path} is {size_mb:.1f}MB — exceeds OpenAI's 20MB limit. "
            f"Resize or compress it first."
        )

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")

    return f"data:{mime};base64,{data}", size_mb


def setup_key(key):
    """Validate and store an API key in settings.json.

    Validates first (no write on invalid). Idempotent — re-run to change key.
    Returns dict with keys: success (bool), message (str).
    """
    if not key or not key.strip():
        return {"success": False, "message": "Key must not be empty."}

    key = key.strip()
    if not key.startswith("sk-"):
        return {
            "success": False,
            "message": "Key doesn't look like an OpenAI key (should start with sk-...).",
        }

    # Validate before writing
    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {
                "success": False,
                "message": "Key rejected by OpenAI (401). Check for typos or a revoked key.",
            }
        return {"success": False, "message": f"Validation failed: HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"success": False, "message": f"Network error during validation: {e.reason}"}

    # Store in settings.json
    settings = _read_settings()
    env = settings.get("env", {})
    env["DEEPSEEK_VISION_API_KEY"] = key
    settings["env"] = env
    _write_settings(settings)

    return {
        "success": True,
        "message": f"API key stored in ~/.claude/settings.json. /vision and /generate are ready.",
    }


# ── System prompts (research-backed, mode-specific) ──────────────────────────

SYSTEM_CRITIQUE = """You are a senior web designer and UI reviewer with 15 years of experience.
You review web UI screenshots with precision and intellectual honesty.

## Process — always, in this order
1. INVENTORY FIRST, JUDGE SECOND. Before any opinion, list what you actually see: every major element (header, nav, cards, buttons, form fields, text blocks), its rough position (top-left, center, bottom), and visible text. Do not interpret yet. Reason over this list, not raw pixels.
2. DIAGNOSE: for each issue, state the problem, the likely cause, and the concrete fix. Name the element and its location every time.
3. PRIORITIZE: P0 = broken or usability-blocking, P1 = clearly wrong, P2 = polish.

## Evidence rule (non-negotiable)
Every claim must be grounded in something visible. Cite the element and location: "the card grid in the middle section", "the button in the top-right". If you cannot point to it, do not report it. If text is unreadable, write "unreadable" — never guess. Before finalizing, delete any issue you cannot directly see.

## Honesty about measurement
You cannot measure pixels, so never state absolute pixel values. Describe spacing in relative terms: "the gap between cards is roughly half the gap between the grid and the footer", "the form's left margin is about 2x the header's". Flag inconsistencies between related gaps — that is the real bug, not the absolute value.

## Review dimensions — check each
- Layout & structure: alignment, grid consistency, visual hierarchy, grouping
- Spacing: margin/padding rhythm, crowding, dead whitespace, inconsistency
- Typography: size/weight hierarchy, line length, legibility, font consistency
- Color & contrast: text/background contrast, color semantics, palette consistency
- States & feedback: missing hover/error/empty/loading states
- Responsiveness: how this likely breaks at narrow widths
- Accessibility: color-only signals, tiny tap targets, contrast issues

## Output format
Return Markdown with exactly these sections:

### Summary
2-3 sentences: what this screen is, overall quality, the single most important fix.

### Issues
One bullet per issue, sorted by priority:
- **[P0|P1|P2] <area> — <issue>** (<location>). <why it matters> → <fix>.

### What Works
A few strengths. Critique without being hostile.

### Actionable Fixes
Numbered, ordered by impact. Use specific CSS properties or DOM structure changes where applicable."""

SYSTEM_COMPARE = """You are a senior web designer comparing UI screenshots with precision.

Images are labeled: Image 1 = design/mockup (ground truth), Image 2+ = implementation(s).

## Process
1. INVENTORY: independently list what you see in each image — every major element and its position.
2. COMPARE: identify every divergence between the design and implementation. Do not manufacture differences where none exist.
3. PRIORITIZE: missing elements first, then major drift, then minor drift.

## Evidence rule (non-negotiable)
Every divergence must cite the element and its location in both images. "The button label in Image 1 reads 'Submit' (top-right), Image 2 reads 'Send' (same position)."

## Honesty about measurement
Never state absolute pixel values. Describe spacing in relative terms. Flag inconsistencies between related gaps.

## Output format

### Comparison Table
| # | Area | Design (Image 1) | Implementation (Image 2) | Verdict | Fix |
|---|------|-----------------|------------------------|---------|-----|
| 1 | ... | ... | ... | missing/major drift/minor drift/matches | ... |

Verdict: missing, major drift, minor drift, or matches.

### Summary
Total matches, minor drifts, major drifts, missing elements. Overall assessment.

### Fixes
Numbered, ordered by impact, copy-pasteable changes to make the implementation match the design."""

SYSTEM_REFERENCE = """You are a senior web designer comparing a reference design to a work under review.

Image 1 is the REFERENCE design. Image 2 is the work under review.

## Process
1. EXTRACT: from Image 1, extract the design system — spacing scale, grid structure, alignment rules, type hierarchy, color palette, component style — in relative terms.
2. EVALUATE: judge Image 2 against those extracted rules, NOT against your own taste.
3. FRAME: every finding as "the reference uses X here; the implementation uses Y" — this makes the divergence actionable.

## Evidence rule (non-negotiable)
Cite specific elements and locations. Never report a difference you cannot point to.

## Honesty about measurement
Use relative comparisons: "the reference's card padding is about 2x the implementation's."

## Output format

### Reference Design System
Bullet list of extracted rules from Image 1 (spacing scale, grid, alignment, type, color, components).

### Gaps
| # | Rule | Reference (Image 1) | Current (Image 2) | Severity | Fix |
|---|------|--------------------|-------------------|----------|-----|
| 1 | ... | ... | ... | P0/P1/P2 | ... |

### Summary
How closely Image 2 follows the reference. The 2-3 most impactful changes."""


def _pick_mode(image_paths, prompt):
    """Auto-detect the analysis mode from prompt and image count."""
    prompt_lower = prompt.lower()
    n = len(image_paths)

    # Explicit mode hints in prompt override
    compare_words = {"compare", "diff", "vs", "difference", "differences",
                     "between", "side by side", "side-by-side", "match"}
    reference_words = {"reference", "match this", "make it like", "should be",
                       "supposed to", "attached design", "like this"}

    if n >= 2:
        if any(w in prompt_lower for w in reference_words):
            return "reference"
        if any(w in prompt_lower for w in compare_words):
            return "compare"
        # Multiple images with no clear mode: default to compare
        return "compare"

    return "critique"


def vision(image_paths, prompt, mode="auto", model="gpt-4o",
           max_tokens=3000, detail="high"):
    """Send images to GPT-4o for analysis with mode-specific system prompts.

    Args:
        image_paths: list of image file paths (1-10 images)
        prompt: text question/instruction about the images
        mode: 'critique', 'compare', 'reference', or 'auto' (default 'auto')
        model: OpenAI model (default gpt-4o)
        max_tokens: max response tokens (default 3000 for design analysis)
        detail: 'low', 'high', or 'auto' (default 'high' for design work)

    Returns:
        dict with keys: text (str), model (str), usage (dict), elapsed_s (float),
                        mode (str), image_count (int)
    """
    api_key, source = _load_api_key()
    if not api_key:
        return {
            "error": "no_api_key",
            "message": (
                "No OpenAI API key found. Set it up:\n"
                "  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure.py --interactive\n"
                "Or: export DEEPSEEK_VISION_API_KEY=sk-..."
            ),
        }

    if not image_paths:
        return {"error": "no_images", "message": "No image paths provided."}

    if len(image_paths) > 10:
        return {
            "error": "too_many_images",
            "message": f"Maximum 10 images per request, got {len(image_paths)}.",
        }

    # Resolve mode
    if mode == "auto":
        mode = _pick_mode(image_paths, prompt)

    system_prompts = {
        "critique": SYSTEM_CRITIQUE,
        "compare": SYSTEM_COMPARE,
        "reference": SYSTEM_REFERENCE,
    }
    system_msg = system_prompts.get(mode, SYSTEM_CRITIQUE)

    # Build messages: system + user (with images labeled)
    messages = [{"role": "system", "content": system_msg}]

    # Label images for multi-image modes
    if len(image_paths) > 1:
        labeled_prompt = f"Images: "
        for i, p in enumerate(image_paths, 1):
            labeled_prompt += f"Image {i} = {os.path.basename(p)}, "
        labeled_prompt = labeled_prompt.rstrip(", ") + f"\n\nQuestion: {prompt}"
    else:
        labeled_prompt = prompt

    content = [{"type": "text", "text": labeled_prompt}]

    total_mb = 0
    for path in image_paths:
        try:
            data_url, size_mb = _image_to_data_url(path)
            total_mb += size_mb
            content.append({
                "type": "image_url",
                "image_url": {"url": data_url, "detail": detail},
            })
        except (FileNotFoundError, ValueError) as e:
            return {"error": "image_load_error", "message": str(e)}

    messages.append({"role": "user", "content": content})

    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    data = json.dumps(body).encode("utf-8")
    url = "https://api.openai.com/v1/chat/completions"

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(error_body)
            msg = error_data.get("error", {}).get("message", error_body)
        except json.JSONDecodeError:
            msg = error_body
        return {
            "error": f"http_{e.code}",
            "message": f"OpenAI API error ({e.code}): {msg}",
        }
    except urllib.error.URLError as e:
        return {
            "error": "network_error",
            "message": f"Network error reaching OpenAI API: {e.reason}",
        }
    elapsed = time.time() - t0

    choice = result.get("choices", [{}])[0]
    text = choice.get("message", {}).get("content", "")

    return {
        "text": text,
        "model": result.get("model", model),
        "usage": result.get("usage", {}),
        "elapsed_s": round(elapsed, 2),
        "mode": mode,
        "image_count": len(image_paths),
    }


def generate(prompt, size="1024x1024", quality="standard", model="gpt-image-1"):
    """Generate an image via OpenAI's image generation API.

    Args:
        prompt: image description
        size: '1024x1024', '1024x1536', or '1536x1024'
        quality: 'low', 'medium', 'high' (model-dependent)
        model: 'gpt-image-1', 'gpt-image-1-mini', 'gpt-image-2', or 'dall-e-3'

    Returns:
        dict with keys: b64_json (str), error (str or None)
    """
    if not prompt or not prompt.strip():
        return {"error": "empty_prompt", "message": "Prompt must not be empty."}

    api_key, source = _load_api_key()
    if not api_key:
        return {
            "error": "no_api_key",
            "message": (
                "No OpenAI API key found. Set it up:\n"
                "  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure.py --interactive\n"
                "Or: export DEEPSEEK_VISION_API_KEY=sk-..."
            ),
        }

    valid_sizes = {"1024x1024", "1024x1536", "1536x1024", "auto"}
    if size not in valid_sizes:
        return {"error": "invalid_size", "message": f"Size must be one of {sorted(valid_sizes)}"}

    body = {
        "model": model,
        "prompt": prompt.strip(),
        "n": 1,
        "size": size,
    }
    if quality != "standard":
        body["quality"] = quality

    data = json.dumps(body).encode("utf-8")
    url = "https://api.openai.com/v1/images/generations"

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(error_body)
            msg = error_data.get("error", {}).get("message", error_body)
        except json.JSONDecodeError:
            msg = error_body
        return {"error": f"http_{e.code}", "message": f"OpenAI API error ({e.code}): {msg}"}
    except urllib.error.URLError as e:
        return {"error": "network_error", "message": f"Network error: {e.reason}"}

    image_data = result.get("data", [{}])[0]
    # gpt-image-* models return b64_json; dall-e-3 returns url
    return {
        "b64_json": image_data.get("b64_json"),
        "url": image_data.get("url"),
        "error": None,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli_check():
    result = check()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["valid"] else 1)


def _cli_setup():
    import argparse
    parser = argparse.ArgumentParser(description="Store API key")
    parser.add_argument("key", help="OpenAI API key (sk-...)")
    args = parser.parse_args()
    result = setup_key(args.key)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["success"] else 1)


def _cli_vision():
    import argparse
    parser = argparse.ArgumentParser(description="GPT-4o vision analysis")
    parser.add_argument("images", nargs="+", help="Image file paths")
    parser.add_argument("--prompt", "-p", required=True, help="Analysis prompt/question")
    parser.add_argument("--mode", default="auto",
                        choices=["auto", "critique", "compare", "reference"])
    parser.add_argument("--detail", default="high", choices=["low", "high", "auto"])
    parser.add_argument("--max-tokens", type=int, default=3000)
    args = parser.parse_args()

    result = vision(args.images, args.prompt, mode=args.mode,
                    detail=args.detail, max_tokens=args.max_tokens)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if "error" not in result else 1)


def _cli_generate():
    import argparse
    parser = argparse.ArgumentParser(description="OpenAI image generation")
    parser.add_argument("prompt", help="Image description")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default="standard")
    parser.add_argument("--model", default="gpt-image-1")
    parser.add_argument("--output", "-o", help="File path to save the image (required)")
    args = parser.parse_args()

    result = generate(args.prompt, size=args.size, quality=args.quality,
                      model=args.model)
    print(json.dumps({k: v for k, v in result.items() if k not in ("b64_json",)},
                     indent=2, ensure_ascii=False))

    if result.get("error"):
        sys.exit(1)

    # Save image from base64 or URL
    output = args.output
    if not output:
        output = f"generated-{time.strftime('%Y%m%d-%H%M%S')}.png"

    try:
        b64 = result.get("b64_json")
        if b64:
            img_data = base64.b64decode(b64)
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            with open(output, "wb") as f:
                f.write(img_data)
            print(f"\nImage saved to: {output} ({len(img_data) / 1024:.0f} KB)")
        elif result.get("url"):
            req = urllib.request.Request(result["url"])
            with urllib.request.urlopen(req, timeout=60) as resp:
                img_data = resp.read()
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            with open(output, "wb") as f:
                f.write(img_data)
            print(f"\nImage saved to: {output} ({len(img_data) / 1024:.0f} KB)")
        else:
            print("\nNo image data returned.")
            sys.exit(1)
    except Exception as e:
        print(f"\nFailed to save image: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenAI API utilities")
    parser.add_argument("action", choices=["check", "setup", "vision", "generate"],
                        nargs="?")
    args, unknown = parser.parse_known_args()

    if args.action == "check":
        sys.argv = [sys.argv[0]] + unknown
        _cli_check()
    elif args.action == "setup":
        sys.argv = [sys.argv[0]] + unknown
        _cli_setup()
    elif args.action == "vision":
        sys.argv = [sys.argv[0]] + unknown
        _cli_vision()
    elif args.action == "generate":
        sys.argv = [sys.argv[0]] + unknown
        _cli_generate()
    else:
        parser.print_help()
