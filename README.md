# crawl-web

A modular toolkit for crawling web documentation and converting it to organized markdown files. Built with [Crawl4AI](https://github.com/unclecode/crawl4ai) for robust web scraping with browser automation.

## Features

- **Modular architecture** - Add new documentation sources via simple YAML config
- **Smart URL discovery** - Automatically find pages from seed URLs with pattern matching
- **Custom cleaners** - Source-specific markdown post-processing
- **Change detection** - Track updates via content hashing or HTTP headers
- **Claude Code integration** - Skills and commands for AI-assisted crawling

## Installation

```bash
# Clone the repository
git clone https://github.com/sebc-dev/crawl-web.git
cd crawl-web

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (required by Crawl4AI)
playwright install chromium
```

## Usage

### Run a crawl

```bash
# Full crawl
python crawl.py <source-name>

# List URLs only (no crawl)
python crawl.py <source-name> --discover-only

# Use known URLs only (skip discovery)
python crawl.py <source-name> --skip-discovery

# Different language
python crawl.py <source-name> --language fr

# Custom concurrency
python crawl.py <source-name> -c 10
```

### Check for changes

```bash
# Check local files for modifications
python crawl.py <source-name> --check

# Re-crawl and check for remote changes
python crawl.py <source-name> --check-remote
```

### List available sources

```bash
python crawl.py --list
```

## Adding a New Source

Create a directory under `sources/` with:

### 1. config.yaml (required)

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
  module: "cleaner"  # Optional: custom cleaner module
```

### 2. cleaner.py (optional)

Custom markdown cleaner for source-specific post-processing:

```python
from crawl4ai_toolkit.cleaner import CleanerBase

class MyCleaner(CleanerBase):
    def clean(self, content: str, title: str = "") -> str:
        content = super().clean(content, title)
        # Add source-specific cleaning
        return content
```

## Architecture

```
crawl-web/
├── crawl.py                 # CLI entry point
├── crawl4ai_toolkit/        # Reusable library
│   ├── crawler.py           # URL discovery and page crawling
│   ├── generator.py         # Markdown file generation
│   ├── cleaner.py           # Base cleaner class
│   ├── state.py             # Crawl state and change detection
│   └── link_transformer.py  # Link processing utilities
├── sources/                 # Documentation sources
│   └── <source-name>/
│       ├── config.yaml      # Source configuration
│       ├── cleaner.py       # Optional custom cleaner
│       └── output/          # Generated markdown files
└── .claude/                 # Claude Code integration
    ├── skills/crawl4ai/     # Crawl4AI skill with examples
    ├── commands/crawl/      # Crawl commands
    └── agents/              # Specialized agents
```

## Dependencies

- `crawl4ai>=0.7.4` - Web crawling with browser automation
- `pyyaml` - Configuration parsing
- `aiohttp` - HTTP headers checking

## License

MIT
