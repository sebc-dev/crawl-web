# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a documentation crawling toolkit designed for use with Claude Code. It converts web documentation (like MDN) into organized markdown files using Crawl4AI and provides slash commands and specialized agents for AI-assisted workflows.

## Slash Commands

Use these commands to interact with the toolkit:

| Command | Description |
|---------|-------------|
| `/crawl:analyze-urls` | Analyze a documentation URL to discover and categorize pages |
| `/crawl:create-source` | Create a new documentation source with config and cleaner |
| `/crawl:run` | Run a crawl for a configured source |
| `/crawl:clean-docs` | Analyze and clean crawled documentation quality |
| `/crawl:check-updates` | Check if documentation sources need updates |

## Agents

Specialized agents are invoked by the commands:

| Agent | Purpose |
|-------|---------|
| `url-analyzer` | Crawls URLs and categorizes pages (API reference, guides, examples) |
| `cleaning-analyzer` | Identifies noise patterns in crawled markdown files |
| `cleaning-implementer` | Implements Python cleaning methods from analysis reports |

## Direct CLI Commands

For debugging or direct usage:

```bash
# List available sources
.venv/bin/python3 crawl.py --list

# Full crawl
.venv/bin/python3 crawl.py <source-name>

# Discover URLs only (no crawl)
.venv/bin/python3 crawl.py <source-name> --discover-only

# Use known URLs only (skip discovery)
.venv/bin/python3 crawl.py <source-name> --skip-discovery

# Different language
.venv/bin/python3 crawl.py <source-name> --language fr

# Custom concurrency
.venv/bin/python3 crawl.py <source-name> -c 10

# Check local files for modifications
.venv/bin/python3 crawl.py <source-name> --check

# Re-crawl and check for remote changes
.venv/bin/python3 crawl.py <source-name> --check-remote
```

### Run tests (for the crawl4ai skill)
```bash
.venv/bin/python3 .claude/skills/crawl4ai/tests/run_all_tests.py
```

## Architecture

### Core Components

**crawl.py** - CLI entry point that orchestrates the crawl pipeline:
1. Loads source configuration from `sources/<name>/config.yaml`
2. Discovers URLs from seed pages
3. Crawls all discovered pages
4. Generates markdown files with frontmatter
5. Saves crawl state for change detection

**crawl4ai_toolkit/** - Reusable library:
- `crawler.py` - URL discovery (`discover_urls`) and page crawling (`crawl_pages`)
- `generator.py` - Markdown file generation with frontmatter and index creation
- `cleaner.py` - Base `CleanerBase` class for markdown content cleaning
- `state.py` - `CrawlState` class for tracking crawl history and detecting changes

### Adding a New Documentation Source

Use `/crawl:create-source` or manually create a directory under `sources/` with:

1. **config.yaml** - Required configuration:
```yaml
name: "Source Name"
base_url: "https://example.com"
language: "en-US"
seed_urls:
  - "/docs/page1"
  - "/docs/page2"
include_patterns:
  - "/docs/relevant-section($|/)"
crawler:
  max_concurrent: 5
  page_timeout: 30000
  excluded_tags: [nav, footer, aside]
output:
  structure: "hierarchical"
  frontmatter: true
cleaner:
  module: "cleaner"
```

2. **cleaner.py** (optional) - Custom markdown cleaner extending `CleanerBase`:
```python
from crawl4ai_toolkit.cleaner import CleanerBase

class MyCleaner(CleanerBase):
    def clean(self, content: str, title: str = "") -> str:
        content = super().clean(content, title)
        # Add source-specific cleaning
        return content
```

### Change Detection

The toolkit uses a multi-level strategy for detecting content changes:
1. HTTP headers (ETag/Last-Modified) - fast, requires HEAD request only
2. Content hash (SHA256) - reliable fallback, requires full crawl

State is stored in `sources/<name>/.crawl-state.json`.

## Dependencies

- `crawl4ai>=0.7.4` - Web crawling with browser automation
- `pyyaml` - Configuration parsing
- `aiohttp` - HTTP headers checking
