# Skillset Marketplace

A curated marketplace of Claude Code plugins and skills.

## Quick Install

```bash
# Add this marketplace
claude marketplace add trousev/skillset

# Install a plugin
claude plugins install product-planning
```

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [product-planning](plugins/product-planning/) | Interactive 4-step feature planning interview that produces comprehensive specs |

## For Contributors

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on writing and submitting skills.

### Validation

```bash
# Validate a plugin
python3 evals/runner/validate.py plugins/product-planning

# Validate everything
python3 evals/runner/validate.py --all
```

## License

MIT
