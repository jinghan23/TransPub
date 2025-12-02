<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/GPT--4o-Powered-orange?style=for-the-badge&logo=openai" alt="GPT-4o">
  <img src="https://img.shields.io/badge/TTS-OpenAI-purple?style=for-the-badge" alt="TTS">
</p>

<h1 align="center">TransPub</h1>

<p align="center">
  <strong>One command to transform PDF books into translated audiobook websites</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-configuration">Configuration</a>
</p>

---

## ✨ Features

```
📄 PDF  →  📑 Chapter Extraction  →  🧹 Preprocessing  →  🌐 Translation  →  📝 Summary  →  🎧 Audio  →  🌍 Website
```

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Chapter Detection** | Automatically detects chapter boundaries in PDFs |
| 🧹 **PDF Preprocessing** | Fixes common PDF extraction issues, adds Markdown formatting |
| 🌐 **AI Translation** | High-quality translation powered by GPT-4o |
| 📝 **Chapter Summaries** | Auto-generated summaries for each chapter |
| 🎧 **Text-to-Speech** | Natural voice audio using OpenAI TTS |
| 🌍 **One-Click Publishing** | Generates static website with audio player, ready for GitHub Pages |
| ⚡ **Resume Support** | Incremental processing, can resume after interruption |

---

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/YOUR_USERNAME/TransPub.git
cd TransPub

conda create -n transpub python=3.10 -y
conda activate transpub

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run

```bash
# Full pipeline: PDF → Translation → Summary → Audio → Website
./process_book.sh "books/MyBook.pdf" "my-book" "My Book Title"

# Quick test (first 3 chapters, no audio)
./process_book.sh "books/MyBook.pdf" "my-book" "My Book Title" --max-chapters 3 --skip-audio
```

### 4. Deploy

```bash
# Local preview
cd docs && python3 -m http.server 8000
# Open http://localhost:8000/books/my-book/

# Deploy to GitHub Pages
git add docs/ && git commit -m "Add my-book" && git push
```

---

## 📖 Usage

### Basic Usage

```bash
./process_book.sh <pdf_path> <book_slug> <book_title> [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--skip-audio` | Skip audio generation (faster) |
| `--skip-pages N` | Skip first N pages (default: 10) |
| `--max-chapters N` | Process only first N chapters |
| `--step STEP` | Run specific step only: `extract`, `preprocess`, `translate`, `summarize`, `audio`, `website` |

### Examples

```bash
# Skip audio generation
./process_book.sh "books/Book.pdf" "my-book" "Title" --skip-audio

# Process only first 5 chapters
./process_book.sh "books/Book.pdf" "my-book" "Title" --max-chapters 5

# Run only translation step
./process_book.sh "books/Book.pdf" "my-book" "Title" --step translate
```

---

## 📁 Project Structure

```
TransPub/
├── books/                      # Input PDF files
├── src/                        # Core Python modules
│   ├── config.py               # Configuration
│   ├── extract_chapters.py     # Chapter extraction
│   ├── preprocess.py           # Text preprocessing
│   ├── translate.py            # Translation
│   ├── summarize.py            # Summary generation
│   ├── generate_audio.py       # TTS audio generation
│   └── generate_website.py     # Website generation
├── output/books/               # Processing output
│   └── {book-slug}/
│       ├── chapters/           # Raw chapters
│       ├── processed/          # Preprocessed chapters
│       ├── translations/       # Translated chapters
│       ├── summaries/          # Chapter summaries
│       └── audio/              # Audio files
├── docs/                       # GitHub Pages website
├── process_book.sh             # Main entry script
├── .env.example                # Environment template
└── requirements.txt            # Python dependencies
```

---

## ⚙️ Configuration

Create `.env` from `.env.example`:

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-your-api-key-here

# API Base URL (optional, defaults to OpenAI)
OPENAI_API_BASE=https://api.openai.com/v1

# For Azure OpenAI (uncomment):
# OPENAI_API_BASE=https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT
# OPENAI_API_VERSION=2024-02-01

# Models
TRANSLATION_MODEL=gpt-4o
SUMMARY_MODEL=gpt-4o
TTS_MODEL=tts-1-hd
TTS_VOICE=nova

# Rate limiting
TTS_QPM=5

# Processing
MAX_RETRIES=3
TEMPERATURE=0.7
```

---

## 🔧 Individual Modules

Each module can be used independently:

```bash
# Extract chapters from PDF
python src/extract_chapters.py book.pdf output/chapters

# Preprocess chapters
python src/preprocess.py input/ output/

# Translate chapters
python src/translate.py input/ output/

# Generate summaries
python src/summarize.py input/ output/

# Generate audio
python src/generate_audio.py input/ output/

# Generate website
python src/generate_website.py book-slug "Book Title"
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>⭐ Star this repo if you find it useful!</strong>
</p>
