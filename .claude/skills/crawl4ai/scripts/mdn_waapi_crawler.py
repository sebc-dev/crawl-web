#!/usr/bin/env python3
"""
MDN Web Animations API Documentation Crawler

Extracts all pages from MDN Web Animations API documentation
and converts them to organized markdown files.

Usage:
    python mdn_waapi_crawler.py                           # Full crawl with defaults
    python mdn_waapi_crawler.py --discover-only           # List URLs without crawling
    python mdn_waapi_crawler.py --output-dir ./docs       # Custom output directory
    python mdn_waapi_crawler.py --language fr             # French documentation
    python mdn_waapi_crawler.py --max-concurrent 3        # Limit concurrency
"""

import asyncio
import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse
from datetime import datetime

# Version check
MIN_CRAWL4AI_VERSION = "0.7.4"
try:
    from crawl4ai.__version__ import __version__
    from packaging import version
    if version.parse(__version__) < version.parse(MIN_CRAWL4AI_VERSION):
        print(f"Warning: Crawl4AI {MIN_CRAWL4AI_VERSION}+ recommended (you have {__version__})")
except ImportError:
    print(f"Crawl4AI {MIN_CRAWL4AI_VERSION}+ required")

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


def clean_markdown(content: str, title: str = "") -> str:
    """
    Clean MDN markdown content:
    - Remove anchor links from headings
    - Remove Baseline info block
    - Remove duplicated title at the start
    - Remove MDN footer
    """
    lines = content.split('\n')
    cleaned_lines = []
    skip_until_next_heading = False
    in_baseline_block = False
    found_first_heading = False

    for i, line in enumerate(lines):
        # Skip the first H1 heading (duplicated title)
        if not found_first_heading and line.startswith('# '):
            found_first_heading = True
            continue

        # Detect and skip Baseline block
        if 'Baseline' in line and ('Widely available' in line or 'Limited availability' in line):
            in_baseline_block = True
            continue

        if in_baseline_block:
            # End of baseline block when we hit actual content
            if line.startswith('#') or (line.strip() and not line.startswith('  *') and not line.startswith('This feature')):
                in_baseline_block = False
            else:
                continue

        # Remove MDN footer section
        if line.strip() == '## Help improve MDN' or line.startswith('## Help improve MDN'):
            break

        # Clean anchor links from headings: ## [Title](url) -> ## Title
        heading_match = re.match(r'^(#{1,6})\s+\[([^\]]+)\]\([^)]+\)\s*$', line)
        if heading_match:
            level = heading_match.group(1)
            heading_text = heading_match.group(2)
            cleaned_lines.append(f"{level} {heading_text}")
            continue

        cleaned_lines.append(line)

    # Join and clean up excessive blank lines
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()

    return result


# Base URL for MDN
MDN_BASE = "https://developer.mozilla.org"

# URL patterns to include (relative to /docs/Web/API/)
INCLUDE_PATTERNS = [
    r"/docs/Web/API/Web_Animations_API($|/)",
    r"/docs/Web/API/Animation($|/)",
    r"/docs/Web/API/AnimationEffect($|/)",
    r"/docs/Web/API/AnimationEvent($|/)",
    r"/docs/Web/API/AnimationTimeline($|/)",
    r"/docs/Web/API/AnimationPlaybackEvent($|/)",
    r"/docs/Web/API/DocumentTimeline($|/)",
    r"/docs/Web/API/KeyframeEffect($|/)",
    r"/docs/Web/API/ScrollTimeline($|/)",
    r"/docs/Web/API/ViewTimeline($|/)",
    r"/docs/Web/API/Document/timeline($|$)",
    r"/docs/Web/API/Document/getAnimations($|$)",
    r"/docs/Web/API/Element/animate($|$)",
    r"/docs/Web/API/Element/getAnimations($|$)",
]

