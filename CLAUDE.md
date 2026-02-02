# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a documentation crawling toolkit that converts web documentation (like MDN) into organized markdown files. It uses Crawl4AI for web scraping and provides a modular architecture for crawling different documentation sources.

## Commands

### Run a crawl
```bash
.venv/bin/python3 crawl.py <source-name>                    # Full crawl
.venv/bin/python3 crawl.py <source-name> --discover-only    # List URLs only (no crawl)
.venv/bin/python3 crawl.py <source-name> --skip-discovery   # Use known URLs only
.venv/bin/python3 crawl.py <source-name> --language fr      # Different language
.venv/bin/python3 crawl.py <source-name> -c 10              # Custom concurrency
```

### Check for changes
```bash
.venv/bin/python3 crawl.py <source-name> --check            # Check local files for modifications
.venv/bin/python3 crawl.py <source-name> --check-remote     # Re-crawl and check for remote changes
```

### List available sources
```bash
.venv/bin/python3 crawl.py --list
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

**crawl4ai_toolkit/** - Reusable library with four modules:
- `crawler.py` - URL discovery (`discover_urls`) and page crawling (`crawl_pages`) using Crawl4AI's `AsyncWebCrawler`
- `generator.py` - Markdown file generation with frontmatter and index creation
- `cleaner.py` - Base `CleanerBase` class for markdown content cleaning
- `state.py` - `CrawlState` class for tracking crawl history and detecting changes via content hashes or HTTP headers

### Adding a New Documentation Source

Create a directory under `sources/` with:

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
  module: "cleaner"  # Optional: custom cleaner module
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

3. **url_mappings.py** (optional) - URL normalization and file path mapping:
   - `normalize_mdn_url(url, language)` - Normalize URL format
   - `get_file_path_from_url(url)` - Map URL to output file path
   - `build_urls(base_url, language)` - Build dict of known URLs

### Change Detection

The toolkit uses a multi-level strategy for detecting content changes:
1. HTTP headers (ETag/Last-Modified) - fast, requires HEAD request only
2. Content hash (SHA256) - reliable fallback, requires full crawl

State is stored in `sources/<name>/.crawl-state.json` and includes content hashes for each page.

## Dependencies

- `crawl4ai>=0.7.4` - Web crawling with browser automation
- `pyyaml` - Configuration parsing
- `aiohttp` - HTTP headers checking
