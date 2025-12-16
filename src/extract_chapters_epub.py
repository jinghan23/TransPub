#!/usr/bin/env python3
"""
Extract chapters from EPUB files.
EPUB files are already structured as separate HTML files per chapter,
making extraction simpler than PDFs.
"""

import re
from pathlib import Path
from ebooklib import epub
import ebooklib

# Support both direct execution and module import
try:
    from .utils import clean_html_text, chinese_to_int
except ImportError:
    from utils import clean_html_text, chinese_to_int


def extract_toc_chapters_epub(epub_path: str) -> list:
    """
    Extract chapter information from EPUB's built-in TOC.

    Returns:
        List of tuples: (chapter_number, title, item_id)
    """
    book = epub.read_epub(epub_path)
    toc = book.toc

    if not toc:
        return []

    chapters = []
    chapter_num = 0
    seen_hrefs = set()  # Track seen hrefs to avoid duplicates

    # Keywords that indicate section/part headers (not actual chapters)
    section_keywords = ['part', 'section', 'introduction to part', 'unit']

    def is_section_header(title: str) -> bool:
        """Check if this is a section/part header rather than a chapter"""
        title_lower = title.lower().strip()
        # Check if it's ONLY "part" or "part I/II/III" etc.
        if re.match(r'^part\s*[ivxlcdm0-9]*$', title_lower):
            return True
        return False

    def is_valid_chapter(title: str, href: str) -> bool:
        """Check if this is a valid chapter to extract"""
        title_lower = title.lower().strip()

        # Skip section headers
        if is_section_header(title):
            return False

        # Skip generic "chapter" entries (likely duplicates or navigation links)
        if title_lower == 'chapter':
            return False

        # Skip if we've already seen this href (duplicate entry)
        if href in seen_hrefs:
            return False

        return True

    def parse_toc_item(item, depth=0):
        """Recursively parse TOC items (handles nested sections)"""
        nonlocal chapter_num

        if isinstance(item, tuple):
            # Nested section: (Section/Link, children)
            section = item[0]
            children = item[1] if len(item) > 1 else []

            # If the section itself is a Link (not just a Section header), extract it
            if isinstance(section, epub.Link) and is_valid_chapter(section.title, section.href):
                chapter_num += 1
                chapters.append((chapter_num, section.title, section.href))
                seen_hrefs.add(section.href)
                print(f"  Chapter {chapter_num}: '{section.title}'")

            # Process children (actual chapters in the section)
            for sub_item in children:
                parse_toc_item(sub_item, depth + 1)

        elif isinstance(item, epub.Link):
            # Direct link - extract if valid
            if is_valid_chapter(item.title, item.href):
                chapter_num += 1
                chapters.append((chapter_num, item.title, item.href))
                seen_hrefs.add(item.href)
                print(f"  Chapter {chapter_num}: '{item.title}'")

        elif isinstance(item, epub.Section):
            # Section header alone - skip it (just a label)
            pass

        else:
            # Assume it's an EpubHtml item
            if hasattr(item, 'get_name'):
                href = item.get_name()
                title = getattr(item, 'title', f'Chapter {chapter_num + 1}')
                if is_valid_chapter(title, href):
                    chapter_num += 1
                    chapters.append((chapter_num, title, href))
                    seen_hrefs.add(href)
                    print(f"  Chapter {chapter_num}: '{title}'")

    print(f"Found EPUB TOC with {len(toc)} entries")
    for item in toc:
        parse_toc_item(item)

    return chapters


def extract_all_documents_epub(epub_path: str) -> list:
    """
    Fallback: Extract all ITEM_DOCUMENT items as chapters.
    Used when TOC is not available or unreliable.

    Returns:
        List of tuples: (chapter_number, title, item_name)
    """
    book = epub.read_epub(epub_path)
    chapters = []
    chapter_num = 0

    print("Extracting all document items from EPUB...")

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            chapter_num += 1

            # Try to extract title from HTML
            try:
                html_content = item.get_content().decode('utf-8')
                # Look for <title> or <h1> tags
                title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
                if not title_match:
                    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE)

                if title_match:
                    title = clean_html_text(title_match.group(1))
                else:
                    title = f"Chapter {chapter_num}"
            except:
                title = f"Chapter {chapter_num}"

            chapters.append((chapter_num, title, item.get_name()))
            print(f"  Chapter {chapter_num}: '{title}' ({item.get_name()})")

    return chapters


def find_chapter_items(epub_path: str) -> list:
    """
    Find chapters using the best available method.

    Returns:
        List of tuples: (chapter_number, title, item_identifier)
    """
    # Try TOC first (most reliable)
    chapters = extract_toc_chapters_epub(epub_path)

    if chapters:
        print(f"\nUsing EPUB TOC (found {len(chapters)} chapters)")
        return chapters

    # Fallback to extracting all documents
    print("\nNo reliable TOC found, extracting all document items...")
    chapters = extract_all_documents_epub(epub_path)

    if chapters:
        print(f"Found {len(chapters)} chapters from document items")
    else:
        print("Warning: No chapters detected!")

    return chapters


def extract_chapters_epub(epub_path: str, output_dir: str, skip_pages: int = 0) -> list:
    """
    Extract chapters from EPUB and save as text files.

    Args:
        epub_path: Path to EPUB file
        output_dir: Directory to save chapter files
        skip_pages: Ignored for EPUB (kept for interface compatibility)

    Returns:
        List of chapter metadata dictionaries
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get chapters as list of (chapter_num, title, item_id)
    chapters = find_chapter_items(epub_path)

    if not chapters:
        print("Error: No chapters found!")
        return []

    book = epub.read_epub(epub_path)
    chapters_meta = []

    # Create a mapping of item names to items for quick lookup
    items_map = {}
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            items_map[item.get_name()] = item

    for chapter_num, title, item_id in chapters:
        # Find the item by ID/href
        item = None

        # Try exact match first
        if item_id in items_map:
            item = items_map[item_id]
        else:
            # Try to find by matching href (might have anchor)
            item_id_base = item_id.split('#')[0]
            if item_id_base in items_map:
                item = items_map[item_id_base]

        if not item:
            print(f"  Warning: Could not find item for Chapter {chapter_num}: '{title}'")
            continue

        try:
            # Extract and clean HTML content
            html_content = item.get_content().decode('utf-8')
            text = clean_html_text(html_content)

            # Skip empty chapters
            if not text.strip():
                print(f"  Skipping Chapter {chapter_num}: '{title}' (empty)")
                continue

            # Save chapter
            chapter_file = output_dir / f"chapter_{chapter_num:02d}.txt"
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(f"{chapter_num}. {title}\n\n")
                f.write(text)

            meta = {
                'number': chapter_num,
                'title': title,
                'pages': 0,  # EPUB doesn't have pages
                'chars': len(text),
                'file': chapter_file.name
            }
            chapters_meta.append(meta)

            print(f"  Chapter {chapter_num}: '{title}' - {len(text):,} chars")

        except Exception as e:
            print(f"  Error processing Chapter {chapter_num}: {e}")
            continue

    return chapters_meta