# Known pages (pre-compiled list based on MDN structure)
KNOWN_PAGES = {
    # Main page
    "Web_Animations_API": "/docs/Web/API/Web_Animations_API",

    # Guides
    "guides/Using_the_Web_Animations_API": "/docs/Web/API/Web_Animations_API/Using_the_Web_Animations_API",
    "guides/Web_Animations_API_Concepts": "/docs/Web/API/Web_Animations_API/Web_Animations_API_Concepts",
    "guides/Keyframe_Formats": "/docs/Web/API/Web_Animations_API/Keyframe_Formats",
    "guides/Tips": "/docs/Web/API/Web_Animations_API/Tips",

    # Animation interface
    "interfaces/Animation/index": "/docs/Web/API/Animation",
    "interfaces/Animation/Animation": "/docs/Web/API/Animation/Animation",
    "interfaces/Animation/currentTime": "/docs/Web/API/Animation/currentTime",
    "interfaces/Animation/effect": "/docs/Web/API/Animation/effect",
    "interfaces/Animation/finished": "/docs/Web/API/Animation/finished",
    "interfaces/Animation/id": "/docs/Web/API/Animation/id",
    "interfaces/Animation/overallProgress": "/docs/Web/API/Animation/overallProgress",
    "interfaces/Animation/pending": "/docs/Web/API/Animation/pending",
    "interfaces/Animation/playbackRate": "/docs/Web/API/Animation/playbackRate",
    "interfaces/Animation/playState": "/docs/Web/API/Animation/playState",
    "interfaces/Animation/ready": "/docs/Web/API/Animation/ready",
    "interfaces/Animation/replaceState": "/docs/Web/API/Animation/replaceState",
    "interfaces/Animation/startTime": "/docs/Web/API/Animation/startTime",
    "interfaces/Animation/timeline": "/docs/Web/API/Animation/timeline",
    "interfaces/Animation/cancel": "/docs/Web/API/Animation/cancel",
    "interfaces/Animation/commitStyles": "/docs/Web/API/Animation/commitStyles",
    "interfaces/Animation/finish": "/docs/Web/API/Animation/finish",
    "interfaces/Animation/pause": "/docs/Web/API/Animation/pause",
    "interfaces/Animation/persist": "/docs/Web/API/Animation/persist",
    "interfaces/Animation/play": "/docs/Web/API/Animation/play",
    "interfaces/Animation/reverse": "/docs/Web/API/Animation/reverse",
    "interfaces/Animation/updatePlaybackRate": "/docs/Web/API/Animation/updatePlaybackRate",
    "interfaces/Animation/cancel_event": "/docs/Web/API/Animation/cancel_event",
    "interfaces/Animation/finish_event": "/docs/Web/API/Animation/finish_event",
    "interfaces/Animation/remove_event": "/docs/Web/API/Animation/remove_event",

    # KeyframeEffect interface
    "interfaces/KeyframeEffect/index": "/docs/Web/API/KeyframeEffect",
    "interfaces/KeyframeEffect/KeyframeEffect": "/docs/Web/API/KeyframeEffect/KeyframeEffect",
    "interfaces/KeyframeEffect/target": "/docs/Web/API/KeyframeEffect/target",
    "interfaces/KeyframeEffect/pseudoElement": "/docs/Web/API/KeyframeEffect/pseudoElement",
    "interfaces/KeyframeEffect/iterationComposite": "/docs/Web/API/KeyframeEffect/iterationComposite",
    "interfaces/KeyframeEffect/composite": "/docs/Web/API/KeyframeEffect/composite",
    "interfaces/KeyframeEffect/getKeyframes": "/docs/Web/API/KeyframeEffect/getKeyframes",
    "interfaces/KeyframeEffect/setKeyframes": "/docs/Web/API/KeyframeEffect/setKeyframes",

    # AnimationEffect interface
    "interfaces/AnimationEffect/index": "/docs/Web/API/AnimationEffect",
    "interfaces/AnimationEffect/getComputedTiming": "/docs/Web/API/AnimationEffect/getComputedTiming",
    "interfaces/AnimationEffect/getTiming": "/docs/Web/API/AnimationEffect/getTiming",
    "interfaces/AnimationEffect/updateTiming": "/docs/Web/API/AnimationEffect/updateTiming",

    # AnimationTimeline interface
    "interfaces/AnimationTimeline/index": "/docs/Web/API/AnimationTimeline",
    "interfaces/AnimationTimeline/currentTime": "/docs/Web/API/AnimationTimeline/currentTime",
    "interfaces/AnimationTimeline/duration": "/docs/Web/API/AnimationTimeline/duration",

    # DocumentTimeline interface
    "interfaces/DocumentTimeline/index": "/docs/Web/API/DocumentTimeline",
    "interfaces/DocumentTimeline/DocumentTimeline": "/docs/Web/API/DocumentTimeline/DocumentTimeline",

    # AnimationEvent interface
    "interfaces/AnimationEvent/index": "/docs/Web/API/AnimationEvent",
    "interfaces/AnimationEvent/AnimationEvent": "/docs/Web/API/AnimationEvent/AnimationEvent",
    "interfaces/AnimationEvent/animationName": "/docs/Web/API/AnimationEvent/animationName",
    "interfaces/AnimationEvent/elapsedTime": "/docs/Web/API/AnimationEvent/elapsedTime",
    "interfaces/AnimationEvent/pseudoElement": "/docs/Web/API/AnimationEvent/pseudoElement",

    # AnimationPlaybackEvent interface
    "interfaces/AnimationPlaybackEvent/index": "/docs/Web/API/AnimationPlaybackEvent",
    "interfaces/AnimationPlaybackEvent/AnimationPlaybackEvent": "/docs/Web/API/AnimationPlaybackEvent/AnimationPlaybackEvent",
    "interfaces/AnimationPlaybackEvent/currentTime": "/docs/Web/API/AnimationPlaybackEvent/currentTime",
    "interfaces/AnimationPlaybackEvent/timelineTime": "/docs/Web/API/AnimationPlaybackEvent/timelineTime",

    # ScrollTimeline interface
    "interfaces/ScrollTimeline/index": "/docs/Web/API/ScrollTimeline",
    "interfaces/ScrollTimeline/ScrollTimeline": "/docs/Web/API/ScrollTimeline/ScrollTimeline",
    "interfaces/ScrollTimeline/source": "/docs/Web/API/ScrollTimeline/source",
    "interfaces/ScrollTimeline/axis": "/docs/Web/API/ScrollTimeline/axis",

    # ViewTimeline interface
    "interfaces/ViewTimeline/index": "/docs/Web/API/ViewTimeline",
    "interfaces/ViewTimeline/ViewTimeline": "/docs/Web/API/ViewTimeline/ViewTimeline",
    "interfaces/ViewTimeline/subject": "/docs/Web/API/ViewTimeline/subject",
    "interfaces/ViewTimeline/startOffset": "/docs/Web/API/ViewTimeline/startOffset",
    "interfaces/ViewTimeline/endOffset": "/docs/Web/API/ViewTimeline/endOffset",

    # Extensions (Document/Element)
    "extensions/Document.timeline": "/docs/Web/API/Document/timeline",
    "extensions/Document.getAnimations": "/docs/Web/API/Document/getAnimations",
    "extensions/Element.animate": "/docs/Web/API/Element/animate",
    "extensions/Element.getAnimations": "/docs/Web/API/Element/getAnimations",
}


