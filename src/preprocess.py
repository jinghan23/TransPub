#!/usr/bin/env python3
"""
Preprocess extracted chapters to fix PDF artifacts and add Markdown formatting.
This step runs BEFORE translation to ensure clean source text.
"""

import argparse
import time
from pathlib import Path

from config import (
    get_openai_client, TRANSLATION_MODEL, TEMPERATURE, MAX_RETRIES
)


def clean_and_format_chapter(client, text: str, chapter_num: int) -> str:
    """Use GPT to clean PDF artifacts AND add Markdown formatting"""
    print(f"  Processing Chapter {chapter_num}...")

    prompt = f"""You are a text preprocessing expert. Clean up this English book chapter AND add Markdown formatting in ONE step.

TASK 1 - FIX PDF ARTIFACTS:
1. **Broken paragraphs**: Merge paragraphs split by page breaks (no topic change)
2. **Hyphenated words**: Fix words split across lines (e.g., "meno-\\npause" → "menopause")
3. **Broken sentences**: Merge sentences incorrectly split across paragraphs
4. PRESERVE intentional paragraph breaks (topic changes, new sections)

TASK 2 - ADD MARKDOWN FORMATTING:
1. Chapter title → `# Title` (H1)
2. Chapter subtitle/tagline → `*subtitle*` (italic)
3. Section headings → `## Heading` (H2)
4. Keep all paragraph text unchanged

RULES:
- DO NOT change any words or rephrase content
- DO NOT add or remove content
- Only fix paragraph breaks and add Markdown symbols

Example output format:
```
# 1. The Stats. The Stigma. The Silence.

*How we think and talk about menopause matters.*

Life expectancy for women is about 81 years...

## PERCEPTION MATTERS

Our cultural and societal views on aging...

## CHANGING FOR THE BETTER

Menopause is a time to look forward...
```

Input text (with PDF artifacts):

{text}

Cleaned AND formatted text (Markdown added, artifacts fixed):"""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=TRANSLATION_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at cleaning up PDF-extracted text. You fix paragraph breaks and hyphenation without changing any content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=16000
            )

            cleaned = response.choices[0].message.content.strip()
            print(f"    Done (before: {len(text):,}, after: {len(cleaned):,} chars)")
            return cleaned

        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    Failed to process Chapter {chapter_num}, returning original")
                return text

    return text


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
