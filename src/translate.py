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


def _split_sentences(text: str) -> list:
    """Split a paragraph into sentences using simple punctuation heuristics.

    Handles both English (.!?), and Chinese (。！？) sentence enders and consumes
    following closing quotes/brackets. Keeps original order without rephrasing.
    """
    enders = set('.!?。！？')
    closers = set('"\'\)\]”’』」»）]')
    sentences = []
    n = len(text)
    start = 0
    i = 0
    while i < n:
        c = text[i]
        if c in enders:
            j = i + 1
            while j < n and text[j] in closers:
                j += 1
            if j >= n or text[j].isspace():
                # cut here
                seg = text[start:j]
                if seg.strip():
                    sentences.append(seg.strip())
                # advance to next non-space
                k = j
                while k < n and text[k].isspace():
                    k += 1
                start = k
                i = k
                continue
        i += 1
    # trailing remainder
    if start < n:
        rem = text[start:]
        if rem.strip():
            sentences.append(rem.strip())
    return sentences


def split_into_chunks(text: str) -> list:
    """Split text into chunks with paragraph-first and sentence-aware boundaries.

    - Greedily packs paragraphs (split by blank lines) up to CHUNK_SIZE.
    - If a single paragraph exceeds CHUNK_SIZE, split it into sentences and pack.
    - Falls back to space boundaries if a very long sentence exceeds CHUNK_SIZE.
    """
    paragraphs = text.split('\n\n')
    chunks = []

    current = []
    current_len = 0

    def flush_current():
        nonlocal current, current_len
        if current:
            chunks.append('\n\n'.join(current).strip())
            current = []
            current_len = 0

    for para in paragraphs:
        if not para:
            # preserve multiple blank blocks sparingly
            sep = 2 if current else 0
            if current_len + sep <= CHUNK_SIZE:
                current.append('')
                current_len += sep
            else:
                flush_current()
            continue

        # if this paragraph fits, add it
        sep = 2 if current else 0
        if current_len + sep + len(para) <= CHUNK_SIZE:
            current.append(para)
            current_len += sep + len(para)
            continue

        # if current has content, flush it first to keep boundaries clean
        if current:
            flush_current()

        # paragraph is too large: split by sentences and pack
        sentences = _split_sentences(para)
        buf = []
        buf_len = 0
        for sent in sentences:
            sep_in = 1 if buf else 0  # join sentences with a single space
            if buf_len + sep_in + len(sent) <= CHUNK_SIZE:
                buf.append(sent)
                buf_len += sep_in + len(sent)
            else:
                if buf:
                    chunks.append(' '.join(buf).strip())
                    buf = [sent]
                    buf_len = len(sent)
                else:
                    # ultra-long sentence: hard cut at last space before limit
                    s = sent
                    i = 0
                    while i < len(s):
                        end = min(i + CHUNK_SIZE, len(s))
                        part = s[i:end]
                        if end < len(s):
                            cut = part.rfind(' ')
                            if cut > CHUNK_SIZE * 0.6:
                                part = part[:cut]
                                end = i + cut
                        chunks.append(part.strip())
                        i = end
                    buf = []
                    buf_len = 0
        if buf:
            chunks.append(' '.join(buf).strip())

    flush_current()
    return [c for c in chunks if c]


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
