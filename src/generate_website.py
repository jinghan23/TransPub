#!/usr/bin/env python3
"""
Generate website files for a book:
- chapters.json: Chapter metadata
- Chapter HTML pages
- Index page
"""

import argparse
import json
import shutil
from pathlib import Path
import markdown


def get_summary(summary_dir: Path, chapter_num: int) -> str:
    """Get chapter summary preview"""
    summary_file = summary_dir / f'chapter_{chapter_num:02d}_summary.txt'
    if summary_file.exists():
        summary = summary_file.read_text(encoding='utf-8').strip()
        return summary[:200] + '...' if len(summary) > 200 else summary
    return "暂无摘要"


def get_full_summary(summary_dir: Path, chapter_num: int) -> str:
    """Get full chapter summary"""
    summary_file = summary_dir / f'chapter_{chapter_num:02d}_summary.txt'
    if summary_file.exists():
        return summary_file.read_text(encoding='utf-8').strip()
    return ""


def has_audio(audio_dir: Path, chapter_num: int) -> bool:
    """Check if chapter has audio"""
    return (audio_dir / f'chapter_{chapter_num:02d}_full.mp3').exists()


def get_word_count(trans_file: Path) -> int:
    """Count Chinese characters"""
    if trans_file.exists():
        text = trans_file.read_text(encoding='utf-8')
        return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return 0


def extract_title(trans_file: Path, chapter_num: int) -> str:
    """Extract chapter title from translation file"""
    if trans_file.exists():
        first_line = trans_file.read_text(encoding='utf-8').split('\n')[0]
        # Remove chapter number prefix if present
        if first_line.startswith(f"{chapter_num}."):
            return first_line[len(f"{chapter_num}."):].strip()
        return first_line.strip()
    return f"Chapter {chapter_num}"


def generate_chapters_json(trans_dir: Path, summary_dir: Path, audio_dir: Path, output_file: Path):
    """Generate chapters.json metadata file"""
    chapters = []

    trans_files = sorted(trans_dir.glob('chapter_*_cn.md'))

    for trans_file in trans_files:
        chapter_num = int(trans_file.stem.split('_')[1])

        chapter_data = {
            'number': chapter_num,
            'title': extract_title(trans_file, chapter_num),
            'summary': get_summary(summary_dir, chapter_num),
            'hasAudio': has_audio(audio_dir, chapter_num),
            'wordCount': get_word_count(trans_file),
            'file': f'chapter_{chapter_num:02d}.html'
        }

        chapters.append(chapter_data)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

    print(f"Generated {output_file} with {len(chapters)} chapters")
    return chapters


def generate_chapter_html(chapter_num: int, trans_file: Path, summary_dir: Path,
                         audio_dir: Path, output_dir: Path, book_title: str):
    """Generate HTML page for a chapter"""
    content = trans_file.read_text(encoding='utf-8')
    title = extract_title(trans_file, chapter_num)

    # Convert markdown to HTML
    content_html = markdown.markdown(content, extensions=['extra'])

    # Audio section
    audio_html = ''
    if has_audio(audio_dir, chapter_num):
        audio_html = f'''
        <div class="audio-player">
            <h3>章节音频</h3>
            <audio controls>
                <source src="../audio/chapter_{chapter_num:02d}_full.mp3" type="audio/mpeg">
                您的浏览器不支持音频播放。
            </audio>
        </div>'''

    # Summary section
    summary_html = ''
    full_summary = get_full_summary(summary_dir, chapter_num)
    if full_summary:
        summary_html = f'''
        <div class="chapter-summary-box">
            <h3>章节摘要</h3>
            <p>{full_summary}</p>
        </div>'''

    # HTML template
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>第 {chapter_num} 章: {title} - {book_title}</title>
    <link rel="stylesheet" href="../../../css/style.css">
</head>
<body>
    <div class="container chapter-detail">
        <a href="../index.html" class="back-link">&larr; 返回目录</a>

        <div class="chapter-header">
            <h1>第 {chapter_num} 章: {title}</h1>
        </div>

        {summary_html}
        {audio_html}

        <div class="chapter-content">
            {content_html}
        </div>

        <div class="chapter-bottom-nav">
            <a href="../index.html" class="back-link">&larr; 返回目录</a>
        </div>
    </div>
</body>
</html>'''

    output_file = output_dir / f'chapter_{chapter_num:02d}.html'
    output_file.write_text(html, encoding='utf-8')
    print(f"  Generated {output_file.name}")


def generate_index_html(chapters: list, output_dir: Path, book_title: str, book_slug: str):
    """Generate book index page"""
    chapters_html = ''
    for ch in chapters:
        audio_badge = '<span class="audio-badge">🔊</span>' if ch['hasAudio'] else ''
        chapters_html += f'''
        <div class="chapter-card" onclick="location.href='chapters/{ch['file']}'">
            <div class="chapter-number">第 {ch['number']} 章</div>
            <div class="chapter-title">{ch['title']}</div>
            <div class="chapter-summary">{ch['summary']}</div>
            <div class="chapter-meta">
                <span>{ch['wordCount']:,} 字</span>
                {audio_badge}
            </div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{book_title} - 中文翻译</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>{book_title}</h1>
            <p class="subtitle">中文翻译版 | {len(chapters)} 章节</p>
        </header>

        <div class="chapters-grid">
            {chapters_html}
        </div>

        <footer>
            <p>由 AI 翻译生成 | <a href="../../index.html">返回书籍列表</a></p>
        </footer>
    </div>
