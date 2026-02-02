"""
State management for tracking crawl changes.

Provides functionality to detect if pages have changed since the last crawl,
using a multi-level strategy: HTTP headers (ETag/Last-Modified) first,
then content hash as fallback.
"""

import json
import hashlib
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, asdict


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of content.

    Args:
        content: The content to hash

    Returns:
        Hash string in format "sha256:<first 16 chars of hex digest>"
    """
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:16]}"


@dataclass
class ChangeResult:
    """Result of checking if a page has changed."""
    url: str
    file_path: str
    status: str  # 'unchanged', 'changed', 'new', 'removed'
    reason: str  # 'etag', 'last_modified', 'content_hash', 'new_page', 'missing_file', 'local_modified'

    def to_dict(self) -> dict:
        return asdict(self)


class CrawlState:
    """
    Manages crawl state for a source.

    Stores metadata about crawled pages including content hashes and
    HTTP headers for change detection.
    """

    def __init__(self, source_dir: Path):
        """
        Initialize CrawlState for a source directory.

        Args:
            source_dir: Path to the source directory (e.g., sources/mdn-web-animations-api)
        """
        self.source_dir = source_dir
        self.state_file = source_dir / ".crawl-state.json"
        self.state = self._load()

    def _load(self) -> dict:
        """Load state from file or return empty state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"  Warning: Could not load state file: {e}")
                return self._empty_state()
        return self._empty_state()

    def _empty_state(self) -> dict:
        """Return an empty state structure."""
        return {
            "source": self.source_dir.name,
            "last_crawl": None,
            "supports_etag": False,
            "supports_last_modified": False,
            "pages": {}
        }

    def save(self) -> None:
        """Save state to file."""
        self.state["last_crawl"] = datetime.now().isoformat()
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def get_page(self, file_path: str) -> Optional[dict]:
        """
        Get saved state for a page.

        Args:
            file_path: Relative file path (without .md extension)

        Returns:
            Page state dict or None if not found
        """
        return self.state.get("pages", {}).get(file_path)

    def set_page(
        self,
        file_path: str,
        url: str,
        content_hash: str,
        title: str = "",
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> None:
        """
        Save state for a page.

        Args:
            file_path: Relative file path (without .md extension)
            url: Page URL
            content_hash: SHA256 hash of content
            title: Page title
            etag: ETag header value
            last_modified: Last-Modified header value
        """
        if "pages" not in self.state:
            self.state["pages"] = {}

        self.state["pages"][file_path] = {
            "url": url,
            "content_hash": content_hash,
            "title": title,
            "crawled_at": datetime.now().isoformat(),
        }

        if etag:
            self.state["pages"][file_path]["etag"] = etag
            self.state["supports_etag"] = True

        if last_modified:
            self.state["pages"][file_path]["last_modified"] = last_modified
            self.state["supports_last_modified"] = True

    def remove_page(self, file_path: str) -> None:
        """Remove a page from state."""
        if "pages" in self.state and file_path in self.state["pages"]:
            del self.state["pages"][file_path]

    def get_all_pages(self) -> Dict[str, dict]:
        """Get all pages in state."""
        return self.state.get("pages", {})

    def get_last_crawl(self) -> Optional[str]:
        """Get timestamp of last crawl."""
        return self.state.get("last_crawl")

    @property
    def page_count(self) -> int:
        """Get number of pages in state."""
        return len(self.state.get("pages", {}))


async def check_headers(url: str, timeout: int = 10) -> dict:
    """
    Make HEAD request to get ETag/Last-Modified headers.

    Args:
        url: URL to check
        timeout: Request timeout in seconds

    Returns:
        Dict with 'etag', 'last_modified', 'status' keys
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(
                url,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                return {
                    'etag': resp.headers.get('ETag'),
                    'last_modified': resp.headers.get('Last-Modified'),
                    'status': resp.status
                }
    except Exception as e:
        return {
            'etag': None,
            'last_modified': None,
            'status': None,
            'error': str(e)
        }


async def check_page_changed(
    url: str,
    file_path: str,
    saved_state: Optional[dict],
    crawler_func: Optional[Callable] = None,
) -> ChangeResult:
    """
    Check if a page has changed using multi-level strategy.

    Strategy:
    1. Try ETag/Last-Modified (HEAD request) - fastest
    2. Fallback to content hash (requires full crawl)

    Args:
        url: Page URL
        file_path: Relative file path
        saved_state: Previously saved state for this page
        crawler_func: Optional async function to crawl page for content hash comparison

    Returns:
        ChangeResult indicating if page changed
    """
    # New page - no previous state
    if saved_state is None:
        return ChangeResult(url, file_path, 'new', 'new_page')

    # Level 1: Check HTTP headers
    headers = await check_headers(url)

    # Check ETag
    if headers.get('etag') and saved_state.get('etag'):
        if headers['etag'] == saved_state['etag']:
            return ChangeResult(url, file_path, 'unchanged', 'etag')

    # Check Last-Modified
    if headers.get('last_modified') and saved_state.get('last_modified'):
        if headers['last_modified'] == saved_state['last_modified']:
            return ChangeResult(url, file_path, 'unchanged', 'last_modified')

    # Level 2: Content hash (requires full crawl)
    if crawler_func:
        result = await crawler_func(url)
        if result and result.get('markdown'):
            new_hash = compute_content_hash(result['markdown'])
            if new_hash == saved_state.get('content_hash'):
                return ChangeResult(url, file_path, 'unchanged', 'content_hash')
            return ChangeResult(url, file_path, 'changed', 'content_hash')

    # If we can't verify via content hash and headers changed/missing
    return ChangeResult(url, file_path, 'changed', 'content_hash')


def check_local_file(
    output_dir: Path,
    file_path: str,
    saved_state: dict,
) -> ChangeResult:
    """
    Check if a local file has been modified since crawl.

    Args:
        output_dir: Output directory path
        file_path: Relative file path (without .md extension)
        saved_state: Saved state for this page

    Returns:
        ChangeResult indicating local file status
    """
    url = saved_state.get('url', '')
    full_path = output_dir / f"{file_path}.md"

    if not full_path.exists():
        return ChangeResult(url, file_path, 'removed', 'missing_file')

    # Read file and compute hash
    try:
        content = full_path.read_text(encoding='utf-8')

        # Extract markdown content after frontmatter for hashing
        # The hash should be of the markdown content, not the full file with frontmatter
        if content.startswith('---'):
            # Find end of frontmatter
            end_idx = content.find('---', 3)
            if end_idx != -1:
                # Skip frontmatter and the following newlines
                content_start = content.find('\n', end_idx + 3)
                if content_start != -1:
                    markdown_content = content[content_start:].strip()
                else:
                    markdown_content = content
            else:
                markdown_content = content
        else:
            markdown_content = content

        current_hash = compute_content_hash(markdown_content)

        if current_hash == saved_state.get('content_hash'):
            return ChangeResult(url, file_path, 'unchanged', 'content_hash')
        else:
            return ChangeResult(url, file_path, 'changed', 'local_modified')

    except IOError as e:
        return ChangeResult(url, file_path, 'removed', f'read_error: {e}')


def print_change_report(
    results: List[ChangeResult],
    source_name: str,
    last_crawl: Optional[str],
    is_remote: bool = False,
) -> None:
    """
    Print a formatted change report.

    Args:
        results: List of ChangeResult objects
        source_name: Name of the source
        last_crawl: Timestamp of last crawl
        is_remote: Whether this is a remote check
    """
    # Categorize results
    unchanged = [r for r in results if r.status == 'unchanged']
    changed = [r for r in results if r.status == 'changed']
    new_pages = [r for r in results if r.status == 'new']
    removed = [r for r in results if r.status == 'removed']

    check_type = "remote changes" if is_remote else "local files"
    print(f"\nChecking {check_type} for {source_name}...")

    if last_crawl:
        print(f"Last crawl: {last_crawl}")

    print(f"\nTotal files: {len(results)}")
    print(f"  - {len(unchanged)} unchanged")
    print(f"  - {len(changed)} {'changed' if is_remote else 'modified locally'}")
    print(f"  - {len(new_pages)} new")
    print(f"  - {len(removed)} removed")

    if changed:
        print(f"\n{'Changed' if is_remote else 'Modified'} pages:")
        for r in changed:
            print(f"  - {r.file_path}.md ({r.reason})")

    if new_pages:
        print("\nNew pages:")
        for r in new_pages:
            print(f"  - {r.file_path}.md")

    if removed:
        print("\nRemoved pages:")
        for r in removed:
            print(f"  - {r.file_path}.md")

    if is_remote and (changed or new_pages or removed):
        print(f"\nRun 'python crawl.py {source_name}' to update.")
