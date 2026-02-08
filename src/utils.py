#!/usr/bin/env python3
"""
Shared utility functions for chapter extraction.
"""

import logging
import re

logger = logging.getLogger(__name__)


def chinese_to_int(s: str) -> int:
    """Convert Chinese numeral string to integer."""
    if s.isdigit():
        return int(s)

    chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
                    '百': 100, '零': 0}

    if len(s) == 1:
        return chinese_nums.get(s, 0)

    # Handle numbers like 十一, 二十, 二十一
    result = 0
    if '百' in s:
        parts = s.split('百')
        result = chinese_nums.get(parts[0], 1) * 100
        s = parts[1] if len(parts) > 1 else ''

    if '十' in s:
        parts = s.split('十')
        tens = chinese_nums.get(parts[0], 1) if parts[0] else 1
        result += tens * 10
        if len(parts) > 1 and parts[1]:
            result += chinese_nums.get(parts[1], 0)
    elif s:
        for c in s:
            result += chinese_nums.get(c, 0)

    return result


def extract_title_from_lines(lines: list, chapter_line: str) -> str:
    """Extract chapter title from lines following the chapter marker."""
    title_parts = []
    found_chapter = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line == chapter_line:
            found_chapter = True
            # If chapter line contains title (e.g., "Chapter 1: Introduction")
            if ':' in line or '：' in line:
                title = re.split(r'[:：]', line, 1)[1].strip()
                if title:
                    return title
            continue

        if found_chapter:
            # Skip if it's just a number (likely page number)
            if line.isdigit():
                continue
            title_parts.append(line)
            if len(title_parts) >= 2:
                break

    return ' '.join(title_parts) if title_parts else "Untitled"


def _extract_footnotes(soup) -> list:
    """
    Extract footnote reference numbers from HTML and replace them with [N] markers.

    Recognises common EPUB footnote patterns:
      - <sup><a>N</a></sup>
      - <sup>N</sup>  (bare superscript digit)
      - <a epub:type="noteref">
      - <a class="footnote"> / <a class="footnote-ref"> etc.

    Returns:
        List of footnote number strings found (in document order).
    """
    from bs4 import NavigableString

    footnotes = []

    def replace_with_marker(element, num):
        """Replace element with [N] text marker."""
        marker = NavigableString(f'[{num}]')
        element.replace_with(marker)

    # Pattern 1: <a epub:type="noteref"> or <a role="doc-noteref">
    for a_tag in soup.find_all('a', attrs={'epub:type': 'noteref'}):
        num = a_tag.get_text(strip=True)
        if num.isdigit():
            footnotes.append(num)
            parent = a_tag.parent
            if parent and parent.name == 'sup':
                replace_with_marker(parent, num)
            else:
                replace_with_marker(a_tag, num)

    for a_tag in soup.find_all('a', attrs={'role': 'doc-noteref'}):
        num = a_tag.get_text(strip=True)
        if num.isdigit():
            footnotes.append(num)
            parent = a_tag.parent
            if parent and parent.name == 'sup':
                replace_with_marker(parent, num)
            else:
                replace_with_marker(a_tag, num)

    # Pattern 2: <a class="footnote*"> wrapping a digit
    for a_tag in soup.find_all('a', class_=True):
        classes = a_tag.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        if any('footnote' in c.lower() for c in classes):
            num = a_tag.get_text(strip=True)
            if num.isdigit():
                footnotes.append(num)
                parent = a_tag.parent
                if parent and parent.name == 'sup':
                    replace_with_marker(parent, num)
                else:
                    replace_with_marker(a_tag, num)

    # Pattern 3: <sup><a>N</a></sup> where N is a digit
    for sup in soup.find_all('sup'):
        a_child = sup.find('a')
        if a_child:
            num = a_child.get_text(strip=True)
            if num.isdigit():
                footnotes.append(num)
                replace_with_marker(sup, num)

    # Pattern 4: <sup>N</sup> bare superscript digit (no child tags)
    for sup in soup.find_all('sup'):
        if not sup.find():  # no child elements
            num = sup.get_text(strip=True)
            if num.isdigit():
                footnotes.append(num)
                replace_with_marker(sup, num)

    return footnotes