def url_matches_patterns(url: str) -> bool:
    """Check if URL matches any of the include patterns."""
    for pattern in INCLUDE_PATTERNS:
        if re.search(pattern, url):
            return True
    return False


def get_file_path_from_url(url: str) -> str:
    """Map URL to output file path."""
    parsed = urlparse(url)
    path = parsed.path

    # Remove language prefix
    path = re.sub(r'^/[a-z]{2}(-[A-Z]{2})?/', '/', path)

    # Find matching known page
    for file_path, url_path in KNOWN_PAGES.items():
        if path == url_path or path.endswith(url_path):
            return file_path

    # Fallback: derive from URL path
    path = path.replace('/docs/Web/API/', '')
    path = path.strip('/')

    # Handle interface pages
    parts = path.split('/')
    if len(parts) == 1:
        return f"interfaces/{parts[0]}/index"
    elif len(parts) == 2:
        return f"interfaces/{parts[0]}/{parts[1]}"

    return path


def build_urls(language: str = "en-US") -> Dict[str, str]:
    """Build full URLs for all known pages."""
    urls = {}
    for file_path, url_path in KNOWN_PAGES.items():
        full_url = f"{MDN_BASE}/{language}{url_path}"
        urls[file_path] = full_url
    return urls


async def discover_urls(language: str = "en-US", max_concurrent: int = 5) -> Set[str]:
    """
    Phase 1: Discover all relevant URLs by crawling seed pages.
    Returns a set of discovered URLs matching our patterns.
    """
    print(f"Phase 1: Discovering URLs...")

    seed_urls = [
        f"{MDN_BASE}/{language}/docs/Web/API/Web_Animations_API",
        f"{MDN_BASE}/{language}/docs/Web/API/Animation",
        f"{MDN_BASE}/{language}/docs/Web/API/KeyframeEffect",
        f"{MDN_BASE}/{language}/docs/Web/API/AnimationEffect",
        f"{MDN_BASE}/{language}/docs/Web/API/AnimationTimeline",
        f"{MDN_BASE}/{language}/docs/Web/API/DocumentTimeline",
        f"{MDN_BASE}/{language}/docs/Web/API/AnimationEvent",
        f"{MDN_BASE}/{language}/docs/Web/API/AnimationPlaybackEvent",
        f"{MDN_BASE}/{language}/docs/Web/API/ScrollTimeline",
        f"{MDN_BASE}/{language}/docs/Web/API/ViewTimeline",
    ]

    discovered: Set[str] = set()

    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1280,
        viewport_height=800,
        verbose=False
    )

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "footer", "aside", "header"],
        remove_overlay_elements=True,
        page_timeout=30000,
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

                    # Normalize URL
                    if href.startswith('/'):
                        href = f"{MDN_BASE}{href}"

                    # Check if matches our patterns
                    if url_matches_patterns(href):
                        # Normalize language
                        href = re.sub(r'developer\.mozilla\.org/[a-z]{2}(-[A-Z]{2})?/',
                                     f'developer.mozilla.org/{language}/', href)
                        discovered.add(href)

    # Also add all known pages
    known_urls = build_urls(language)
    for url in known_urls.values():
        discovered.add(url)

    print(f"  Discovered {len(discovered)} URLs")
    return discovered


