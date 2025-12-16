#!/usr/bin/env python3
"""
Extract chapters from PDF using multiple detection strategies:
1. PDF outline/TOC (most reliable)
2. Text pattern matching (fallback)
"""

import re
import fitz  # PyMuPDF - better for TOC extraction
import pdfplumber

# Support both direct execution and module import
try:
    from .utils import chinese_to_int, extract_title_from_lines
except ImportError:
    from utils import chinese_to_int, extract_title_from_lines


def extract_toc_chapters(pdf_path: str) -> list:
    """
    Extract chapter information from PDF's built-in TOC/outline.

    Returns:
        List of tuples: (chapter_number, title, page_index)
    """
    chapters = []

    with fitz.open(pdf_path) as doc:
        toc = doc.get_toc()  # Returns list of [level, title, page]

        if not toc:
            return []

        print(f"Found PDF outline with {len(toc)} entries")

        chapter_num = 0
        for level, title, page in toc:
            # Only use top-level entries (level 1) as chapters
            if level == 1:
                chapter_num += 1
                # page in TOC is 1-indexed, convert to 0-indexed
                page_idx = page - 1 if page > 0 else 0
                chapters.append((chapter_num, title.strip(), page_idx))
                print(f"  Chapter {chapter_num}: '{title.strip()}' (page {page})")

    return chapters


def find_chapter_pages_by_pattern(pdf_path: str, skip_pages: int = 10) -> list:
    """
    Fallback: Find chapters by text pattern matching.
    Supports multiple formats: standalone numbers, "Chapter N", "第N章", etc.

    Returns:
        List of tuples: (chapter_number, title, page_index)
    """
    chapters = []
    seen_chapters = set()

    # Patterns to match chapter headings
    patterns = [
        # "Chapter 1" or "CHAPTER 1"
        (r'^(?:chapter|CHAPTER)\s+(\d+)', lambda m: int(m.group(1))),
        # "第1章" or "第一章"
        (r'^第([一二三四五六七八九十百\d]+)章', lambda m: chinese_to_int(m.group(1))),
        # Standalone number at start (1-99), more strict matching
        (r'^(\d{1,2})\s*$', lambda m: int(m.group(1))),
    ]

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Scanning {len(pdf.pages)} pages for chapter markers...")

        for page_num in range(skip_pages, len(pdf.pages)):
            page = pdf.pages[page_num]
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')

            # Check first 5 non-empty lines for chapter markers
            checked = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                checked += 1
                if checked > 5:
                    break

                for pattern, extractor in patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        chapter_num = extractor(match)
                        if 1 <= chapter_num <= 200 and chapter_num not in seen_chapters:
                            # Extract title from subsequent lines
                            title = extract_title_from_lines(lines, line)
                            chapters.append((chapter_num, title, page_num))
                            seen_chapters.add(chapter_num)
                            print(f"  Found Chapter {chapter_num}: '{title}' (page {page_num + 1})")
                            break
                else:
                    continue
                break

    # Sort by chapter number
    chapters.sort(key=lambda x: x[0])
    return chapters


def find_chapter_pages(pdf_path: str, skip_pages: int = 10) -> list:
    """
    Find chapters using the best available method.

    Returns:
        List of tuples: (chapter_number, title, page_index)
    """
    # Try TOC first (most reliable)
    chapters = extract_toc_chapters(pdf_path)

    if chapters:
        print(f"\nUsing PDF outline (found {len(chapters)} chapters)")
        return chapters

    # Fallback to pattern matching
    print("\nNo PDF outline found, using text pattern matching...")
    chapters = find_chapter_pages_by_pattern(pdf_path, skip_pages)

    if chapters:
        print(f"Found {len(chapters)} chapters via pattern matching")
    else:
        print("Warning: No chapters detected!")

    return chapters


def extract_chapters_pdf(pdf_path: str, output_dir: str, skip_pages: int = 10) -> list:
    """
    Extract chapters from PDF and save as text files.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save chapter files
        skip_pages: Number of pages to skip

    Returns:
        List of chapter metadata dictionaries
    """
    from pathlib import Path

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get chapters as list of (chapter_num, title, page_index)
    chapters = find_chapter_pages(pdf_path, skip_pages)

    if not chapters:
        print("Error: No chapters found!")
        return []

    chapters_meta = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for i, (chapter_num, title, start_page) in enumerate(chapters):
            # Determine end page
            if i + 1 < len(chapters):
                end_page = chapters[i + 1][2]  # page_index of next chapter
            else:
                end_page = total_pages

            # Extract text
            chapter_text = []
            for page_num in range(start_page, end_page):
                if page_num < total_pages:
                    text = pdf.pages[page_num].extract_text()
                    if text:
                        chapter_text.append(text)

            combined_text = "\n\n".join(chapter_text)

            # Skip empty chapters
            if not combined_text.strip():
                print(f"  Skipping Chapter {chapter_num}: '{title}' (empty)")
                continue

            # Save chapter
            chapter_file = output_dir / f"chapter_{chapter_num:02d}.txt"
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(f"{chapter_num}. {title}\n\n")
                f.write(combined_text)

            meta = {
                'number': chapter_num,
                'title': title,
                'pages': end_page - start_page,
                'chars': len(combined_text),
                'file': chapter_file.name
            }
            chapters_meta.append(meta)

            print(f"  Chapter {chapter_num}: '{title}' - {len(combined_text):,} chars ({end_page - start_page} pages)")

    return chapters_meta
