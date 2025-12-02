#!/usr/bin/env python3
"""
Generate summaries for translated chapters.
"""

import argparse
import time
from pathlib import Path

from config import (
    get_openai_client, SUMMARY_MODEL, TEMPERATURE, MAX_RETRIES
)


def generate_summary(client, chapter_num: int, text: str) -> str:
    """Generate summary for a chapter"""
    # Use first 3000 chars for summary
    text_to_summarize = text[:3000]

    prompt = f"""Summarize this Chinese chapter in 2-3 paragraphs (in Chinese).

Focus on:
- Main ideas and key points
- Important concepts or lessons
- Practical takeaways

Text:
{text_to_summarize}

Summary (in Chinese):"""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at creating concise, insightful chapter summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=2000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    return ""


def summarize_chapters(input_dir: str, output_dir: str, max_chapters: int = None):
    """Generate summaries for all chapters"""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize client
    print("Initializing OpenAI client...")
    client = get_openai_client()

    # Get translation files
    trans_files = sorted(input_dir.glob('chapter_*_cn.md'))
    if max_chapters:
        trans_files = trans_files[:max_chapters]

    print(f"Found {len(trans_files)} chapters to summarize\n")

    # Generate summaries
    for trans_file in trans_files:
        chapter_num = int(trans_file.stem.split('_')[1])

        # Check if already summarized
        output_file = output_dir / f"chapter_{chapter_num:02d}_summary.txt"
        if output_file.exists():
            print(f"Chapter {chapter_num}: Already summarized, skipping")
            continue

        print(f"Chapter {chapter_num}...", end=' ', flush=True)

        # Read translation
        text = trans_file.read_text(encoding='utf-8')

        # Generate summary
        summary = generate_summary(client, chapter_num, text)

        if summary:
            output_file.write_text(summary, encoding='utf-8')
            print(f"Done ({len(summary)} chars)")
        else:
            print("Failed")

        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Summaries generated!")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Generate chapter summaries')
    parser.add_argument('input_dir', help='Directory containing translated chapter files')
    parser.add_argument('output_dir', help='Directory to save summaries')
    parser.add_argument('--max', type=int, help='Summarize only first N chapters')

    args = parser.parse_args()

    summarize_chapters(args.input_dir, args.output_dir, args.max)


if __name__ == '__main__':
    main()
