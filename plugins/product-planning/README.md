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

```
/product-planning user-authentication
```

Or just ask Claude to plan a feature — the skill description triggers automatically.

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
