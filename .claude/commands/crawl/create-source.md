---
description: Create a new documentation source for the crawl toolkit
---

# Create New Documentation Source

You are creating a new documentation source for the web crawling toolkit. This will set up all the necessary files for crawling a documentation website.

## Steps to follow

### 1. Gather Information

Use `AskUserQuestion` to collect the following information from the user:

**Required information:**
- **Source Name**: A descriptive name for the documentation (e.g., "MDN Web Animations API", "React Documentation")
- **Source ID**: A slug for the directory name (e.g., "mdn-web-animations-api", "react-docs")
- **Base URL**: The root URL of the documentation site (e.g., "https://developer.mozilla.org")
- **Language**: The language code (default: "en-US")
- **Seed URLs**: One or more starting URLs to crawl (relative to base URL, e.g., "/docs/Web/API/Animation")
- **Include Patterns**: Regex patterns to match URLs to include (e.g., "/docs/Web/API/Animation($|/)")

**Optional configuration:**
- **Max Concurrent**: Number of concurrent crawl workers (default: 5)
- **Page Timeout**: Timeout in ms for each page (default: 30000)
- **Excluded Tags**: HTML tags to exclude from content (default: nav, footer, aside, header, script, style)
- **Title Suffix Pattern**: Regex to remove from page titles (e.g., "\\s*[-|].*Site Name.*$")
- **Custom Cleaner**: Whether to create a custom cleaner module (default: yes for MDN-like sites)

### 2. Create Source Directory Structure

Create the directory `sources/{source_id}/` with the following files:

#### config.yaml

```yaml
name: "{source_name}"
base_url: "{base_url}"
language: "{language}"

seed_urls:
  - "{seed_url_1}"
  - "{seed_url_2}"

include_patterns:
  - "{pattern_1}"
  - "{pattern_2}"

crawler:
  max_concurrent: {max_concurrent}
  page_timeout: {page_timeout}
  excluded_tags:
    - nav
    - footer
    - aside
    - header
    - script
    - style

output:
  structure: "hierarchical"
  frontmatter: true
  title_suffix_pattern: "{title_suffix_pattern}"

cleaner:
  module: "cleaner"
```

#### cleaner.py

Create a cleaner class that extends `CleanerBase`:

```python
"""
{source_name} markdown cleaner.

Handles source-specific content patterns and formatting.
"""

import re
from crawl4ai_toolkit.cleaner import CleanerBase


class {SourceClassName}Cleaner(CleanerBase):
    """
    Cleaner for {source_name} documentation content.

    Customize the clean() method to handle source-specific elements.
    """

    def clean(self, content: str, title: str = "") -> str:
        """Apply source-specific cleaning."""
        # Apply base cleaning first
        content = super().clean(content, title)

        # Add your source-specific cleaning here
        # Example: content = self.remove_sidebar(content)
        # Example: content = self.remove_footer(content)

        # Remove duplicated H1 heading (already in frontmatter)
        content = self.remove_first_h1(content)

        return content

    # Add custom cleaning methods below
    # def remove_sidebar(self, content: str) -> str:
    #     """Remove sidebar navigation."""
    #     pass
```

#### url_mappings.py (optional)

If the user wants explicit URL-to-filepath mappings:

```python
"""
URL to file path mappings for {source_name}.

Maps URLs to organized file paths for the output structure.
"""

import re
from urllib.parse import urlparse


# Known pages with explicit mappings
# Format: "output/file/path": "/url/path"
KNOWN_PAGES = {
    # Add mappings here
    # "main_page": "/docs/main",
}

# Reverse mapping for URL to file path lookup
_URL_TO_FILEPATH = {v: k for k, v in KNOWN_PAGES.items()}


def get_file_path_from_url(url: str) -> str:
    """
    Map a URL to its output file path.

    Args:
        url: Full URL

    Returns:
        Relative file path (without .md extension)
    """
    parsed = urlparse(url)
    path = parsed.path

    # Remove language prefix if present
    path = re.sub(r'^/[a-z]{2}(-[A-Z]{2})?/', '/', path)

    # Check explicit mappings first
    if path in _URL_TO_FILEPATH:
        return _URL_TO_FILEPATH[path]

    # Fallback: derive from URL path
    # Customize this logic for your source
    return path.strip('/')


def build_urls(base_url: str, language: str = "en-US") -> dict:
    """
    Build full URLs for all known pages.

    Args:
        base_url: Base URL
        language: Language code

    Returns:
        Dict mapping file path to full URL
    """
    urls = {}
    for file_path, url_path in KNOWN_PAGES.items():
        full_url = f"{base_url}/{language}{url_path}"
        urls[file_path] = full_url
    return urls
```

### 3. Validate the Source

After creating the files:
1. Show the user the created files
2. Suggest running a discovery test: `.venv/bin/python3 crawl.py {source_id} --discover-only`
3. Explain how to run a full crawl: `.venv/bin/python3 crawl.py {source_id}`

### 4. Important Notes for the User

- The `include_patterns` should be regex patterns that match URLs you want to crawl
- Use `($|/)` at the end of patterns to match both the exact URL and subpages
- The cleaner module is optional but recommended for cleaning up source-specific content
- Run `--discover-only` first to verify URL discovery before a full crawl
- Check the output in `sources/{source_id}/output/` after crawling
