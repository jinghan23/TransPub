#!/usr/bin/env python3
"""
Generate audio files for translated chapters using TTS.
Supports paragraph-based chunking for long chapters.
"""

import argparse
import time
from pathlib import Path
from collections import deque

from config import (
    get_openai_client, TTS_API_KEY,
    TTS_MODEL, TTS_VOICE, TTS_QPM, MAX_RETRIES, MAX_AUDIO_CHUNK
)


class RateLimiter:
    """Rate limiter for TTS API"""

    def __init__(self, qpm):
        self.qpm = qpm
        self.min_delay = 60.0 / qpm
        self.request_times = deque(maxlen=qpm)

    def wait_if_needed(self):
        now = time.time()

        if len(self.request_times) > 0:
            time_since_last = now - self.request_times[-1]
            if time_since_last < self.min_delay:
                sleep_time = self.min_delay - time_since_last
                print(f"      Rate limiting: {sleep_time:.1f}s", end='', flush=True)
                time.sleep(sleep_time)
                now = time.time()

        if len(self.request_times) >= self.qpm:
            time_since_oldest = now - self.request_times[0]
            if time_since_oldest < 60.0:
                sleep_time = 60.0 - time_since_oldest
                print(f"      QPM limit: {sleep_time:.1f}s", end='', flush=True)
                time.sleep(sleep_time)
                now = time.time()

        self.request_times.append(now)


def init_client():
    """Initialize OpenAI client for TTS"""
    return get_openai_client(api_key=TTS_API_KEY)


def split_by_paragraphs(text: str) -> list:
    """Split text into chunks by paragraph boundaries"""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_size = len(para)

        if para_size > MAX_AUDIO_CHUNK:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0

            # Split large paragraph by sentences
            sentences = []
            for delimiter in ['。', '！', '？', '.', '!', '?']:
                if delimiter in para:
                    parts = para.split(delimiter)
                    sentences = [s + delimiter for s in parts[:-1]] + [parts[-1]]
                    break

            if not sentences:
                sentences = [para]

            temp_chunk = []
            temp_size = 0
            for sent in sentences:
                if temp_size + len(sent) > MAX_AUDIO_CHUNK and temp_chunk:
                    chunks.append(''.join(temp_chunk))
                    temp_chunk = [sent]
                    temp_size = len(sent)
                else:
                    temp_chunk.append(sent)
                    temp_size += len(sent)

            if temp_chunk:
                chunks.append(''.join(temp_chunk))

        elif current_size + para_size + 2 > MAX_AUDIO_CHUNK:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size + 2

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def generate_audio_chunk(client, rate_limiter, text: str, output_path: Path) -> bool:
    """Generate audio for a single chunk"""
    for attempt in range(MAX_RETRIES):
        try:
            rate_limiter.wait_if_needed()
            start_time = time.time()

            with client.audio.speech.with_streaming_response.create(
                model=TTS_MODEL,
                voice=TTS_VOICE,
                input=text
            ) as response:
                response.stream_to_file(str(output_path))

            duration = time.time() - start_time
            file_size = output_path.stat().st_size
            print(f" {duration:.1f}s ({file_size/1024:.0f}KB)")
            return True

        except Exception as e:
            print(f" Failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    return False


def merge_audio_parts(audio_dir: Path, chapter_num: int, num_parts: int) -> bool:
    """Merge audio parts into a single file"""
    part_files = [audio_dir / f'chapter_{chapter_num:02d}_part{i:02d}.mp3'
                  for i in range(1, num_parts + 1)]

    if not all(f.exists() for f in part_files):
        return False

    full_file = audio_dir / f'chapter_{chapter_num:02d}_full.mp3'

    with open(full_file, 'wb') as outfile:
        for part_file in part_files:
            with open(part_file, 'rb') as infile:
                outfile.write(infile.read())

    file_size = full_file.stat().st_size / (1024 * 1024)
    print(f"    Merged: {full_file.name} ({file_size:.2f} MB)")
    return True


def generate_audio_for_chapter(client, rate_limiter, chapter_num: int, text: str, audio_dir: Path) -> bool:
    """Generate audio for a chapter"""
    print(f"  Chapter {chapter_num} ({len(text):,} chars)")

    # Remove markdown for cleaner audio
    clean_text = text.replace('#', '').replace('*', '').strip()

    chunks = split_by_paragraphs(clean_text)
    print(f"    {len(chunks)} chunks")

    success_count = 0
    for idx, chunk in enumerate(chunks, 1):
        if len(chunks) == 1:
            output_path = audio_dir / f"chapter_{chapter_num:02d}_full.mp3"
        else:
            output_path = audio_dir / f"chapter_{chapter_num:02d}_part{idx:02d}.mp3"

        if output_path.exists():
            print(f"    Chunk {idx}: Already exists")
            success_count += 1
            continue

        print(f"    Chunk {idx}/{len(chunks)} ({len(chunk):,} chars)...", end='', flush=True)

        if generate_audio_chunk(client, rate_limiter, chunk, output_path):
            success_count += 1

    if success_count == len(chunks) and len(chunks) > 1:
        merge_audio_parts(audio_dir, chapter_num, len(chunks))

    return success_count == len(chunks)


def generate_audio(input_dir: str, output_dir: str, chapters: str = None):
    """Generate audio for chapters"""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize
    print(f"TTS Model: {TTS_MODEL}, Voice: {TTS_VOICE}, QPM: {TTS_QPM}\n")
    client = init_client()
    rate_limiter = RateLimiter(TTS_QPM)

    # Get translation files
    trans_files = sorted(input_dir.glob('chapter_*_cn.md'))

    # Filter by chapter numbers if specified
    if chapters:
        if '-' in chapters:
            start, end = map(int, chapters.split('-'))
            chapter_nums = set(range(start, end + 1))
        else:
            chapter_nums = set(map(int, chapters.split(',')))

        trans_files = [f for f in trans_files
                      if int(f.stem.split('_')[1]) in chapter_nums]

    print(f"Processing {len(trans_files)} chapters\n")

    # Generate audio
    success = 0
    for trans_file in trans_files:
        chapter_num = int(trans_file.stem.split('_')[1])

        # Check if already done
        full_audio = output_dir / f'chapter_{chapter_num:02d}_full.mp3'
        if full_audio.exists():
            print(f"  Chapter {chapter_num}: Already done")
            success += 1
            continue

        text = trans_file.read_text(encoding='utf-8')
        if generate_audio_for_chapter(client, rate_limiter, chapter_num, text, output_dir):
            success += 1

    print(f"\n{'='*60}")
    print(f"Audio generation complete: {success}/{len(trans_files)} chapters")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Generate audio for translated chapters')
    parser.add_argument('input_dir', help='Directory containing translated chapter files')
    parser.add_argument('output_dir', help='Directory to save audio files')
    parser.add_argument('--chapters', help='Chapter numbers to process (e.g., "1-5" or "1,3,5")')

    args = parser.parse_args()

    generate_audio(args.input_dir, args.output_dir, args.chapters)


if __name__ == '__main__':
    main()
