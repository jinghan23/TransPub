#!/usr/bin/env python3
"""
Preprocess extracted chapters to fix PDF artifacts and add Markdown formatting.
This step runs BEFORE translation to ensure clean source text.
"""

import argparse
import time
from pathlib import Path

from config import (
    get_openai_client, TRANSLATION_MODEL, TEMPERATURE, MAX_RETRIES,
    PREPROCESS_CHUNK_SIZE,
)


def _split_preprocess_chunks(text: str, max_chars: int) -> list:
    """Split text into large chunks preferring paragraph boundaries ("\n\n").

    - Greedily packs paragraphs until adding the next would exceed max_chars.
    - If a single paragraph exceeds max_chars, fall back to sentence/space split.
    """
    paras = text.split("\n\n")
    chunks = []
    current = []
    current_len = 0

    def flush_current():
        nonlocal current, current_len
        if current:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_len = 0

    for para in paras:
        # Include separator length (two newlines) if current not empty
        sep = 2 if current else 0
        if current_len + sep + len(para) <= max_chars:
            current.append(para)
            current_len += sep + len(para)
        else:
            # If paragraph itself is too large, split within paragraph
            if not current:
                p = para
                i = 0
                while i < len(p):
                    end = min(i + max_chars, len(p))
                    chunk = p[i:end]
                    # try to cut on sentence boundary within this oversized paragraph
                    if end < len(p):
                        last_break = max(
                            chunk.rfind(". "),
                            chunk.rfind("! "),
                            chunk.rfind("? "),
                            chunk.rfind(".\n"),
                            chunk.rfind(" ")
                        )
                        if last_break > max_chars * 0.5:
                            chunk = chunk[:last_break + 1]
                            end = i + len(chunk)
                    chunks.append(chunk.strip())
                    i = end
            else:
                flush_current()
                current.append(para)
                current_len = len(para)

    flush_current()

    # Remove empties just in case
    return [c for c in chunks if c]


def _preprocess_chunk(client, chunk: str, chapter_num: int, idx: int, total: int) -> str:
    """Clean PDF artifacts and add Markdown formatting for a single chunk."""
    prompt = f"""You are a text preprocessing expert. Clean up this English book chapter PART and add Markdown formatting.

This is part {idx} of {total} for Chapter {chapter_num}. Only process the given text span; do not assume context outside it.

TASK 1 - FIX PDF ARTIFACTS (within this part only):
1. Merge paragraphs split by page breaks when clearly the same sentence/topic
2. Fix hyphenated words split across lines (e.g., "meno-\\npause" → "menopause")
3. Merge sentences incorrectly split across lines
4. Preserve intentional paragraph breaks

TASK 2 - ADD MARKDOWN FORMATTING:
1. Convert section headings to `## Heading` when already present
2. Convert obvious subtitles/taglines to `*italic*` when clearly intended
3. Keep body text unchanged except for artifact fixes
4. DO NOT add the chapter title H1 here (handled elsewhere)

RULES:
- DO NOT change wording or meaning
- DO NOT add or remove content
- Only fix paragraph/sentence breaks and add minimal Markdown markers

Input text (with PDF artifacts):

{chunk}

Cleaned and markdown-formatted text for this part:"""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=TRANSLATION_MODEL,
                messages=[
                    {"role": "system", "content": "You clean PDF-extracted text without rewriting, adding only minimal Markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=16000
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"    Part {idx}: attempt failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                return chunk  # fallback to original chunk


def clean_and_format_chapter(client, text: str, chapter_num: int) -> str:
    """Use GPT to clean PDF artifacts and add Markdown formatting with chunking.

    Splits the chapter content into large chunks using blank-line boundaries
    and processes each chunk independently to avoid context window limits.
    """
    print(f"  Processing Chapter {chapter_num}...")

    chunks = _split_preprocess_chunks(text, PREPROCESS_CHUNK_SIZE)
    if len(chunks) > 1:
        print(f"    Split into {len(chunks)} parts (≤{PREPROCESS_CHUNK_SIZE} chars each)")

    outputs = []
    for idx, chunk in enumerate(chunks, 1):
        print(f"    Part {idx}/{len(chunks)}...", end=' ', flush=True)
        cleaned = _preprocess_chunk(client, chunk, chapter_num, idx, len(chunks))
        outputs.append(cleaned)
        print(f"Done ({len(cleaned):,} chars)")
        time.sleep(1)

    combined = "\n\n".join(outputs).strip()
    print(f"    Done (before: {len(text):,}, after: {len(combined):,} chars)")
    return combined


def process_chapters(input_dir: str, output_dir: str, max_chapters: int = None):
    """Process all chapters in input directory"""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize client
    print("Initializing OpenAI client...")
    client = get_openai_client()

    # Get chapter files
    chapter_files = sorted(input_dir.glob('chapter_*.txt'))
    if max_chapters:
        chapter_files = chapter_files[:max_chapters]

    print(f"Found {len(chapter_files)} chapters to process\n")

    # Process each chapter
    for chapter_file in chapter_files:
        chapter_num = int(chapter_file.stem.split('_')[1])

        # Read chapter
        text = chapter_file.read_text(encoding='utf-8')
        lines = text.split('\n', 1)
        title = lines[0] if lines else f"Chapter {chapter_num}"
        content = lines[1] if len(lines) > 1 else text

        print(f"\nChapter {chapter_num}: {title}")

        # Clean and format
        cleaned_content = clean_and_format_chapter(client, content, chapter_num)

        # Save
        output_file = output_dir / chapter_file.name
        output_file.write_text(f"{title}\n\n{cleaned_content}", encoding='utf-8')

        time.sleep(1)  # Rate limiting

    print(f"\n{'='*60}")
    print(f"All chapters preprocessed!")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Preprocess chapters for translation')
    parser.add_argument('input_dir', help='Directory containing raw chapter files')
    parser.add_argument('output_dir', help='Directory to save processed files')
    parser.add_argument('--max', type=int, help='Process only first N chapters')

    args = parser.parse_args()

    process_chapters(args.input_dir, args.output_dir, args.max)


if __name__ == '__main__':
    main()
