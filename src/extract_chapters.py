#!/usr/bin/env python3
"""
Router for extracting chapters from different book formats.
Supports: PDF, EPUB

Usage:
    python extract_chapters.py book.pdf output/chapters
    python extract_chapters.py book.epub output/chapters
"""

import argparse
from pathlib import Path


def extract_chapters(input_path: str, output_dir: str, skip_pages: int = 10) -> list:
    """
    Extract chapters from a book file (PDF or EPUB).

    Args:
        input_path: Path to the book file (PDF or EPUB)
        output_dir: Directory to save chapter files
        skip_pages: Number of front matter pages to skip (PDF only)

    Returns:
        List of chapter metadata dictionaries

    Raises:
        ValueError: If file format is not supported
    """
    input_path = Path(input_path)
    file_ext = input_path.suffix.lower()

    if file_ext == '.pdf':
        print(f"Detected PDF file: {input_path}")
        try:
            from .extract_chapters_pdf import extract_chapters_pdf
        except ImportError:
            from extract_chapters_pdf import extract_chapters_pdf
        return extract_chapters_pdf(str(input_path), output_dir, skip_pages)

    elif file_ext == '.epub':
        print(f"Detected EPUB file: {input_path}")
        try:
            from .extract_chapters_epub import extract_chapters_epub
        except ImportError:
            from extract_chapters_epub import extract_chapters_epub
        return extract_chapters_epub(str(input_path), output_dir)

    else:
        raise ValueError(
            f"Unsupported file format: {file_ext}\n"
            f"Supported formats: .pdf, .epub"
        )


def main():
    parser = argparse.ArgumentParser(
        description='Extract chapters from PDF or EPUB files'
    )
    parser.add_argument('input_path', help='Path to the book file (PDF or EPUB)')
    parser.add_argument('output_dir', help='Directory to save chapter files')
    parser.add_argument('--skip-pages', type=int, default=10,
                       help='Number of front matter pages to skip (PDF only, default: 10)')

    args = parser.parse_args()

    input_path = Path(args.input_path)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return

    print(f"\n{'='*60}")
    print(f"Extracting chapters from: {input_path}")
    print(f"Output directory: {args.output_dir}")
    if input_path.suffix.lower() == '.pdf':
        print(f"Skipping first {args.skip_pages} pages")
    print(f"{'='*60}\n")

    try:
        chapters = extract_chapters(str(input_path), args.output_dir, args.skip_pages)

        print(f"\n{'='*60}")
        print(f"✓ Extracted {len(chapters)} chapters successfully!")
        print(f"{'='*60}")

    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        raise


if __name__ == '__main__':
    main()
