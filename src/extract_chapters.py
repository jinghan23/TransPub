#!/usr/bin/env python3
"""
Extract chapters from PDF based on chapter number detection.
Automatically detects chapter boundaries by looking for standalone numbers
at the start of pages that indicate chapter beginnings.
"""

import argparse
import re
import pdfplumber
from pathlib import Path


def find_chapter_pages(pdf_path: str, skip_pages: int = 10) -> dict:
    """
    Find the starting page for each chapter by detecting chapter numbers.

    Args:
        pdf_path: Path to PDF file
        skip_pages: Number of pages to skip (front matter, TOC)

    Returns:
        Dictionary mapping chapter numbers to page indices
    """
    chapter_pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Scanning {len(pdf.pages)} pages for chapter markers...")

        for page_num in range(skip_pages, len(pdf.pages)):
            page = pdf.pages[page_num]
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')[:10]
            first_line = lines[0].strip() if lines else ''

            # Check if first line is a chapter number (1-99)
            if re.match(r'^\d{1,2}$', first_line):
                chapter_num = int(first_line)
                if 1 <= chapter_num <= 99 and chapter_num not in chapter_pages:
                    # Verify it looks like a chapter by checking for uppercase text
                    title_lines = ' '.join(lines[1:3])
                    uppercase_count = sum(1 for c in title_lines if c.isupper())
                    total_letters = sum(1 for c in title_lines if c.isalpha())

                    if total_letters > 0 and uppercase_count / total_letters > 0.25:
                        chapter_pages[chapter_num] = page_num
                        print(f"  Found Chapter {chapter_num} on page {page_num + 1}")

    return chapter_pages


def extract_chapters(pdf_path: str, output_dir: str, skip_pages: int = 10) -> list:
    """
    Extract chapters from PDF and save as text files.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save chapter files
        skip_pages: Number of pages to skip

    Returns:
        List of chapter metadata dictionaries
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chapter_pages = find_chapter_pages(pdf_path, skip_pages)
    sorted_chapters = sorted(chapter_pages.items())
    chapters_meta = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, (chapter_num, start_page) in enumerate(sorted_chapters):
            # Determine end page
            if i + 1 < len(sorted_chapters):
                end_page = sorted_chapters[i + 1][1]
            else:
                end_page = len(pdf.pages)

            # Extract text
            chapter_text = []
            for page_num in range(start_page, end_page):
                text = pdf.pages[page_num].extract_text()
                if text:
                    chapter_text.append(text)

            combined_text = "\n\n".join(chapter_text)

            # Extract title from first few lines
            lines = combined_text.split('\n')
            title_lines = []
            for line in lines[1:4]:  # Skip chapter number, get next 3 lines
                line = line.strip()
                if line and not line.isdigit():
                    title_lines.append(line)
                    if len(title_lines) >= 2:
                        break

            title = ' '.join(title_lines) if title_lines else f"Chapter {chapter_num}"

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

            print(f"  Chapter {chapter_num}: {len(combined_text):,} chars ({end_page - start_page} pages)")

    return chapters_meta


def main():
    parser = argparse.ArgumentParser(description='Extract chapters from PDF')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('output_dir', help='Directory to save chapter files')
    parser.add_argument('--skip-pages', type=int, default=10,
                       help='Number of front matter pages to skip (default: 10)')

    args = parser.parse_args()

    print(f"\nExtracting chapters from: {args.pdf_path}")
    print(f"Output directory: {args.output_dir}")
    print(f"Skipping first {args.skip_pages} pages\n")

    chapters = extract_chapters(args.pdf_path, args.output_dir, args.skip_pages)

    print(f"\n{'='*60}")
    print(f"Extracted {len(chapters)} chapters successfully!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
