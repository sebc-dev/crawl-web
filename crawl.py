#!/usr/bin/env python3
"""
Generic documentation crawler CLI.

Crawl documentation sources defined in the sources/ directory.

Usage:
    python crawl.py <source-name>                    # Full crawl
    python crawl.py <source-name> --discover-only    # List URLs only
    python crawl.py <source-name> --check            # Check local files for changes
    python crawl.py <source-name> --check-remote     # Check remote for changes
    python crawl.py --list                           # List available sources
    python crawl.py <source-name> --language fr      # Different language
"""

import asyncio
import sys
import re
import argparse
import importlib.util
from pathlib import Path
from typing import Optional

import yaml

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from crawl4ai_toolkit import discover_urls, crawl_pages, CleanerBase
from crawl4ai_toolkit.generator import generate_markdown_files, generate_index
from crawl4ai_toolkit.state import (
    CrawlState,
    check_local_file,
    check_page_changed,
    print_change_report,
    ChangeResult,
)


def list_sources() -> list:
    """List all available sources in the sources/ directory."""
    sources_dir = PROJECT_ROOT / "sources"
    if not sources_dir.exists():
        return []

    sources = []
    for source_dir in sources_dir.iterdir():
        if source_dir.is_dir():
            config_file = source_dir / "config.yaml"
            if config_file.exists():
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                sources.append({
                    'name': source_dir.name,
                    'title': config.get('name', source_dir.name),
                    'base_url': config.get('base_url', ''),
                })
    return sources


def load_source_config(source_name: str) -> dict:
    """Load configuration for a source."""
    config_path = PROJECT_ROOT / "sources" / source_name / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Source '{source_name}' not found. Config: {config_path}")

    with open(config_path) as f:
        return yaml.safe_load(f)


