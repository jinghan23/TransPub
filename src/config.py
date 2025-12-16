#!/usr/bin/env python3
"""
Unified configuration for book pipeline
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI / Azure OpenAI Configuration
# For standard OpenAI: OPENAI_API_BASE=https://api.openai.com/v1
# For Azure OpenAI: OPENAI_API_BASE=https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
OPENAI_API_VERSION = os.getenv('OPENAI_API_VERSION', '')  # Only needed for Azure
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TTS_API_KEY = os.getenv('TTS_API_KEY') or OPENAI_API_KEY  # Fallback to main key

# Model Configuration
TRANSLATION_MODEL = os.getenv('TRANSLATION_MODEL', 'gpt-5')
SUMMARY_MODEL = os.getenv('SUMMARY_MODEL', 'gpt-5')
TTS_MODEL = os.getenv('TTS_MODEL', 'tts-1-hd')
TTS_VOICE = os.getenv('TTS_VOICE', 'nova')
TTS_QPM = int(os.getenv('TTS_QPM', 5))

# Processing Settings
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
CHUNK_SIZE = 3000  # Characters per translation chunk
# Preprocessing chunk size (characters). Use larger chunks, split on blank lines
# Can be overridden via env PREPROCESS_CHUNK_SIZE
PREPROCESS_CHUNK_SIZE = int(os.getenv('PREPROCESS_CHUNK_SIZE', 8000))
MAX_AUDIO_CHUNK = 4000  # Characters per TTS chunk


def get_openai_client(api_key: str = None):
    """
    Create OpenAI client with proper configuration.
    Supports both standard OpenAI and Azure OpenAI endpoints.
    """
    from openai import OpenAI, AzureOpenAI

    key = api_key or OPENAI_API_KEY
    if not key:
        raise ValueError("No API key found. Set OPENAI_API_KEY in .env")

    # Check if using Azure endpoint
    if 'azure' in OPENAI_API_BASE.lower() or OPENAI_API_VERSION:
        return AzureOpenAI(
            azure_endpoint=OPENAI_API_BASE,
            api_key=key,
            api_version=OPENAI_API_VERSION or 'preview',
            timeout=1200,
            max_retries=MAX_RETRIES
        )
    else:
        return OpenAI(
            base_url=OPENAI_API_BASE,
            api_key=key,
            timeout=1200,
            max_retries=MAX_RETRIES
        )


def get_book_paths(book_slug: str):
    """Get all paths for a book based on its slug"""
    base = Path('output/books') / book_slug
    return {
        'chapters': base / 'chapters',
        'processed': base / 'processed',
        'translations': base / 'translations',
        'summaries': base / 'summaries',
        'audio': base / 'audio',
    }


def get_docs_paths(book_slug: str):
    """Get documentation paths for a book"""
    base = Path('docs/books') / book_slug
    return {
        'root': base,
        'chapters': base / 'chapters',
        'data': base / 'data',
        'audio': base / 'audio',
    }


def ensure_dirs(paths: dict):
    """Create all directories if they don't exist"""
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
