"""
Generic web crawler using Crawl4AI.

Provides URL discovery and page crawling functionality that can be
configured for different documentation sources.
"""

import re
from typing import List, Dict, Set, Optional, Callable
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


async def discover_urls(
    seed_urls: List[str],
    include_patterns: List[str],
    base_url: str,
    language: str = "en-US",
    max_concurrent: int = 5,
    page_timeout: int = 30000,
    excluded_tags: Optional[List[str]] = None,
    normalize_url: Optional[Callable[[str, str], str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> Set[str]:
    """
    Discover URLs by crawling seed pages and extracting internal links.

    Args:
        seed_urls: Initial URLs to crawl for link discovery
        include_patterns: Regex patterns to filter discovered URLs
        base_url: Base URL for the site (e.g., "https://developer.mozilla.org")
        language: Language code for URL normalization
        max_concurrent: Maximum concurrent crawls
        page_timeout: Page load timeout in milliseconds
        excluded_tags: HTML tags to exclude from content
        normalize_url: Optional function to normalize URLs (receives url, language)
        exclude_patterns: Regex patterns to exclude URLs (applied after include)

    Returns:
        Set of discovered URLs matching the include patterns
    """
    if excluded_tags is None:
        excluded_tags = ["nav", "footer", "aside", "header"]

    print(f"Phase 1: Discovering URLs from {len(seed_urls)} seed URLs...")

    discovered: Set[str] = set()

    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1280,
        viewport_height=800,
        verbose=False
    )

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=excluded_tags,
        remove_overlay_elements=True,
        page_timeout=page_timeout,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls=seed_urls,
            config=crawler_config,
            max_concurrent=max_concurrent
        )

        for result in results:
            if result.success:
                discovered.add(result.url)
                print(f"  Seed: {result.url}")

                # Extract internal links
                internal_links = result.links.get('internal', [])
                for link_info in internal_links:
                    href = link_info.get('href', '') if isinstance(link_info, dict) else str(link_info)

                    # Make absolute URL
                    if href.startswith('/'):
                        href = f"{base_url}{href}"

                    # Check if matches any include pattern and not excluded
                    if _url_matches_patterns(href, include_patterns):
                        if exclude_patterns and _url_matches_patterns(href, exclude_patterns):
                            continue  # Skip excluded URLs
                        # Normalize URL if function provided
                        if normalize_url:
                            href = normalize_url(href, language)
                        discovered.add(href)

    print(f"  Discovered {len(discovered)} URLs")
    return discovered


def _url_matches_patterns(url: str, patterns: List[str]) -> bool:
    """Check if URL matches any of the include patterns."""
    for pattern in patterns:
        if re.search(pattern, url):
            return True
    return False


async def crawl_pages(
    urls: List[str],
    max_concurrent: int = 5,
    page_timeout: int = 30000,
    excluded_tags: Optional[List[str]] = None,
) -> Dict[str, dict]:
    """
    Crawl pages and extract content.

    Args:
        urls: List of URLs to crawl
        max_concurrent: Maximum concurrent crawls
        page_timeout: Page load timeout in milliseconds
        excluded_tags: HTML tags to exclude from content

    Returns:
        Dict mapping URL to crawl result with keys:
        - url: The page URL
        - title: Page title from metadata
        - description: Page description from metadata
        - markdown: Extracted markdown content
        - links: Internal and external links
    """
    if excluded_tags is None:
        excluded_tags = ["nav", "footer", "aside", "header", "script", "style"]

    print(f"\nPhase 2: Crawling {len(urls)} pages...")

    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1280,
        viewport_height=800,
        verbose=False
    )

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=excluded_tags,
        remove_overlay_elements=True,
        page_timeout=page_timeout,
        screenshot=False,
    )

    results_map = {}
    failed = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Process in batches to show progress
        batch_size = max_concurrent * 2
        url_list = list(urls)

        for i in range(0, len(url_list), batch_size):
            batch = url_list[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(url_list) + batch_size - 1) // batch_size
            print(f"  Batch {batch_num}/{total_batches}: {len(batch)} URLs")

            batch_results = await crawler.arun_many(
                urls=batch,
                config=crawler_config,
                max_concurrent=max_concurrent
            )

            for result in batch_results:
                if result.success:
                    results_map[result.url] = {
                        'url': result.url,
                        'title': result.metadata.get('title', ''),
                        'description': result.metadata.get('description', ''),
                        'markdown': result.markdown,
                        'links': result.links,
                        # HTTP headers for change detection
                        'etag': result.response_headers.get('etag') if hasattr(result, 'response_headers') and result.response_headers else None,
                        'last_modified': result.response_headers.get('last-modified') if hasattr(result, 'response_headers') and result.response_headers else None,
                    }
                    print(f"    OK: {result.url.split('/')[-1]}")
                else:
                    failed.append({
                        'url': result.url,
                        'error': result.error_message
                    })
                    print(f"    FAIL: {result.url} - {result.error_message}")

    print(f"  Crawled: {len(results_map)} success, {len(failed)} failed")

    if failed:
        print("\n  Failed URLs:")
        for f in failed:
            print(f"    - {f['url']}: {f['error']}")

    return results_map