async def crawl_pages(urls: List[str], max_concurrent: int = 5) -> Dict[str, dict]:
    """
    Phase 2: Crawl all discovered pages and extract content.
    Returns a dict mapping URL to crawl result data.
    """
    print(f"\nPhase 2: Crawling {len(urls)} pages...")

    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1280,
        viewport_height=800,
        verbose=False
    )

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "footer", "aside", "header", "script", "style"],
        remove_overlay_elements=True,
        page_timeout=30000,
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
            print(f"  Batch {i // batch_size + 1}/{(len(url_list) + batch_size - 1) // batch_size}: {len(batch)} URLs")

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


def generate_markdown_files(results: Dict[str, dict], output_dir: Path, language: str):
    """
    Phase 3: Generate organized markdown files from crawl results.
    """
    print(f"\nPhase 3: Generating markdown files in {output_dir}...")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (output_dir / "guides").mkdir(exist_ok=True)
    (output_dir / "interfaces").mkdir(exist_ok=True)
    (output_dir / "extensions").mkdir(exist_ok=True)

    # Interface subdirectories
    interfaces = [
        "Animation", "KeyframeEffect", "AnimationEffect", "AnimationTimeline",
        "DocumentTimeline", "AnimationEvent", "AnimationPlaybackEvent",
        "ScrollTimeline", "ViewTimeline"
    ]
    for interface in interfaces:
        (output_dir / "interfaces" / interface).mkdir(exist_ok=True)

    files_written = 0
    index_entries = {
        'main': [],
        'guides': [],
        'interfaces': {},
        'extensions': []
    }

    known_urls = build_urls(language)

    for file_path, url in known_urls.items():
        if url not in results:
            print(f"  SKIP (not crawled): {file_path}")
            continue

        result = results[url]
        markdown_content = result['markdown']
        title = result['title'] or file_path.split('/')[-1]

        # Clean up title (remove " - Web APIs | MDN" suffix)
        title = re.sub(r'\s*[-|].*MDN.*$', '', title)
        title = re.sub(r'\s*[-|]\s*Web APIs.*$', '', title)

        # Clean the markdown content
        markdown_content = clean_markdown(markdown_content, title)

        # Build file content with frontmatter
        content = f"""---
title: "{title}"
url: "{url}"
crawled_at: "{datetime.now().isoformat()}"
---

# {title}

{markdown_content}
"""

        # Determine output file path
        if file_path == "Web_Animations_API":
            out_path = output_dir / "Web_Animations_API.md"
            index_entries['main'].append((title, "Web_Animations_API.md"))
        elif file_path.startswith("guides/"):
            name = file_path.replace("guides/", "")
            out_path = output_dir / "guides" / f"{name}.md"
            index_entries['guides'].append((title, f"guides/{name}.md"))
        elif file_path.startswith("interfaces/"):
            parts = file_path.replace("interfaces/", "").split("/")
            interface_name = parts[0]
            page_name = parts[1] if len(parts) > 1 else "index"
            out_path = output_dir / "interfaces" / interface_name / f"{page_name}.md"

            if interface_name not in index_entries['interfaces']:
                index_entries['interfaces'][interface_name] = []
            index_entries['interfaces'][interface_name].append(
                (title, f"interfaces/{interface_name}/{page_name}.md")
            )
        elif file_path.startswith("extensions/"):
            name = file_path.replace("extensions/", "")
            out_path = output_dir / "extensions" / f"{name}.md"
            index_entries['extensions'].append((title, f"extensions/{name}.md"))
        else:
            # Fallback
            safe_name = file_path.replace("/", "_")
            out_path = output_dir / f"{safe_name}.md"

        out_path.write_text(content, encoding='utf-8')
        files_written += 1
        print(f"  Written: {out_path.relative_to(output_dir)}")

    # Generate index.md
    generate_index(output_dir, index_entries)
    files_written += 1

    print(f"  Total files written: {files_written}")
    return files_written


