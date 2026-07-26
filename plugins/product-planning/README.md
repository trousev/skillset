# Product Planning

Interactive 4-step feature planning interview for Claude Code.

## What it does

Launches a structured interview where Claude acts as your product manager and tech lead combined. Through 4 steps, it produces a comprehensive feature spec:

1. **Product Questions** — What, Why, Who
2. **Technical Implementation** — High-level architecture
3. **Implementation Details** — Low-level specifics
4. **Attack & Challenge** — Critical risk analysis

The output lands in `./specs/FEATURE-<name>.md`.

## Usage

### Interactive Mode (default)
```
/product-planning user-authentication
```

Claude interviews you one question at a time. You answer, and the spec builds up gradually.

### Auto Mode (`--auto`)
```
/product-planning --auto user-authentication
```

Claude plays both interviewer and interviewee — but instead of answering its own questions, it spawns **independent sub-agents** to play the developer/stakeholder role. Each question fires a fresh agent that researches the codebase and answers from its own perspective. This creates a genuine two-party dialogue, not a monologue. Ideal for:
- Another AI agent invoking this skill
- Rapid prototyping and brainstorming
- Generating an initial spec to refine later

Auto mode is the same thorough 4-step process — just self-driven.

## Install

```bash
claude plugins install trousev/skillset
```

Or add to your marketplace:

```bash
claude marketplace add trousev/skillset
```

Then install the plugin:

```bash
claude plugins install product-planning
```

## License

MIT
