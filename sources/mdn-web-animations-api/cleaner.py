"""
MDN Web Animations API markdown cleaner.

Handles MDN-specific content patterns and formatting.
"""

import re
from crawl4ai_toolkit.cleaner import CleanerBase


class MDNWebAnimationsAPICleaner(CleanerBase):
    """
    Cleaner for MDN Web Animations API documentation content.

    Removes MDN-specific elements like browser compatibility tables,
    specification links, and other non-essential content.
    """

    def clean(self, content: str, title: str = "") -> str:
        """Apply MDN-specific cleaning."""
        # Apply base cleaning first
        content = super().clean(content, title)

        # Remove duplicated H1 heading (already in frontmatter)
        content = self.remove_first_h1(content)

        # Remove MDN UI elements
        content = self.remove_baseline_banner(content)
        content = self.remove_help_improve_mdn(content)

        # Remove MDN-specific sections
        content = self.remove_specifications_section(content)
        content = self.remove_browser_compatibility_section(content)
        content = self.remove_see_also_links(content)

        # Clean up MDN badges and notes
        content = self.clean_mdn_badges(content)

        # HIGH PRIORITY: Remove incomplete code example sections
        content = self.remove_orphaned_code_example_headings(content)
        content = self.remove_orphaned_code_intro_lines(content)

        # MEDIUM PRIORITY: Fix formatting and remove boilerplate
        content = self.fix_inline_code_internal_spacing(content)
        content = self.fix_missing_spaces_around_inline_code(content)
        content = self.remove_meta_description_boilerplate(content)
        content = self.remove_tangential_external_links(content)

        # LOW PRIORITY: Normalize formatting
        content = self.normalize_definition_list_spacing(content)
        content = self.fix_link_internal_spacing(content)

        # Fix formatting issues (existing rules)
        # NOTE: fix_missing_spaces_after_inline_code removed - it incorrectly
        # matches across multiple code blocks. fix_missing_spaces_around_inline_code
        # handles this more safely.
        content = self.fix_missing_spaces_before_links(content)
        content = self.fix_escaped_parentheses_in_links(content)
        content = self.fix_link_title_escaping(content)
        content = self.fix_read_only_formatting(content)
        content = self.fix_inheritance_statement_formatting(content)

        # Remove inheritance chain badges (the EventTarget -> Animation style blocks)
        content = self.remove_inheritance_chain_badges(content)

        return content

    def remove_baseline_banner(self, content: str) -> str:
        """
        Remove MDN Baseline/Compatibility banners.

        Handles multiple banner formats:
        - "Baseline Widely available" with description and bullet points
        - "Baseline Widely available *" with asterisk notes
        - "Limited availability" with description and bullet points
        """
        # Pattern for "Baseline Widely available" banners (with optional asterisk notes)
        # Matches from "Baseline" through all the bullet points ending with feedback link
        baseline_pattern = (
            r'^Baseline\s+Widely available\s*\*?\s*\n'  # Header line
            r'(?:This feature is well established.*?\n)?'  # Optional description
            r'(?:\*\s+Some parts of this feature.*?\n)?'  # Optional asterisk note
            r'(?:\s*\*\s*\[.*?\]\(.*?\)\n)*'  # Bullet points with links
        )
        content = re.sub(baseline_pattern, '', content, flags=re.MULTILINE)

        # Pattern for "Limited availability" banners
        limited_pattern = (
            r'^Limited availability\s*\n'  # Header line
            r'(?:This feature is not Baseline.*?\n)?'  # Optional description
            r'(?:\s*\*\s*\[.*?\]\(.*?\)\n)*'  # Bullet points with links
        )
        content = re.sub(limited_pattern, '', content, flags=re.MULTILINE)

        return content

    def remove_help_improve_mdn(self, content: str) -> str:
        """
        Remove the "Help improve MDN" footer section.

        This includes:
        - ## Help improve MDN heading
        - "Learn how to contribute" link
        - "This page was last modified on..." text
        - "View this page on GitHub" and "Report a problem" links
        """
        # Remove the entire section from "## Help improve MDN" to end of content
        pattern = r'^## Help improve MDN\s*\n.*'
        content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        return content.rstrip()

    def remove_specifications_section(self, content: str) -> str:
        """Remove the Specifications section."""
        return self.remove_section(content, "Specifications", 2)

    def remove_browser_compatibility_section(self, content: str) -> str:
        """Remove the Browser compatibility section."""
        return self.remove_section(content, "Browser compatibility", 2)

    def remove_see_also_links(self, content: str) -> str:
        """Remove the See also section."""
        return self.remove_section(content, "See also", 2)

    def clean_mdn_badges(self, content: str) -> str:
        """Remove or clean MDN-specific badges like Experimental, Deprecated, etc."""
        # Remove experimental/deprecated badge markers
        content = re.sub(r'\*\*Experimental\*\*:?\s*', '', content)
        content = re.sub(r'\*\*Deprecated\*\*:?\s*', '', content)
        content = re.sub(r'\*\*Non-standard\*\*:?\s*', '', content)
        return content

    def fix_missing_spaces_after_inline_code(self, content: str) -> str:
        """
        Add missing spaces after bold inline code.

        Fixes patterns like:
        - `**`Animation`**interface` -> `**`Animation`** interface`
        - `**`code`**text` -> `**`code`** text`

        Also handles non-bold inline code followed directly by letters.
        """
        # Fix bold inline code followed directly by a letter
        # Pattern: **`code`**letter -> **`code`** letter
        # Use [^`\n]+ to avoid matching across lines
        content = re.sub(r'(\*\*`[^`\n]+`\*\*)([a-zA-Z])', r'\1 \2', content)

        # Fix plain inline code followed directly by a letter (non-bold)
        # Pattern: `code`letter -> `code` letter
        # Use [^`\n]+ to avoid matching across lines
        # But don't add space if already has space, or if followed by punctuation
        content = re.sub(r'(`[^`\n]+`)([a-zA-Z])', r'\1 \2', content)

        return content

    def fix_missing_spaces_before_links(self, content: str) -> str:
        """
        Add missing spaces before links that follow text directly.

        Fixes patterns like:
        - `the[link]` -> `the [link]`
        - `of the[Web Animations API]` -> `of the [Web Animations API]`

        Does NOT modify:
        - `**`code`**` patterns (bold inline code)
        """
        # Add space before [ when preceded by a letter
        # But not when it's part of `]` pattern (end of previous link or code)
        content = re.sub(r'([a-zA-Z])\[', r'\1 [', content)
        return content

    def fix_escaped_parentheses_in_links(self, content: str) -> str:
        """
        Fix escaped parentheses in link tooltips/titles.

        Fixes patterns like:
        - `"Animation\\(\\)"` -> `"Animation()"`
        - Link titles with `\\(` and `\\)` -> `(` and `)`
        """
        # Fix escaped parentheses in link titles (inside quotes after URLs)
        # Pattern: "SomeText\(\)" -> "SomeText()"
        content = re.sub(r'\\?\(\\?\)', '()', content)

        return content

    def fix_link_title_escaping(self, content: str) -> str:
        """
        Clean unnecessary escaping in link titles.

        Fixes patterns like:
        - `\\(Opens in a new tab\\)` -> `(Opens in a new tab)`
        """
        # Fix escaped parentheses in "Opens in a new tab" and similar phrases
        content = re.sub(r'\\?\(Opens in a new tab\\?\)', '(Opens in a new tab)', content)

        # More general fix for any escaped parentheses in quoted strings (link titles)
        # This handles cases like: "title \(text\)" -> "title (text)"
        def fix_title_escaping(match):
            title = match.group(1)
            # Unescape parentheses within the title
            title = title.replace(r'\(', '(').replace(r'\)', ')')
            return f'"{title}"'

        # Match quoted strings that may contain escaped parentheses
        content = re.sub(r'"([^"]*\\[()][^"]*)"', fix_title_escaping, content)

        return content

    def fix_read_only_formatting(self, content: str) -> str:
        """
        Ensure consistent spacing around "Read only" property indicators.

        Normalizes various formats to consistent spacing:
        - `property Read only` with proper spacing
        """
        # Normalize "Read only" with various spacing issues
        # Ensure there's a space before "Read only"
        content = re.sub(r'(\S)(Read only)', r'\1 \2', content)

        # Ensure there's proper spacing after "Read only" before newline
        content = re.sub(r'(Read only)\s*\n', r'\1\n', content)

        return content

    def fix_inheritance_statement_formatting(self, content: str) -> str:
        """
        Fix spacing in inheritance statements.

        Fixes patterns like:
        - `parent,[` -> `parent, [`
        - Ensures proper comma-space before links
        """
        # Add space after comma when followed directly by [
        content = re.sub(r',\[', ', [', content)

        # Add space after comma when followed directly by backtick
        content = re.sub(r',`', ', `', content)

        return content

    def remove_inheritance_chain_badges(self, content: str) -> str:
        """
        Remove the inheritance chain badges that appear as linked items.

        These appear as lines like:
        [ EventTarget  ](url)[ Animation  ](url)
        """
        # Pattern to match lines with consecutive badge-style links
        # These are usually interface inheritance chains
        pattern = r'^\s*(?:\[\s*\w+\s*\]\([^)]+\)\s*)+\s*$\n?'
        content = re.sub(pattern, '', content, flags=re.MULTILINE)

        return content

    # =========================================================================
    # HIGH PRIORITY CLEANING RULES
    # =========================================================================

    def remove_orphaned_code_example_headings(self, content: str) -> str:
        """
        Remove orphaned code example headings (HTML, CSS, JavaScript, Result).

        These are level 4 headings that should precede code blocks but
        sometimes appear without content (the code block was not extracted).

        Removes patterns like:
        - "#### HTML" followed immediately by another heading or end of section
        - Multiple consecutive orphaned headings like "#### HTML\\n#### CSS\\n#### JavaScript\\n#### Result"
        - "#### Result" followed by text (not a code block) - the live demo can't be shown
        """
        # First, remove consecutive orphaned headings (most common case)
        # Match 2+ consecutive code example headings with only whitespace between
        consecutive_pattern = r'(?:^#### (?:HTML|CSS|JavaScript|Result)\s*\n)+(?=^#{1,4} |\Z)'
        content = re.sub(consecutive_pattern, '', content, flags=re.MULTILINE)

        # Then, remove single orphaned headings followed by another heading or EOF
        # Match a code example heading followed by another heading (not a code block)
        single_pattern = r'^#### (?:HTML|CSS|JavaScript|Result)\s*\n(?=^#{1,4} |\Z)'
        content = re.sub(single_pattern, '', content, flags=re.MULTILINE)

        # Remove "#### Result" when followed by regular text (not a code block)
        # The live demo/result can't be rendered in markdown, so the heading is meaningless
        # Pattern: #### Result followed by a line that doesn't start with ``` or #
        result_with_text_pattern = r'^#### Result\s*\n(?=(?!```|#{1,4} )[^\n])'
        content = re.sub(result_with_text_pattern, '', content, flags=re.MULTILINE)

        return content

    def remove_orphaned_code_intro_lines(self, content: str) -> str:
        """
        Remove lines that introduce code examples but have no following code block.

        These are typically lines ending with a colon that describe code but
        the code block was not extracted. Removes patterns like:
        - "The HTML for the example is shown below."
        - "The CSS for the example looks like this:"

        Only removes these if they appear right before a heading or end of content.
        """
        # Pattern matches common intro phrases followed by heading or EOF
        # These phrases typically precede code blocks that weren't extracted
        intro_patterns = [
            r'^The HTML for the example is shown below\.\s*\n(?=^#{1,4} |\Z)',
            r'^The CSS for the example (?:is|looks like)[^.\n]*\.\s*\n(?=^#{1,4} |\Z)',
            r'^The JavaScript for the example[^.\n]*\.\s*\n(?=^#{1,4} |\Z)',
        ]

        for pattern in intro_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)

        return content

    # =========================================================================
    # MEDIUM PRIORITY CLEANING RULES
    # =========================================================================

    def fix_inline_code_internal_spacing(self, content: str) -> str:
        """
        Fix extra spaces inside inline code backticks.

        Normalizes patterns like:
        - ` variable` -> `variable` (leading space)
        - `variable ` -> `variable` (trailing space)
        - ` variable ` -> `variable` (both)

        Only matches single code spans (content has no spaces or backticks).
        """
        # Fix leading space: ` text` -> `text`
        # Content: no spaces or backticks (single identifier/value)
        content = re.sub(r'(?<!`)` ([^\s`]+)`(?!`)', r'`\1`', content)

        # Fix trailing space: `text ` -> `text`
        content = re.sub(r'(?<!`)`([^\s`]+) `(?!`)', r'`\1`', content)

        # Fix both: ` text ` -> `text`
        content = re.sub(r'(?<!`)` ([^\s`]+) `(?!`)', r'`\1`', content)

        return content

    def fix_missing_spaces_around_inline_code(self, content: str) -> str:
        """
        Add missing spaces around inline code backticks.

        Fixes patterns like:
        - word`code` -> word `code` (missing space before)
        - `code`word -> `code` word (missing space after)

        Only handles simple inline code (variable names, short values) to avoid
        accidentally matching across multiple code blocks or markdown links.
        """
        # Match simple inline code: alphanumeric, dots, dashes, underscores, colons, quotes
        # Excludes: brackets, parens, commas to avoid matching markdown link syntax
        simple_code = r'`[a-zA-Z0-9_.:\-<>"\']+`'

        # Add space before inline code when preceded by a letter
        content = re.sub(rf'([a-zA-Z])({simple_code})', r'\1 \2', content)

        # Add space after inline code when followed by a letter
        content = re.sub(rf'({simple_code})([a-zA-Z])', r'\1 \2', content)

        return content

    def remove_meta_description_boilerplate(self, content: str) -> str:
        """
        Remove meta-description boilerplate text.

        Removes patterns like:
        - "_In addition to the properties listed below, properties from the parent interface, [Event](...), are available._"
        """
        # Match the italicized inheritance boilerplate
        pattern = r'^_In addition to the properties listed below[^_\n]*_\s*\n?'
        content = re.sub(pattern, '', content, flags=re.MULTILINE)

        return content

    def remove_tangential_external_links(self, content: str) -> str:
        """
        Remove or simplify tangential external MDN links to CSS/HTML properties.

        In API documentation, inline links to CSS properties or HTML elements
        can be distracting. This converts full external links to just the text.

        Converts patterns like:
        - [animation-range](https://developer.mozilla.org/en-US/docs/Web/CSS/...) -> `animation-range`
        - [<div>](https://developer.mozilla.org/en-US/docs/Web/HTML/...) -> `<div>`

        Preserves internal relative links and non-MDN CSS/HTML links.
        """
        # Convert external MDN CSS property links to inline code
        # [property-name](https://developer.mozilla.org/en-US/docs/Web/CSS/...)
        content = re.sub(
            r'\[`?([^`\]\[]+)`?\]\(https://developer\.mozilla\.org/[^)]*?/docs/Web/CSS/[^)]+\)',
            r'`\1`',
            content
        )

        # Convert external MDN HTML element links to inline code
        # [<element>](https://developer.mozilla.org/en-US/docs/Web/HTML/...)
        content = re.sub(
            r'\[`?([^`\]\[]+)`?\]\(https://developer\.mozilla\.org/[^)]*?/docs/Web/HTML/[^)]+\)',
            r'`\1`',
            content
        )

        return content

    # =========================================================================
    # LOW PRIORITY CLEANING RULES
    # =========================================================================

    def normalize_definition_list_spacing(self, content: str) -> str:
        """
        Normalize spacing between definition list items.

        Ensures consistent blank line separation between list items
        in MDN-style definition lists (term on one line, description indented below).
        """
        # MDN definition lists have the format:
        # [term](link)
        #     Description text.
        #
        # Ensure single blank line between items
        # Pattern: description followed by term (link line starting with [)
        content = re.sub(
            r'(\n    [^\n]+)\n{2,}(\[`?[^\]]+`?\]\([^)]+\))',
            r'\1\n\n\2',
            content
        )

        return content

    def fix_link_internal_spacing(self, content: str) -> str:
        """
        Fix extra spaces inside link brackets.

        Normalizes patterns like:
        - [` element`] -> [`element`]
        - [ text ] -> [text]
        """
        # Fix leading space in link text: [` text`] -> [`text`]
        content = re.sub(r'\[\s*`\s*([^`\]]+)`\s*\]', r'[`\1`]', content)

        # Fix general leading/trailing spaces in link text: [ text ] -> [text]
        content = re.sub(r'\[\s+([^\]\[]+?)\s+\]', r'[\1]', content)

        return content
