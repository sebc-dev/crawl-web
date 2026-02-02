# crawl-web

A documentation crawling toolkit designed for use with [Claude Code](https://claude.ai/code). Converts web documentation into organized markdown files through AI-assisted workflows.

## Features

- **AI-assisted crawling** - Slash commands and specialized agents guide you through each step
- **Smart URL discovery** - Automatically categorize documentation pages by type
- **Custom cleaners** - Source-specific markdown post-processing with AI-generated rules
- **Change detection** - Track updates via content hashing or HTTP headers

## Installation

```bash
git clone https://github.com/sebc-dev/crawl-web.git
cd crawl-web

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage with Claude Code

This toolkit is designed to be used through Claude Code slash commands. Open the project in Claude Code and use the following commands:

### `/crawl:analyze-urls` - Discover what to crawl

Analyzes a documentation URL to find all available pages and categorize them.

```
You: /crawl:analyze-urls

Claude: What documentation URL would you like to analyze?
You: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API

Claude: What level of coverage do you need?
  - Single page only
  - Section (one level deep)
  - Full documentation (recursive)

Claude: [Launches url-analyzer agent]

Claude: Found 18 pages organized in 4 categories:
  - Overview (2 pages)
  - API Reference (12 pages)
  - Guides (3 pages)
  - Examples (1 page)
```

The `url-analyzer` agent crawls the target URL, extracts links, and categorizes pages based on content analysis.

### `/crawl:create-source` - Set up a new documentation source

Creates the configuration files needed to crawl a documentation site.

```
You: /crawl:create-source

Claude: What's the name of this documentation?
You: Fetch API

Claude: What's the source ID (for directory name)?
You: mdn-fetch-api

Claude: What's the base URL?
You: https://developer.mozilla.org

Claude: [Creates sources/mdn-fetch-api/ with config.yaml and cleaner.py]
```

This creates:
- `sources/<id>/config.yaml` - Crawl configuration (URLs, patterns, settings)
- `sources/<id>/cleaner.py` - Markdown post-processor (customizable)

### `/crawl:run` - Execute a crawl

Runs the crawler for a configured source.

```
You: /crawl:run

Claude: Which source do you want to crawl?
  - mdn-fetch-api
  - mdn-web-animations-api

Claude: What mode?
  - Full crawl (discover + crawl all)
  - Discover only (list URLs)
  - Skip discovery (use known URLs)
  - Check local (detect local modifications)
  - Check remote (detect upstream changes)

Claude: [Executes crawl, shows progress]

Claude: Crawled 18 pages successfully.
        Output: sources/mdn-fetch-api/output/
```

### `/crawl:clean-docs` - Improve output quality

Analyzes crawled files and implements cleaning rules to remove noise.

```
You: /crawl:clean-docs

Claude: Which source do you want to clean?
You: mdn-fetch-api

Claude: [Launches cleaning-analyzer agent]

Claude: Found these issues in the crawled files:
  - High Priority: "See also" sections (18 files)
  - High Priority: Browser compatibility tables (15 files)
  - Medium Priority: Breadcrumb navigation (12 files)

Claude: Which issues should I address?
You: All high priority issues

Claude: [Launches cleaning-implementer agent]

Claude: Updated sources/mdn-fetch-api/cleaner.py with:
  - remove_see_also()
  - remove_browser_compatibility()

Run /crawl:run to apply changes.
```

The workflow uses two specialized agents:
- `cleaning-analyzer` - Scans files to detect noise patterns
- `cleaning-implementer` - Writes Python cleaning methods

### `/crawl:check-updates` - Monitor for changes

Checks if crawled documentation needs to be refreshed.

```
You: /crawl:check-updates

Claude: Which source to check?
You: mdn-fetch-api

Claude: What type of check?
  - Local (detect manual edits to output files)
  - Remote (re-crawl and compare with upstream)

Claude: [Runs check]

Claude: Remote Status:
  ✓ 15 pages unchanged
  ⚠ 2 pages changed
  + 1 new page

Recommendation: Run /crawl:run to update
```

## Agents

The toolkit includes specialized agents that handle complex tasks autonomously:

| Agent | Purpose |
|-------|---------|
| `url-analyzer` | Crawls documentation URLs and categorizes pages by type (API reference, guides, examples) |
| `cleaning-analyzer` | Analyzes markdown files to identify noise patterns and formatting issues |
| `cleaning-implementer` | Implements Python cleaning methods based on analysis reports |

Agents are invoked automatically by the slash commands, but can also be triggered directly through Claude Code's agent system.

## Project Structure

```
crawl-web/
├── crawl.py                 # CLI entry point (used by commands)
├── crawl4ai_toolkit/        # Core library
│   ├── crawler.py           # URL discovery and page crawling
│   ├── generator.py         # Markdown file generation
│   ├── cleaner.py           # Base cleaner class
│   └── state.py             # Change detection
├── sources/                 # Documentation sources
│   └── <source-id>/
│       ├── config.yaml      # Source configuration
│       ├── cleaner.py       # Custom cleaner
│       └── output/          # Generated markdown
└── .claude/
    ├── commands/crawl/      # Slash commands
    └── agents/              # Specialized agents
```

## Direct CLI Usage

The commands can also be run directly if needed:

```bash
# List sources
.venv/bin/python3 crawl.py --list

# Full crawl
.venv/bin/python3 crawl.py <source-id>

# Discover URLs only
.venv/bin/python3 crawl.py <source-id> --discover-only

# Check for changes
.venv/bin/python3 crawl.py <source-id> --check-remote
```

## Dependencies

- `crawl4ai>=0.7.4` - Web crawling with browser automation
- `pyyaml` - Configuration parsing
- `aiohttp` - HTTP headers checking

## License

MIT
