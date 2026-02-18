# talon-web

A Flask microservice that transforms raw HTML emails into clean conversation threads for helpdesk-style applications.

## What It Does

```
Raw HTML Email (from Microsoft Graph / Gmail API)
         │
         ▼
┌─────────────────────────────────────┐
│       talon-web                      │
│  • Extracts the new reply            │
│  • Removes quoted content            │
│  • Separates signatures              │
│  • Detects email client format      │
└─────────────────────────────────────┘
         │
         ▼
Clean Conversation Data (JSON)
```

## Quick Start

```bash
# Run with Docker
docker build -t talon-web .
docker run -p 5000:5000 talon-web

# Or run locally
pip install -r requirements.txt
python app.py
```

## API Usage

```bash
curl -X POST http://localhost:5000/reply/extract_from_html \
  -H "Content-Type: text/html" \
  -d '<html><body>Your email HTML here</body></html>'
```

## What You Get

| Field | Description |
|-------|-------------|
| `html` | Clean HTML reply (no quotes, no scripts) |
| `text` | Plain text version |
| `original_html` | Original for archival |
| `quoted_html` | Extracted quoted content |
| `signature` | Separated signature |
| `metadata` | Sender, date, thread info |

## Features

- **Quote Extraction** - Removes quoted content from replies
- **Signature Detection** - Separates signatures from message body
- **Sender/Date Parsing** - Extracts metadata from email headers
- **Thread Detection** - Identifies multi-message threads
- **HTML Sanitization** - Removes scripts, trackers, dangerous elements
- **Multi-format Support** - O365, Outlook Desktop, Gmail, Apple Mail, Yahoo

## Supported Email Clients

| Client | Status |
|--------|--------|
| O365 Web | ✅ |
| Outlook Desktop | ✅ |
| Gmail | ✅ |
| Apple Mail | ✅ |
| Yahoo | ✅ |
| Word-generated | ✅ |

## Configuration

Query parameters:
- `include_signature=true|false` - Include or exclude signature in output

## Development

```bash
# Run tests
pytest

# Run with gunicorn
gunicorn app:app --bind=0.0.0.0:5000 --workers=4
```
