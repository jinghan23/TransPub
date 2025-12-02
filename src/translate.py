#!/usr/bin/env python3
"""
Translate preprocessed chapters from English to Chinese.
Preserves Markdown formatting from preprocessing step.
"""

import argparse
import time
from pathlib import Path

from config import (
    get_openai_client, TRANSLATION_MODEL, TEMPERATURE, MAX_RETRIES, CHUNK_SIZE
)


def split_into_chunks(text: str) -> list:
    """Split text into chunks at safe boundaries"""
    chunks = []
    i = 0

    while i < len(text):
        end = min(i + CHUNK_SIZE, len(text))
        chunk = text[i:end]

        if end < len(text):
            # Try paragraph boundary
            last_para = chunk.rfind('\n\n')
            if last_para > len(chunk) * 0.6:
                chunk = chunk[:last_para]
                end = i + last_para
            else:
                # Try sentence boundary
                last_sentence = max(
                    chunk.rfind('. '),
                    chunk.rfind('! '),
                    chunk.rfind('? '),
                    chunk.rfind('.\n')
                )
                if last_sentence > len(chunk) * 0.5:
                    chunk = chunk[:last_sentence + 1]
                    end = i + last_sentence + 1
                else:
                    # Last resort: word boundary
                    last_space = chunk.rfind(' ')
                    if last_space > len(chunk) * 0.7:
                        chunk = chunk[:last_space]
                        end = i + last_space

        chunks.append(chunk.strip())
        i = end

    return chunks


def translate_chunk(client, chunk: str, idx: int, total: int) -> str:
    """Translate a single chunk"""
    prompt = f"""You are a professional translator working on a book translation project.

Task: Translate the following English text to Chinese (Simplified).

Requirements:
1. **Accuracy**: Stay faithful to the original meaning and tone
2. **Fluency**: Use natural, idiomatic Chinese
3. **Completeness**: Translate ALL text, do not summarize or skip content
4. **Preserve Markdown formatting**: Keep all # ## * symbols exactly as they are
5. Only translate the text content, do NOT translate or modify Markdown symbols

Text to translate (Part {idx} of {total}):

{chunk}

Chinese translation:"""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=TRANSLATION_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional literary translator specializing in English to Chinese translation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE,
                max_tokens=16000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"      Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                return f"[Translation failed for chunk {idx}]"

    return f"[Translation failed for chunk {idx}]"


def translate_chapter(client, chapter_num: int, text: str) -> str:
    """Translate a chapter by splitting into chunks"""
    print(f"  Translating Chapter {chapter_num}...")

    chunks = split_into_chunks(text)
    print(f"    Split into {len(chunks)} chunks")

    translations = []
    for idx, chunk in enumerate(chunks, 1):
        print(f"    Chunk {idx}/{len(chunks)}...", end=' ', flush=True)
        translation = translate_chunk(client, chunk, idx, len(chunks))
        translations.append(translation)
        print(f"Done ({len(translation):,} chars)")
        time.sleep(1)

    full_translation = "\n\n".join(translations)
    print(f"    Total: {len(full_translation):,} chars")

    return full_translation


def translate_chapters(input_dir: str, output_dir: str, max_chapters: int = None):
    """Translate all chapters in input directory"""
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

    print(f"Found {len(chapter_files)} chapters to translate\n")

    # Translate each chapter
    for chapter_file in chapter_files:
        chapter_num = int(chapter_file.stem.split('_')[1])

        # Check if already translated
        output_file = output_dir / f"chapter_{chapter_num:02d}_cn.md"
        if output_file.exists():
            print(f"Chapter {chapter_num}: Already translated, skipping")
            continue

        # Read chapter
        text = chapter_file.read_text(encoding='utf-8')
        lines = text.split('\n', 1)
        title = lines[0] if lines else f"Chapter {chapter_num}"
        content = lines[1] if len(lines) > 1 else text

        print(f"\nChapter {chapter_num}: {title}")

        # Translate
        translation = translate_chapter(client, chapter_num, content)

        # Save translation
        output_file.write_text(f"{title}\n\n{translation}", encoding='utf-8')
        print(f"    Saved: {output_file.name}")

    print(f"\n{'='*60}")
    print(f"All chapters translated!")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Translate chapters to Chinese')
    parser.add_argument('input_dir', help='Directory containing preprocessed chapter files')
    parser.add_argument('output_dir', help='Directory to save translations')
    parser.add_argument('--max', type=int, help='Translate only first N chapters')

    args = parser.parse_args()

    translate_chapters(args.input_dir, args.output_dir, args.max)


if __name__ == '__main__':
    main()
