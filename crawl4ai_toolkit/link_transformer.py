"""
Link transformation utilities for converting web URLs to relative markdown paths.

Handles transforming internal documentation links to relative file paths
while preserving external links and handling edge cases like anchors.
"""

import re
from urllib.parse import urlparse, urljoin
from typing import Callable, Set, Optional


def compute_relative_path(from_path: str, to_path: str) -> str:
    """
    Compute the relative path from one file to another.

    Args:
        from_path: The source file path (without .md extension)
        to_path: The target file path (without .md extension)

    Returns:
        Relative path from source to target (with .md extension)

    Example:
        compute_relative_path("en-US/docs/Web/API/Animation", "en-US/docs/Web/API/Element")
        => "../Element.md"
    """
    from_parts = from_path.split('/')
    to_parts = to_path.split('/')

    # Find common prefix
    common_length = 0
    for i in range(min(len(from_parts) - 1, len(to_parts) - 1)):
        if from_parts[i] == to_parts[i]:
            common_length = i + 1
        else:
            break

    # Calculate path components
    # Number of directories to go up (from file's directory, not the file itself)
    ups = len(from_parts) - 1 - common_length

    # Remaining path to target
    remaining = to_parts[common_length:]

    if ups == 0 and not remaining:
        # Same directory, different file
        return f"{to_parts[-1]}.md"

    # Build relative path
    rel_parts = ['..'] * ups + remaining

    return '/'.join(rel_parts) + '.md'


def is_internal_link(url: str, base_url: str) -> bool:
    """
    Check if a URL is an internal link to the documentation.

    Args:
        url: The URL to check
        base_url: The base URL of the documentation site

    Returns:
        True if the URL is internal, False otherwise
    """
    if not url:
        return False

    # Parse URLs
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)

    # Absolute URL with same host
    if parsed_url.netloc:
        return parsed_url.netloc == parsed_base.netloc

    # Relative URL (starts with / or is path-only)
    if url.startswith('/') or not parsed_url.scheme:
        return True

    return False


def normalize_url(url: str, base_url: str) -> tuple[str, str]:
    """
    Normalize a URL and extract any fragment.

    Args:
        url: The URL to normalize
        base_url: The base URL for resolving relative URLs

    Returns:
        Tuple of (normalized_url_without_fragment, fragment)
    """
    # Parse the URL
    parsed = urlparse(url)
    fragment = parsed.fragment

    # Remove fragment and query for matching
    url_without_fragment = url.split('#')[0].split('?')[0]

    # If relative, make absolute
    if not parsed.netloc:
        url_without_fragment = urljoin(base_url, url_without_fragment)

    # Normalize trailing slashes
    url_without_fragment = url_without_fragment.rstrip('/')

    return url_without_fragment, fragment


def transform_links(
    content: str,
    current_file_path: str,
    base_url: str,
    crawled_urls: Set[str],
    url_to_filepath: Callable[[str], str],
) -> str:
    """
    Transform internal web links to relative markdown file paths.

    Args:
        content: Markdown content with links
        current_file_path: Path of the current file (without .md extension)
        base_url: Base URL of the documentation site
        crawled_urls: Set of URLs that were crawled (and thus have local files)
        url_to_filepath: Function to convert URL to file path

    Returns:
        Content with internal links transformed to relative paths

    Edge cases handled:
        - External links: preserved as-is
        - Uncrawled pages: URL preserved as-is
        - Fragments (#anchor): preserved in relative link
        - Query parameters: ignored for matching
        - Link titles: [text](url "title") - title attribute is stripped
    """
    # Match markdown links: [text](url) or [text](url "title") or [text](url 'title')
    # Group 1: link text
    # Group 2: URL (may include fragment)
    # Group 3: optional title with quotes (to be stripped)
    link_pattern = re.compile(r'\[([^\]]*)\]\(([^\s)]+)(?:\s+["\'][^"\']*["\'])?\)')

    def replace_link(match):
        link_text = match.group(1)
        url = match.group(2)

        # Skip non-internal links
        if not is_internal_link(url, base_url):
            return match.group(0)

        # Normalize URL and extract fragment
        normalized_url, fragment = normalize_url(url, base_url)

        # Check if this URL was crawled
        # Try both with and without trailing slash
        url_found = False
        matched_url = None
        for crawled_url in crawled_urls:
            crawled_normalized = crawled_url.rstrip('/')
            if normalized_url == crawled_normalized:
                url_found = True
                matched_url = crawled_url
                break

        if not url_found:
            # URL not crawled, keep original link
            return match.group(0)

        # Get target file path
        target_path = url_to_filepath(matched_url)
        if not target_path:
            return match.group(0)

        # Compute relative path
        relative_path = compute_relative_path(current_file_path, target_path)

        # Add fragment if present
        if fragment:
            relative_path = f"{relative_path}#{fragment}"

        return f'[{link_text}]({relative_path})'

    return link_pattern.sub(replace_link, content)
