"""
Markdown file generation utilities.

Handles generating organized markdown files from crawl results,
including frontmatter and index generation.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any

from .cleaner import CleanerBase
from .state import CrawlState, compute_content_hash
from .link_transformer import transform_links


def generate_markdown_files(
    results: Dict[str, dict],
    output_dir: Path,
    url_to_filepath: Callable[[str], str],
    cleaner: Optional[CleanerBase] = None,
    frontmatter: bool = True,
    title_cleaner: Optional[Callable[[str], str]] = None,
    crawl_state: Optional[CrawlState] = None,
    base_url: Optional[str] = None,
    transform_internal_links: bool = True,
) -> tuple[int, dict]:
    """
    Generate organized markdown files from crawl results.

    Args:
        results: Dict mapping URL to crawl result data
        output_dir: Directory to write files to
        url_to_filepath: Function mapping URL to relative file path (without .md)
        cleaner: Optional cleaner instance for content processing
        frontmatter: Whether to include YAML frontmatter
        title_cleaner: Optional function to clean page titles
        crawl_state: Optional CrawlState instance for tracking changes
        base_url: Base URL for link transformation (required if transform_internal_links=True)
        transform_internal_links: Whether to transform internal links to relative paths

    Returns:
        Tuple of (files_written, index_entries)
        where index_entries is a dict for building the index
    """
    print(f"\nPhase 3: Generating markdown files in {output_dir}...")

    output_dir.mkdir(parents=True, exist_ok=True)

    if cleaner is None:
        cleaner = CleanerBase()

    files_written = 0
    index_entries: Dict[str, List[tuple]] = {}

    for url, result in results.items():
        # Get file path from URL
        file_path = url_to_filepath(url)
        if not file_path:
            print(f"  SKIP (no mapping): {url}")
            continue

        # Extract content
        markdown_content = result.get('markdown', '')
        title = result.get('title', '') or file_path.split('/')[-1]

        # Clean title if function provided
        if title_cleaner:
            title = title_cleaner(title)

        # Clean content
        markdown_content = cleaner.clean(markdown_content, title)

        # Transform internal links to relative paths
        if transform_internal_links and base_url:
            crawled_urls = set(results.keys())
            markdown_content = transform_links(
                content=markdown_content,
                current_file_path=file_path,
                base_url=base_url,
                crawled_urls=crawled_urls,
                url_to_filepath=url_to_filepath,
            )

        # Compute content hash for change detection
        content_hash = compute_content_hash(f"# {title}\n\n{markdown_content}")

        # Build file content
        if frontmatter:
            content = f"""---
title: "{title}"
url: "{url}"
crawled_at: "{datetime.now().isoformat()}"
content_hash: "{content_hash}"
---

# {title}

{markdown_content}
"""
        else:
            content = f"# {title}\n\n{markdown_content}"

        # Determine output path
        out_path = output_dir / f"{file_path}.md"

        # Create parent directories
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        out_path.write_text(content, encoding='utf-8')
        files_written += 1
        print(f"  Written: {out_path.relative_to(output_dir)}")

        # Update crawl state if provided
        if crawl_state:
            crawl_state.set_page(
                file_path=file_path,
                url=url,
                content_hash=content_hash,
                title=title,
                etag=result.get('etag'),
                last_modified=result.get('last_modified'),
            )

        # Track for index
        category = _get_category(file_path)
        if category not in index_entries:
            index_entries[category] = []
        index_entries[category].append((title, f"{file_path}.md", url))

    print(f"  Total files written: {files_written}")
    return files_written, index_entries


def _get_category(file_path: str) -> str:
    """Extract category from file path for index organization."""
    parts = file_path.split('/')
    if len(parts) >= 2:
        return parts[0]
    return "main"


def generate_index(
    output_dir: Path,
    entries: Dict[str, List[tuple]],
    title: str = "Documentation Index",
    description: str = "",
    category_order: Optional[List[str]] = None,
    category_titles: Optional[Dict[str, str]] = None,
) -> None:
    """
    Generate index.md with table of contents.

    Args:
        output_dir: Directory to write index to
        entries: Dict mapping category to list of (title, path, url) tuples
        title: Index page title
        description: Optional description text
        category_order: Optional list defining category display order
        category_titles: Optional dict mapping category keys to display titles
    """
    if category_titles is None:
        category_titles = {}

    content = f"""---
title: "{title}"
generated_at: "{datetime.now().isoformat()}"
---

# {title}

{description}

## Table of Contents

"""

    # Determine category order
    if category_order:
        categories = [c for c in category_order if c in entries]
        # Add any remaining categories
        categories.extend(c for c in sorted(entries.keys()) if c not in categories)
    else:
        categories = sorted(entries.keys())

    for category in categories:
        if category not in entries:
            continue

        pages = entries[category]
        display_title = category_titles.get(category, category.replace('_', ' ').title())

        content += f"### {display_title}\n\n"

        for page_title, path, _ in sorted(pages, key=lambda x: x[0]):
            content += f"- [{page_title}]({path})\n"

        content += "\n"

    (output_dir / "index.md").write_text(content, encoding='utf-8')
    print(f"  Written: index.md")