def generate_index(output_dir: Path, entries: dict):
    """Generate index.md with table of contents."""

    content = """---
title: "MDN Web Animations API Documentation"
generated_at: "{date}"
---

# MDN Web Animations API Documentation

This documentation was extracted from the Mozilla Developer Network (MDN).

## Table of Contents

""".format(date=datetime.now().isoformat())

    # Main page
    if entries['main']:
        content += "### Overview\n\n"
        for title, path in entries['main']:
            content += f"- [{title}]({path})\n"
        content += "\n"

    # Guides
    if entries['guides']:
        content += "### Guides\n\n"
        for title, path in sorted(entries['guides']):
            content += f"- [{title}]({path})\n"
        content += "\n"

    # Interfaces
    if entries['interfaces']:
        content += "### Interfaces\n\n"
        for interface_name in sorted(entries['interfaces'].keys()):
            pages = entries['interfaces'][interface_name]
            content += f"#### {interface_name}\n\n"
            for title, path in sorted(pages, key=lambda x: (x[1] != f"interfaces/{interface_name}/index.md", x[0])):
                content += f"- [{title}]({path})\n"
            content += "\n"

    # Extensions
    if entries['extensions']:
        content += "### Document and Element Extensions\n\n"
        for title, path in sorted(entries['extensions']):
            content += f"- [{title}]({path})\n"
        content += "\n"

    (output_dir / "index.md").write_text(content, encoding='utf-8')
    print(f"  Written: index.md")


async def main():
    parser = argparse.ArgumentParser(
        description="Crawl MDN Web Animations API documentation to markdown files"
    )
    parser.add_argument(
        "--language", "-l",
        default="en-US",
        choices=["en-US", "fr", "es", "de", "ja", "ko", "pt-BR", "ru", "zh-CN", "zh-TW"],
        help="MDN language (default: en-US)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="./mdn_waapi_docs",
        help="Output directory for markdown files (default: ./mdn_waapi_docs)"
    )
    parser.add_argument(
        "--max-concurrent", "-c",
        type=int,
        default=5,
        help="Maximum concurrent crawls (default: 5)"
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

    args = parser.parse_args()

    print("=" * 60)
    print("MDN Web Animations API Documentation Crawler")
    print("=" * 60)
    print(f"Language: {args.language}")
    print(f"Output: {args.output_dir}")
    print(f"Max concurrent: {args.max_concurrent}")
    print("=" * 60)

    # Phase 1: Discover URLs
    if args.skip_discovery:
        known_urls = build_urls(args.language)
        urls = set(known_urls.values())
        print(f"\nUsing {len(urls)} known URLs (discovery skipped)")
    else:
        urls = await discover_urls(args.language, args.max_concurrent)

    if args.discover_only:
        print(f"\n{'=' * 60}")
        print(f"Discovered {len(urls)} URLs:")
        print("=" * 60)
        for url in sorted(urls):
            print(f"  {url}")
        print(f"\nTotal: {len(urls)} URLs")
        return

    # Phase 2: Crawl pages
    results = await crawl_pages(list(urls), args.max_concurrent)

    # Phase 3: Generate files
    output_dir = Path(args.output_dir)
    files_written = generate_markdown_files(results, output_dir, args.language)

    print(f"\n{'=' * 60}")
    print("Crawl Complete!")
    print("=" * 60)
    print(f"URLs discovered: {len(urls)}")
    print(f"Pages crawled: {len(results)}")
    print(f"Files written: {files_written}")
    print(f"Output directory: {output_dir.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
