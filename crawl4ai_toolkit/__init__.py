"""
Crawl4AI Toolkit - Generic web crawling library

A modular toolkit for crawling documentation sites and converting to markdown.
"""

from .crawler import discover_urls, crawl_pages
from .cleaner import CleanerBase, clean_heading_anchors, clean_excessive_whitespace
from .generator import generate_markdown_files, generate_index
from .state import (
    CrawlState,
    ChangeResult,
    compute_content_hash,
    check_headers,
    check_page_changed,
    check_local_file,
    print_change_report,
)

__version__ = "0.1.0"

__all__ = [
    # Crawler
    "discover_urls",
    "crawl_pages",
    # Cleaner
    "CleanerBase",
    "clean_heading_anchors",
    "clean_excessive_whitespace",
    # Generator
    "generate_markdown_files",
    "generate_index",
    # State / Change detection
    "CrawlState",
    "ChangeResult",
    "compute_content_hash",
    "check_headers",
    "check_page_changed",
    "check_local_file",
    "print_change_report",
]
