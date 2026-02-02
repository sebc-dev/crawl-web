"""
Base markdown cleaning utilities.

Provides common cleaning functions and a base class for
source-specific cleaners to extend.
"""

import re
from typing import Optional


def clean_heading_anchors(content: str) -> str:
    """
    Remove anchor links from markdown headings.

    Transforms: ## [Title](url) -> ## Title
    """
    lines = content.split('\n')
    cleaned_lines = []

    for line in lines:
        # Match headings with anchor links: ## [Title](url)
        heading_match = re.match(r'^(#{1,6})\s+\[([^\]]+)\]\([^)]+\)\s*$', line)
        if heading_match:
            level = heading_match.group(1)
            heading_text = heading_match.group(2)
            cleaned_lines.append(f"{level} {heading_text}")
        else:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def clean_excessive_whitespace(content: str) -> str:
    """
    Reduce multiple consecutive blank lines to maximum of two.
    Also strips leading/trailing whitespace.
    """
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


class CleanerBase:
    """
    Base class for markdown content cleaners.

    Provides common cleaning methods that can be extended
    for source-specific cleaning needs.

    Usage:
        class MyCleaner(CleanerBase):
            def clean(self, content: str, title: str = "") -> str:
                content = super().clean(content, title)
                # Add custom cleaning here
                return content
    """

    def clean(self, content: str, title: str = "") -> str:
        """
        Apply base cleaning operations.

        Override this method in subclasses to add custom cleaning,
        calling super().clean() first to apply base cleaning.

        Args:
            content: Raw markdown content
            title: Optional page title for context

        Returns:
            Cleaned markdown content
        """
        content = clean_heading_anchors(content)
        content = clean_excessive_whitespace(content)
        return content

    def remove_section(self, content: str, heading: str, heading_level: int = 2) -> str:
        """
        Remove a section starting with the given heading.

        Args:
            content: Markdown content
            heading: The heading text to match (without #)
            heading_level: The heading level (1-6)

        Returns:
            Content with the section removed
        """
        pattern = rf'^{"#" * heading_level}\s+{re.escape(heading)}.*?(?=^{"#" * heading_level}\s|\Z)'
        return re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)

    def remove_first_h1(self, content: str) -> str:
        """
        Remove the first H1 heading (often duplicated with frontmatter title).
        """
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# '):
                lines.pop(i)
                break
        return '\n'.join(lines)

    def remove_lines_containing(self, content: str, text: str) -> str:
        """
        Remove all lines containing the specified text.
        """
        lines = content.split('\n')
        return '\n'.join(line for line in lines if text not in line)

    def remove_block_until_heading(
        self,
        content: str,
        start_marker: str,
        end_pattern: Optional[str] = None
    ) -> str:
        """
        Remove a block starting with a marker until the next heading or end pattern.

        Args:
            content: Markdown content
            start_marker: Text that marks the start of the block
            end_pattern: Optional regex pattern for block end (defaults to next heading)

        Returns:
            Content with the block removed
        """
        lines = content.split('\n')
        cleaned_lines = []
        in_block = False

        for line in lines:
            if start_marker in line:
                in_block = True
                continue

            if in_block:
                # Check for end of block
                if end_pattern and re.search(end_pattern, line):
                    in_block = False
                elif line.startswith('#') or (line.strip() and not line.startswith(' ')):
                    in_block = False
                else:
                    continue

            if not in_block:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)