</body>
</html>'''

    (output_dir / 'index.html').write_text(html, encoding='utf-8')
    print(f"Generated index.html")


def copy_audio_files(audio_src: Path, audio_dest: Path):
    """Copy audio files to docs directory"""
    audio_dest.mkdir(parents=True, exist_ok=True)

    for audio_file in audio_src.glob('*_full.mp3'):
        dest_file = audio_dest / audio_file.name
        if not dest_file.exists():
            shutil.copy(audio_file, dest_file)
            print(f"  Copied {audio_file.name}")


def generate_books_index(docs_base: str):
    """Generate docs/index.html with list of all books"""
    docs_dir = Path(docs_base).parent  # docs/books -> docs
    books_dir = Path(docs_base)  # docs/books

    books = []

    # Scan all books in docs/books/
    if books_dir.exists():
        for book_dir in sorted(books_dir.iterdir()):
            if not book_dir.is_dir():
                continue

            # Read chapters.json to get book info
            chapters_json = book_dir / 'data' / 'chapters.json'
            if chapters_json.exists():
                try:
                    chapters_data = json.loads(chapters_json.read_text(encoding='utf-8'))

                    # Extract book title from index.html
                    index_html = book_dir / 'index.html'
                    book_title = book_dir.name  # fallback to slug
                    if index_html.exists():
                        content = index_html.read_text(encoding='utf-8')
                        # Extract title from <h1> tag
                        import re
                        match = re.search(r'<h1>(.*?)</h1>', content)
                        if match:
                            book_title = match.group(1)

                    books.append({
                        'slug': book_dir.name,
                        'title': book_title,
                        'chapters_count': len(chapters_data),
                        'total_words': sum(ch.get('wordCount', 0) for ch in chapters_data),
                        'has_audio': any(ch.get('hasAudio', False) for ch in chapters_data)
                    })
                except Exception as e:
                    print(f"Warning: Failed to read {book_dir.name}: {e}")

    # Generate HTML
    books_html = ''
    for book in books:
        audio_badge = '🔊 有声书' if book['has_audio'] else ''
        books_html += f'''
        <div class="book-card" onclick="location.href='books/{book['slug']}/index.html'">
            <div class="book-title">{book['title']}</div>
            <div class="book-meta">
                <span>📚 {book['chapters_count']} 章节</span>
                <span>📝 {book['total_words']:,} 字</span>
                {f'<span class="audio-badge">{audio_badge}</span>' if audio_badge else ''}
            </div>
        </div>'''

    if not books_html:
        books_html = '<p style="text-align: center; color: #999;">暂无书籍</p>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>书籍列表 - TransPub</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>我的书籍收藏</h1>
            <p class="subtitle">由 TransPub 生成 | 共 {len(books)} 本书籍</p>
        </header>

        <div class="books-grid">
            {books_html}
        </div>

        <footer>
            <p>Powered by <a href="https://github.com/jinghan23/TransPub" target="_blank">TransPub</a></p>
        </footer>
    </div>
</body>
</html>'''

    index_file = docs_dir / 'index.html'
    index_file.write_text(html, encoding='utf-8')
    print(f"\nGenerated {index_file} with {len(books)} book(s)")


def generate_website(book_slug: str, book_title: str, output_base: str, docs_base: str):
    """Generate complete website for a book"""
    output_dir = Path(output_base) / book_slug
    docs_dir = Path(docs_base) / book_slug

    # Source directories
    trans_dir = output_dir / 'translations'
    summary_dir = output_dir / 'summaries'
    audio_dir = output_dir / 'audio'

    # Destination directories
    docs_chapters = docs_dir / 'chapters'
    docs_data = docs_dir / 'data'
    docs_audio = docs_dir / 'audio'

    # Create directories
    docs_chapters.mkdir(parents=True, exist_ok=True)
    docs_data.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating website for: {book_title}")
    print(f"Output: {docs_dir}\n")

    # Generate chapters.json
    chapters = generate_chapters_json(trans_dir, summary_dir, audio_dir,
                                      docs_data / 'chapters.json')

    # Generate chapter HTML pages
    print("\nGenerating chapter pages...")
    for trans_file in sorted(trans_dir.glob('chapter_*_cn.md')):
        chapter_num = int(trans_file.stem.split('_')[1])
        generate_chapter_html(chapter_num, trans_file, summary_dir, audio_dir,
                            docs_chapters, book_title)

    # Generate index page
    print("\nGenerating index page...")
    generate_index_html(chapters, docs_dir, book_title, book_slug)

    # Copy audio files
    if audio_dir.exists():
        print("\nCopying audio files...")
        copy_audio_files(audio_dir, docs_audio)

    # Create global CSS (only if it doesn't exist)
    global_css_dir = Path(docs_base).parent / 'css'
    global_css_file = global_css_dir / 'style.css'

    global_css_dir.mkdir(parents=True, exist_ok=True)
    if not global_css_file.exists():
        print("\nNote: Global CSS file not found at {global_css_file}")
        print("  Copy docs/css/style.css from the TransPub repository.")
    else:
        print(f"\nGlobal CSS: {global_css_file}")

    print(f"\n{'='*60}")
    print(f"Website generated successfully!")
    print(f"{'='*60}")

    # Generate books index page (docs/index.html)
    generate_books_index(docs_base)


def main():
    parser = argparse.ArgumentParser(description='Generate website for a book')
    parser.add_argument('book_slug', help='Book slug (directory name)')
    parser.add_argument('book_title', help='Book title for display')
    parser.add_argument('--output-base', default='output/books', help='Base directory for book outputs')
    parser.add_argument('--docs-base', default='docs/books', help='Base directory for website files')

    args = parser.parse_args()

    generate_website(args.book_slug, args.book_title, args.output_base, args.docs_base)


if __name__ == '__main__':
    main()
