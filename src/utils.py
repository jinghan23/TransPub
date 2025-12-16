#!/usr/bin/env python3
"""
Shared utility functions for chapter extraction.
"""

import re


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


def clean_html_text(html_content: str) -> str:
    """
    Clean HTML content to extract plain text.

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

    # Get text and clean up whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text