def clean_html_text(html_content: str) -> str:
    """
    Clean HTML content to extract plain text.
    Extracts footnote references and appends them as a Notes section.

    Args:
        html_content: HTML string

    Returns:
        Cleaned plain text
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()

    # Extract footnotes before getting text
    footnotes = _extract_footnotes(soup)

    # Get text and clean up whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    # Footnotes have been removed from inline text.
    # The actual footnote content is typically in a separate "Notes" chapter.
    # We don't append placeholder text here to avoid wasting tokens.

    return text


def parse_notes_chapter(notes_text: str) -> dict:
    """
    Parse a Notes chapter to extract footnotes per chapter.

    Expected format:
        Chapter 1
        1.Footnote text...
        2.Another footnote...
        Chapter 2
        1.First footnote of chapter 2...

    Returns:
        Dict mapping chapter_num (int) -> {footnote_num (int) -> content (str)}
    """
    notes_by_chapter = {}
    current_chapter = None
    current_footnotes = {}

    lines = notes_text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for "Chapter N" header
        chapter_match = re.match(r'^Chapter\s+(\d+)\s*$', line, re.IGNORECASE)
        if chapter_match:
            # Save previous chapter's footnotes
            if current_chapter is not None and current_footnotes:
                notes_by_chapter[current_chapter] = current_footnotes
            current_chapter = int(chapter_match.group(1))
            current_footnotes = {}
            continue

        # Check for footnote line "N.Text..." or "N. Text..."
        footnote_match = re.match(r'^(\d+)\.\s*(.*)$', line)
        if footnote_match and current_chapter is not None:
            fn_num = int(footnote_match.group(1))
            fn_text = footnote_match.group(2).strip()
            current_footnotes[fn_num] = fn_text
            continue

    # Save last chapter's footnotes
    if current_chapter is not None and current_footnotes:
        notes_by_chapter[current_chapter] = current_footnotes

    return notes_by_chapter


def clean_html_text_with_footnotes(html_content: str, chapter_footnotes: dict = None) -> str:
    """
    Clean HTML content and append actual footnote content.

    Args:
        html_content: HTML string
        chapter_footnotes: Dict mapping footnote_num -> content (optional)

    Returns:
        Cleaned plain text with footnotes appended
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()

    # Extract footnote numbers before getting text
    footnote_nums = _extract_footnotes(soup)

    # Get text and clean up whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    # Append actual footnote content if available
    if chapter_footnotes and footnote_nums:
        notes_lines = []
        for num_str in footnote_nums:
            num = int(num_str)
            if num in chapter_footnotes:
                notes_lines.append(f"[{num}] {chapter_footnotes[num]}")

        if notes_lines:
            text += "\n\n## Notes\n\n" + "\n\n".join(notes_lines)

    return text


def classify_chapter_type(title: str) -> str:
    """
    Classify a chapter as front_matter, main_content, or back_matter.

    Args:
        title: The chapter title

    Returns:
        One of: "front_matter", "main_content", "back_matter"
    """
    title_lower = title.lower().strip()

    # Front matter patterns
    front_matter_keywords = [
        'title page', 'half title', 'cover',
        'copyright', 'legal',
        'contents', 'table of contents', 'toc',
        'dedication', 'epigraph',
        'preface', 'foreword',
        'about the author', 'about the publisher',
        'praise', 'endorsements', 'reviews',
        'also by',
    ]

    # Back matter patterns
    back_matter_keywords = [
        'notes', 'endnotes', 'footnotes',
        'references', 'bibliography', 'works cited', 'sources',
        'index', 'indices',
        'appendix', 'appendices',
        'glossary',
        'acknowledgment', 'acknowledgement',
        'afterword', 'epilogue', 'postscript',
        'about the author',  # can appear at end too
        'credits',
    ]

    # Check front matter
    for keyword in front_matter_keywords:
        if keyword in title_lower:
            return "front_matter"

    # Check back matter
    for keyword in back_matter_keywords:
        if keyword in title_lower:
            return "back_matter"

    # Check for numbered chapters (main content)
    # Patterns: "1. Title", "Chapter 1", "1: Title", just "1"
    if re.match(r'^\d+[\.\:\s]', title_lower) or re.match(r'^chapter\s+\d+', title_lower):
        return "main_content"

    # Check for "Introduction" - could be front or main, treat as main if standalone
    if title_lower in ['introduction', 'intro']:
        return "main_content"

    # Default to main_content for unrecognized titles
    return "main_content"


def check_truncation(response, input_text: str, task: str) -> bool:
    """
    Detect whether an LLM response was truncated.

    Uses three layers:
      1. finish_reason == "length" (most reliable)
      2. Output/input length ratio below threshold
      3. Missing terminal punctuation (combined with low ratio only)

    Args:
        response: The raw OpenAI API response object.
        input_text: The original input text sent to the model.
        task: One of "translate" or "preprocess".

    Returns:
        True if the response appears truncated.
    """
    choice = response.choices[0]

    # Layer 1: finish_reason
    if choice.finish_reason == "length":
        logger.warning("Truncation detected: finish_reason='length' (%s)", task)
        return True

    output_text = choice.message.content.strip()
    if not output_text or not input_text:
        return False

    # Layer 2: length ratio
    ratio = len(output_text) / len(input_text)
    ratio_threshold = 0.3 if task == "translate" else 0.4
    if ratio < ratio_threshold:
        # Layer 3: combine with missing terminal punctuation
        terminal_chars = set('.!?。！？"\'"\'）)】」』')
        if output_text and output_text[-1] not in terminal_chars:
            logger.warning(
                "Truncation suspected: ratio=%.2f (threshold=%.2f), "
                "no terminal punctuation (%s)",
                ratio, ratio_threshold, task,
            )
            return True

    return False
