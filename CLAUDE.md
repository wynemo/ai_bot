# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言

使用中文回复

## Project Overview

This is a Telegram bot that integrates with OpenAI-compatible APIs to provide conversational AI capabilities. The bot supports:
- OpenAI/Ollama compatible API integration
- Web content fetching and context extraction
- YouTube video caption summarization
- DuckDuckGo search integration
- Mars language text transformation

## Common Development Commands

### Environment Setup
```bash
# Create virtual environment
uv venv --python 3.12

# Install dependencies
uv pip install -r requirements.txt
```

### Running the Bot
```bash
# Development mode - direct execution
uv run --env-file settings.env guard.py

# Production mode - with Docker
docker-compose up -d
```

### Code Formatting
```bash
# Format code (if dev dependencies are installed)
black .
isort .
```

## Architecture

### Core Components

- **main.py**: Primary bot logic with message handling, API calls, and command processing
- **guard.py**: Process manager that restarts the bot on crashes using fork/waitpid
- **settings.py**: Environment configuration management
- **clean.py**: HTML content cleaning utilities using BeautifulSoup
- **youtube.py**: YouTube video caption extraction using yt-dlp
- **spark.py**: Mars language text transformation utilities

### Key Design Patterns

1. **Process Management**: Uses Unix fork() for crash recovery and automatic restart
2. **Async Processing**: All Telegram handlers use asyncio for non-blocking operations
3. **Streaming API**: Supports streaming responses from OpenAI-compatible APIs
4. **Caching**: YouTube captions are cached locally in ./cache/ directory
5. **Error Handling**: Comprehensive error handling for network failures and API errors

### Environment Variables

Configure in `settings.env`:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `API_URL`: OpenAI-compatible API endpoint (default: NVIDIA API)
- `API_SECRET`: API authentication key
- `MODEL_NAMES`: Comma-separated list of models to try (fallback support)
- `BOT_NAME`: Bot username for mention detection
- `DEBUG`: Enable debug logging

### Message Flow

1. Telegram message received → main.py:handle_mention()
2. URL detection → content fetching (web/YouTube)
3. Search command → DuckDuckGo integration
4. Context preparation → API request with streaming
5. Response chunking → Telegram message delivery (4000 char limit)

### API Integration

The bot supports multiple model fallback - if the first model fails, it tries the next one in the `MODEL_NAMES` list. Streaming responses are chunked and sent incrementally to provide real-time feedback.

## Testing

No formal test suite is currently implemented. Manual testing is done through Telegram interactions.

## Dependencies

- python-telegram-bot: Telegram Bot API wrapper
- yt-dlp: YouTube video processing
- beautifulsoup4: HTML content cleaning
- duckduckgo-search: Web search functionality
- httpx: Async HTTP client for API calls
- primp: HTTP client with browser impersonation
