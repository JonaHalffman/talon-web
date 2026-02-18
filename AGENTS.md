# AGENTS.md

Guidelines for AI agents working in this repository.

## Project Overview

A Flask microservice that extracts email quotations and transforms raw HTML emails into structured conversation messages for Freshdesk/Intercom/Zendesk-like thread views.

**Primary Purpose**: Extract ONLY the new message (reply) from an email thread, removing quotations and signatures.

## Architecture

```
Input (Graph/Gmail API HTML) → Pre-processing → Talon → Post-processing → JSON Output
```

See [README.md](README.md) for full architecture diagram.

## Build & Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (development)
python app.py

# Run with gunicorn (production)
gunicorn app:app --bind=0.0.0.0:5000 --log-level=debug --workers=4

# Docker build and run
docker build -t talon-web .
docker run -p 5000:5000 talon-web
```

## Testing

```bash
# Install pytest
pip install pytest pytest-flask

# Run all tests
pytest

# Run a single test file
pytest tests/test_app.py

# Run a single test function
pytest tests/test_app.py::test_extract_from_html

# Run with verbose output
pytest -v
```

### E2E Testing

```bash
cd e2e_tests

# Update .env with Azure AD credentials
cp .env.example .env

# Fetch emails from O365
python fetch_emails.py --html-only

# Process emails through talon-web
python process_emails.py
```

## Code Style Guidelines

### Python Style

- Follow **PEP 8** conventions
- Use **4 spaces** for indentation (no tabs)
- Maximum line length: **88 characters** (Black default) or 100
- Use **double quotes** for strings unless single quotes are needed

### Imports

Order imports in three groups with a blank line between each:
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
import os
import re

from flask import Flask, request
from talon import quotations

from preprocessing import apply_preprocessors
from postprocessing import apply_postprocessors
```

Sort imports alphabetically within each group.

### Pre/Post Processing

Add new email format handlers in:
- `preprocessing.py` - HTML normalization before talon
- `postprocessing.py` - Clean/transform talon output

```python
# In preprocessing.py
def remove_custom_format(html: str) -> str:
    """Remove custom email client quoted content."""
    return html

# Add to PRE_PROCESSORS list
PRE_PROCESSORS = [
    detect_email_client,
    remove_outlook_web_reply_marker,
    remove_o365_reply_div,
    remove_custom_format,
]
```

### Naming Conventions

- `snake_case` for variables, functions, and modules
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Avoid single-letter variable names except for loop indices

### Type Hints

Add type hints for function signatures (optional but encouraged):

```python
from typing import Optional

def extract_from_html(html: str) -> Optional[str]:
    ...
```

### Error Handling

- Use specific exceptions, avoid bare `except:`
- Handle expected errors gracefully with appropriate HTTP status codes
- Log errors for debugging

```python
from flask import abort

try:
    result = process_data(data)
except ValueError as e:
    app.logger.error(f"Invalid data: {e}")
    abort(400, description="Invalid input data")
```

### Flask-Specific Guidelines

- Use `@app.route()` decorators for endpoints
- Return `Response` objects for non-JSON responses
- Use `request.get_data()` for raw request body
- Add docstrings to route handlers

## Linting & Formatting (Recommended Setup)

```bash
# Install tools
pip install black flake8 mypy

# Format code
black .

# Lint
flake8 .

# Type check
mypy .
```

## Docker Guidelines

- Use multi-stage builds for smaller images
- Pin base image versions (e.g., `python:3.10-slim-bullseye`)
- Use `--no-install-recommends` with apt-get
- Clean up apt cache after install
- Copy files with `--link` for better layer caching

```dockerfile
# Copy new modules
COPY --link preprocessing.py .
COPY --link postprocessing.py .
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reply/extract_from_html` | POST | Extracts quotations, returns JSON with full response |
| `/reply/extract_from_html/plain` | POST | Extracts quotations, returns JSON with plain text |
| `/health` | GET | Health check endpoint returns "OK" |

### Response Format

```json
{
  "success": true,
  "html": "<p>Clean reply...</p>",
  "text": "Clean reply...",
  "original_html": "<html>...original...</html>",
  "quoted_html": "<blockquote>...quoted...</blockquote>",
  "signature": "John Doe\nCEO\n...",
  "attachments": [{"name": "file.pdf", "size": 1234, "content_type": "application/pdf"}],
  "original_length": 1000,
  "extracted_length": 500,
  "ratio": 0.5,
  "format_detected": "o365",
  "metadata": {
    "has_reply": true,
    "is_forward": false,
    "is_reply": true
  }
}
```

### Example

```bash
curl -X POST http://localhost:5000/reply/extract_from_html \
  -H "Content-Type: text/html" \
  -d '<html><body>Reply<blockquote>Quoted</blockquote></body></html>'
```

## Dependencies

- `Flask~=2.2.3` - Web framework
- `gunicorn~=20.1.0` - WSGI server
- `talon` - Email quotation extraction (installed in Dockerfile)

## Environment Variables

None currently defined. Flask uses:
- `FLASK_ENV` - Set to `development` for debug mode
- `FLASK_APP` - Set to `app.py`

## Security Features

The service includes HTML sanitization:
- Removes `<script>` tags and inline JavaScript
- Removes 1x1 tracking pixels
- Strips potentially dangerous HTML elements

Always sanitize output - see `postprocessing.py` for implementation.

## Supported Email Clients

| Client | Format | Pre-processor Needed |
|--------|--------|---------------------|
| O365 Web | `divRplyFwdMsg` nested divs | Yes |
| Outlook Desktop | `border-top:solid` | Yes |
| Gmail | `<blockquote class="gmail_quote">` | No |
| Apple Mail | `<blockquote type="cite">` | No |
| Yahoo | `<blockquote>` | No |

## Deduplication

**NOT handled in this service.** Email deduplication should be done at the email ingestion layer using the `Message-ID` header before sending to this service.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed feature timeline.

### Priority Order (Current)

1. Fix O365 extraction for all nested div structures
2. Add HTML sanitization (scripts, tracking pixels)
3. Add signature extraction as separate field
4. Add Gmail API support
5. Add attachment metadata extraction
6. Add thread reconstruction (original_html + quoted_html)