def load_source_cleaner(source_name: str, config: dict) -> CleanerBase:
    """Load the cleaner for a source."""
    cleaner_config = config.get('cleaner', {})
    module_name = cleaner_config.get('module')

    if not module_name:
        return CleanerBase()

    # Load cleaner module from source directory
    source_dir = PROJECT_ROOT / "sources" / source_name
    cleaner_path = source_dir / f"{module_name}.py"

    if not cleaner_path.exists():
        print(f"  Warning: Cleaner module not found: {cleaner_path}")
        return CleanerBase()

    spec = importlib.util.spec_from_file_location(module_name, cleaner_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Look for a class ending in 'Cleaner'
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (isinstance(attr, type) and
            issubclass(attr, CleanerBase) and
            attr is not CleanerBase):
            return attr()

    return CleanerBase()


def load_url_mappings(source_name: str):
    """Load URL mappings module for a source."""
    source_dir = PROJECT_ROOT / "sources" / source_name
    mappings_path = source_dir / "url_mappings.py"

    if not mappings_path.exists():
        return None

    spec = importlib.util.spec_from_file_location("url_mappings", mappings_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def check_local(source_name: str) -> None:
    """
    Check local files against saved state.

    Compares the current output files with the saved state to detect
    if any files have been modified locally since the last crawl.
    """
    source_dir = PROJECT_ROOT / "sources" / source_name
    output_dir = source_dir / "output"

    state = CrawlState(source_dir)

    if state.page_count == 0:
        print(f"No saved state for {source_name}. Run a crawl first.")
        return

    results = []

    for file_path, page_state in state.get_all_pages().items():
        result = check_local_file(output_dir, file_path, page_state)
        results.append(result)

    # Check for new files not in state
    if output_dir.exists():
        for md_file in output_dir.rglob("*.md"):
            if md_file.name == "index.md":
                continue
            rel_path = str(md_file.relative_to(output_dir))[:-3]  # Remove .md
            if rel_path not in state.get_all_pages():
                results.append(ChangeResult(
                    url="",
                    file_path=rel_path,
                    status="new",
                    reason="new_local_file"
                ))

    print_change_report(results, source_name, state.get_last_crawl(), is_remote=False)


async def check_remote(
    source_name: str,
    max_concurrent: Optional[int] = None,
    language: Optional[str] = None,
) -> None:
    """
    Check remote pages for changes.

    Re-crawls all pages and compares with saved state to detect
    if any pages have changed on the remote server.
    """
    # Load config
    config = load_source_config(source_name)
    source_dir = PROJECT_ROOT / "sources" / source_name
    output_dir = source_dir / "output"

    state = CrawlState(source_dir)

    if state.page_count == 0:
        print(f"No saved state for {source_name}. Run a crawl first.")
        return

    # Override config with CLI args
    base_url = config['base_url']
    lang = language or config.get('language', 'en-US')
    crawler_config = config.get('crawler', {})
    concurrent = max_concurrent or crawler_config.get('max_concurrent', 5)
    page_timeout = crawler_config.get('page_timeout', 30000)
    excluded_tags = crawler_config.get('excluded_tags', [])

    print(f"Checking remote changes for {config.get('name', source_name)}...")
    print(f"Last crawl: {state.get_last_crawl()}")

    # Load URL mappings
    mappings_module = load_url_mappings(source_name)

    # Build seed URLs (URLs in config should be complete paths including language)
    seed_urls = [
        f"{base_url}{url}" for url in config.get('seed_urls', [])
    ]

    # Define URL normalization function
    def normalize_url(url: str, language: str) -> str:
        if mappings_module and hasattr(mappings_module, 'normalize_mdn_url'):
            return mappings_module.normalize_mdn_url(url, language)
        return url

    # Discover URLs
    urls = await discover_urls(
        seed_urls=seed_urls,
        include_patterns=config.get('include_patterns', []),
        base_url=base_url,
        language=lang,
        max_concurrent=concurrent,
        page_timeout=page_timeout,
        excluded_tags=excluded_tags,
        normalize_url=normalize_url,
        exclude_patterns=config.get('exclude_patterns'),
    )

    # Add known pages
    if mappings_module:
        known_urls = mappings_module.build_urls(base_url, lang)
        for url in known_urls.values():
            urls.add(url)

    # URL to file path function
    def url_to_filepath(url: str) -> str:
        if mappings_module and hasattr(mappings_module, 'get_file_path_from_url'):
            return mappings_module.get_file_path_from_url(url)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        return path  # Keep slashes for hierarchical structure

    print(f"Crawling {len(urls)} pages to check for changes...")

    # Crawl all pages
    crawl_results = await crawl_pages(
        urls=list(urls),
        max_concurrent=concurrent,
        page_timeout=page_timeout,
        excluded_tags=excluded_tags,
    )

    results = []
    saved_pages = state.get_all_pages()

    # Load cleaner for consistent hash computation
    cleaner = load_source_cleaner(source_name, config)

    # Title cleaner
    output_config = config.get('output', {})
    title_pattern = output_config.get('title_suffix_pattern')

    def clean_title(title: str) -> str:
        if title_pattern:
            title = re.sub(title_pattern, '', title)
        return title.strip()

    # Check each crawled page
    for url, crawl_result in crawl_results.items():
        file_path = url_to_filepath(url)
        if not file_path:
            continue

        # Clean content same way as generator
        markdown_content = crawl_result.get('markdown', '')
        title = crawl_result.get('title', '') or file_path.split('/')[-1]
        title = clean_title(title)
        markdown_content = cleaner.clean(markdown_content, title)

        # Compute hash the same way as generator
        from crawl4ai_toolkit.state import compute_content_hash
        new_hash = compute_content_hash(f"# {title}\n\n{markdown_content}")

        saved_state = saved_pages.get(file_path)

        if saved_state is None:
            results.append(ChangeResult(url, file_path, 'new', 'new_page'))
        elif new_hash != saved_state.get('content_hash'):
            results.append(ChangeResult(url, file_path, 'changed', 'content_hash'))
        else:
            results.append(ChangeResult(url, file_path, 'unchanged', 'content_hash'))

    # Check for removed pages (in state but not in crawl results)
    crawled_paths = {url_to_filepath(url) for url in crawl_results.keys()}
    for file_path, page_state in saved_pages.items():
        if file_path not in crawled_paths:
            results.append(ChangeResult(
                page_state.get('url', ''),
                file_path,
                'removed',
                'not_found'
            ))

    print_change_report(results, source_name, state.get_last_crawl(), is_remote=True)


async def run_crawl(
    source_name: str,
    discover_only: bool = False,
    skip_discovery: bool = False,
    max_concurrent: Optional[int] = None,
    language: Optional[str] = None,
):
    """Run the crawl for a source."""
    # Load config
    config = load_source_config(source_name)
    print("=" * 60)
    print(f"Crawling: {config.get('name', source_name)}")
    print("=" * 60)

    # Override config with CLI args
    base_url = config['base_url']
    lang = language or config.get('language', 'en-US')
    crawler_config = config.get('crawler', {})
    concurrent = max_concurrent or crawler_config.get('max_concurrent', 5)
    page_timeout = crawler_config.get('page_timeout', 30000)
    excluded_tags = crawler_config.get('excluded_tags', [])

    print(f"Base URL: {base_url}")
    print(f"Language: {lang}")
    print(f"Max concurrent: {concurrent}")
    print("=" * 60)

    # Load URL mappings
    mappings_module = load_url_mappings(source_name)

    # Build seed URLs (URLs in config should be complete paths including language)
    seed_urls = [
        f"{base_url}{url}" for url in config.get('seed_urls', [])
    ]

    # Define URL normalization function
    def normalize_url(url: str, language: str) -> str:
        if mappings_module and hasattr(mappings_module, 'normalize_mdn_url'):
            return mappings_module.normalize_mdn_url(url, language)
        return url

    # Phase 1: Discover URLs
    if skip_discovery and mappings_module:
        # Use known pages
        known_urls = mappings_module.build_urls(base_url, lang)
        urls = set(known_urls.values())
        print(f"\nUsing {len(urls)} known URLs (discovery skipped)")
    else:
        urls = await discover_urls(
            seed_urls=seed_urls,
            include_patterns=config.get('include_patterns', []),
            base_url=base_url,
            language=lang,
            max_concurrent=concurrent,
            page_timeout=page_timeout,
            excluded_tags=excluded_tags,
            normalize_url=normalize_url,
            exclude_patterns=config.get('exclude_patterns'),
        )

        # Add known pages
        if mappings_module:
            known_urls = mappings_module.build_urls(base_url, lang)
            for url in known_urls.values():
                urls.add(url)

    if discover_only:
        print(f"\n{'=' * 60}")
        print(f"Discovered {len(urls)} URLs:")
        print("=" * 60)
        for url in sorted(urls):
            print(f"  {url}")
        print(f"\nTotal: {len(urls)} URLs")
        return

    # Phase 2: Crawl pages
    results = await crawl_pages(
        urls=list(urls),
        max_concurrent=concurrent,
        page_timeout=page_timeout,
        excluded_tags=excluded_tags,
    )

    # Phase 3: Generate files
    source_dir = PROJECT_ROOT / "sources" / source_name
    output_dir = source_dir / "output"
    cleaner = load_source_cleaner(source_name, config)

    # Initialize crawl state for tracking
    crawl_state = CrawlState(source_dir)

    # URL to file path function
    def url_to_filepath(url: str) -> str:
        if mappings_module and hasattr(mappings_module, 'get_file_path_from_url'):
            return mappings_module.get_file_path_from_url(url)
        # Fallback: use URL path
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        return path  # Keep slashes for hierarchical structure

    # Title cleaner
    output_config = config.get('output', {})
    title_pattern = output_config.get('title_suffix_pattern')

    def clean_title(title: str) -> str:
        if title_pattern:
            title = re.sub(title_pattern, '', title)
        return title.strip()

    files_written, index_entries = generate_markdown_files(
        results=results,
        output_dir=output_dir,
        url_to_filepath=url_to_filepath,
        cleaner=cleaner,
        frontmatter=output_config.get('frontmatter', True),
        title_cleaner=clean_title,
        crawl_state=crawl_state,
        base_url=base_url,
        transform_internal_links=output_config.get('transform_links', True),
    )

    # Save crawl state
    crawl_state.save()
    print(f"  State saved: {crawl_state.state_file}")

    # Generate index
    generate_index(
        output_dir=output_dir,
        entries=index_entries,
        title=f"{config.get('name', source_name)} Documentation",
        description="This documentation was extracted automatically.",
        category_order=['main', 'guides', 'interfaces', 'extensions'],
        category_titles={
            'main': 'Overview',
            'guides': 'Guides',
            'interfaces': 'Interfaces',
            'extensions': 'Document and Element Extensions',
        },
    )

    print(f"\n{'=' * 60}")
    print("Crawl Complete!")
    print("=" * 60)
    print(f"URLs discovered: {len(urls)}")
    print(f"Pages crawled: {len(results)}")
    print(f"Files written: {files_written + 1}")  # +1 for index
    print(f"Output directory: {output_dir.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Crawl documentation sources to markdown files"
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Source name to crawl (directory name in sources/)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available sources"
    )
    parser.add_argument(
        "--language",
        help="Override language (e.g., fr, es, de)"
    )
    parser.add_argument(
        "--max-concurrent", "-c",
        type=int,
        help="Maximum concurrent crawls"
    )
    parser.add_argument(
        "--discover-only", "-d",
        action="store_true",
        help="Only discover and list URLs, don't crawl"
    )
    parser.add_argument(
        "--skip-discovery",
        action="store_true",
        help="Skip URL discovery, use only known pages list"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check local files against saved state (detect local modifications)"
    )
    parser.add_argument(
        "--check-remote",
        action="store_true",
        help="Re-crawl and check for remote changes"
    )

    args = parser.parse_args()

    if args.list:
        sources = list_sources()
        if not sources:
            print("No sources found in sources/ directory")
            return

        print("Available sources:")
        print("-" * 40)
        for source in sources:
            print(f"  {source['name']}")
            print(f"    Title: {source['title']}")
            print(f"    URL: {source['base_url']}")
            print()
        return

    if not args.source:
        parser.print_help()
        print("\nError: source name required (or use --list)")
        sys.exit(1)

    try:
        if args.check:
            asyncio.run(check_local(args.source))
        elif args.check_remote:
            asyncio.run(check_remote(
                source_name=args.source,
                max_concurrent=args.max_concurrent,
                language=args.language,
            ))
        else:
            asyncio.run(run_crawl(
                source_name=args.source,
                discover_only=args.discover_only,
                skip_discovery=args.skip_discovery,
                max_concurrent=args.max_concurrent,
                language=args.language,
            ))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCrawl interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()
