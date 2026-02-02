---
description: Run a crawl for a documentation source
---

# Run Documentation Crawl

You are launching a crawl for a documentation source.

## Steps to follow

### 1. List Available Sources

First, run the following command to see available sources:

```bash
.venv/bin/python3 crawl.py --list
```

### 2. Get User Input

Use `AskUserQuestion` to ask the user:

**Question 1: Source Selection**
- Ask which source they want to crawl
- List the available sources from the previous command as options

**Question 2: Crawl Mode**
- Options:
  - **Full crawl** (default) - Discover URLs and crawl all pages
  - **Discover only** - List URLs without crawling (useful for testing patterns)
  - **Skip discovery** - Use only known URLs from url_mappings.py
  - **Check local** - Check if local files have been modified
  - **Check remote** - Re-crawl and check for remote changes

**Question 3: Additional Options** (optional, only ask if relevant)
- **Language** - Language code if different from default (e.g., "fr", "de", "ja")
- **Concurrency** - Number of concurrent workers (default from config)

### 3. Build and Run Command

Based on the user's choices, build the appropriate command:

```bash
# Full crawl (default)
.venv/bin/python3 crawl.py <source-name>

# Discover only
.venv/bin/python3 crawl.py <source-name> --discover-only

# Skip discovery
.venv/bin/python3 crawl.py <source-name> --skip-discovery

# Check local changes
.venv/bin/python3 crawl.py <source-name> --check

# Check remote changes
.venv/bin/python3 crawl.py <source-name> --check-remote

# With language
.venv/bin/python3 crawl.py <source-name> --language <lang-code>

# With custom concurrency
.venv/bin/python3 crawl.py <source-name> -c <number>
```

### 4. Execute the Crawl

Run the command using Bash and show the output to the user.

### 5. Post-Crawl Summary

After the crawl completes:
- Report the number of pages crawled
- Show the output directory location: `sources/<source-name>/output/`
- If errors occurred, summarize them
- Suggest next steps (e.g., run `/crawl:clean-docs` to improve quality)
