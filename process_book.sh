#!/bin/bash
#
# Book Pipeline - Process a PDF book from start to finish
#
# Usage:
#   ./process_book.sh <pdf_path> <book_slug> <book_title> [options]
#
# Example:
#   ./process_book.sh "books/MyBook.pdf" "my-book" "My Book Title"
#   ./process_book.sh "books/MyBook.pdf" "my-book" "My Book Title" --skip-audio
#
# Options:
#   --skip-audio       Skip audio generation
#   --skip-pages N     Skip first N pages (default: 10)
#   --max-chapters N   Process only first N chapters
#
# Pipeline Steps:
#   1. Extract chapters from PDF
#   2. Preprocess chapters (clean + format)
#   3. Translate to Chinese
#   4. Generate summaries
#   5. Generate audio (optional)
#   6. Generate website
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_step() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Show usage
usage() {
    echo "Usage: $0 <pdf_path> <book_slug> <book_title> [options]"
    echo ""
    echo "Arguments:"
    echo "  pdf_path     Path to the PDF file"
    echo "  book_slug    Short identifier for the book (e.g., 'next-level')"
    echo "  book_title   Full title of the book"
    echo ""
    echo "Options:"
    echo "  --skip-audio       Skip audio generation"
    echo "  --skip-pages N     Skip first N pages (default: 10)"
    echo "  --max-chapters N   Process only first N chapters"
    echo "  --step STEP        Run only specific step:"
    echo "                     extract, preprocess, translate, summarize, audio, website"
    echo ""
    echo "Example:"
    echo "  $0 'books/MyBook.pdf' 'my-book' 'My Book Title'"
    exit 1
}

# Parse arguments
if [ $# -lt 3 ]; then
    usage
fi

PDF_PATH="$1"
BOOK_SLUG="$2"
BOOK_TITLE="$3"
shift 3

# Default options
SKIP_AUDIO=false
SKIP_PAGES=10
MAX_CHAPTERS=""
SINGLE_STEP=""

# Parse optional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-audio)
            SKIP_AUDIO=true
            shift
            ;;
        --skip-pages)
            SKIP_PAGES="$2"
            shift 2
            ;;
        --max-chapters)
            MAX_CHAPTERS="$2"
            shift 2
            ;;
        --step)
            SINGLE_STEP="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate PDF exists
if [ ! -f "$PDF_PATH" ]; then
    print_error "PDF file not found: $PDF_PATH"
    exit 1
fi

# Set up paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
OUTPUT_DIR="$SCRIPT_DIR/output/books/$BOOK_SLUG"
DOCS_DIR="$SCRIPT_DIR/docs/books/$BOOK_SLUG"

CHAPTERS_DIR="$OUTPUT_DIR/chapters"
PROCESSED_DIR="$OUTPUT_DIR/processed"
TRANSLATIONS_DIR="$OUTPUT_DIR/translations"
SUMMARIES_DIR="$OUTPUT_DIR/summaries"
AUDIO_DIR="$OUTPUT_DIR/audio"

# Create directories
mkdir -p "$CHAPTERS_DIR" "$PROCESSED_DIR" "$TRANSLATIONS_DIR" "$SUMMARIES_DIR" "$AUDIO_DIR"

# Build max chapters argument
MAX_ARG=""
if [ -n "$MAX_CHAPTERS" ]; then
    MAX_ARG="--max $MAX_CHAPTERS"
fi

# Print configuration
echo -e "\n${GREEN}Book Pipeline Configuration${NC}"
echo "─────────────────────────────────────────────────────"
echo "PDF:          $PDF_PATH"
echo "Slug:         $BOOK_SLUG"
echo "Title:        $BOOK_TITLE"
echo "Output:       $OUTPUT_DIR"
echo "Skip pages:   $SKIP_PAGES"
echo "Max chapters: ${MAX_CHAPTERS:-all}"
echo "Skip audio:   $SKIP_AUDIO"
echo "Single step:  ${SINGLE_STEP:-none}"
echo "─────────────────────────────────────────────────────"

# Function to run a step
run_step() {
    local step_name="$1"
    local step_cmd="$2"

    # Check if we should run this step
    if [ -n "$SINGLE_STEP" ] && [ "$SINGLE_STEP" != "$step_name" ]; then
        echo "Skipping $step_name (single step mode)"
        return 0
    fi

    print_step "Step: $step_name"
    eval "$step_cmd"
}

# Change to script directory
cd "$SCRIPT_DIR"

# Step 1: Extract chapters from PDF
run_step "extract" "python3 '$SRC_DIR/extract_chapters.py' '$PDF_PATH' '$CHAPTERS_DIR' --skip-pages $SKIP_PAGES"

# Step 2: Preprocess chapters (clean + format)
run_step "preprocess" "python3 '$SRC_DIR/preprocess.py' '$CHAPTERS_DIR' '$PROCESSED_DIR' $MAX_ARG"

# Step 3: Translate to Chinese
run_step "translate" "python3 '$SRC_DIR/translate.py' '$PROCESSED_DIR' '$TRANSLATIONS_DIR' $MAX_ARG"

# Step 4: Generate summaries
run_step "summarize" "python3 '$SRC_DIR/summarize.py' '$TRANSLATIONS_DIR' '$SUMMARIES_DIR' $MAX_ARG"

# Step 5: Generate audio (optional)
if [ "$SKIP_AUDIO" = false ]; then
    run_step "audio" "python3 '$SRC_DIR/generate_audio.py' '$TRANSLATIONS_DIR' '$AUDIO_DIR'"
else
    echo "Skipping audio generation (--skip-audio)"
fi

# Step 6: Generate website
run_step "website" "python3 '$SRC_DIR/generate_website.py' '$BOOK_SLUG' '$BOOK_TITLE'"

# Done!
print_step "Pipeline Complete!"

echo -e "Output files:"
echo "  Chapters:     $CHAPTERS_DIR"
echo "  Processed:    $PROCESSED_DIR"
echo "  Translations: $TRANSLATIONS_DIR"
echo "  Summaries:    $SUMMARIES_DIR"
echo "  Audio:        $AUDIO_DIR"
echo ""
echo "Website files:"
echo "  $DOCS_DIR"
echo ""
echo -e "${GREEN}To view the website locally:${NC}"
echo "  cd docs && python3 -m http.server 8000"
echo "  Open: http://localhost:8000/books/$BOOK_SLUG/"
echo ""
echo -e "${GREEN}To deploy to GitHub Pages:${NC}"
echo "  git add docs/"
echo "  git commit -m 'Add $BOOK_TITLE'"
echo "  git push"
