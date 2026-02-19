# talon-web

**Email Thread Processor** - Transforms raw HTML emails into clean conversation threads for helpdesk applications (Freshdesk, Intercom, Zendesk, etc.).

## What It Does

```
Raw HTML Email (Microsoft Graph / Gmail API)
         │
         ▼
┌─────────────────────────────────────────┐
│             talon-web                      │
│  • Extracts newest reply only            │
│  • Removes quoted content                 │
│  • Separates signatures                   │
│  • Parses sender/date metadata           │
│  • Detects thread breaks                  │
└─────────────────────────────────────────┘
         │
         ▼
Clean Thread Data (JSON + HTML + Plain Text)
```

## Why This Service

When customers reply to emails, the original message gets quoted. Helpdesk systems need only the **newest reply**:

- Extract reply from quoted threads
- Get both HTML and plain text output
- Separate signatures from message body
- Detect when subject changes (new thread)
- Parse sender info and timestamps
- Sanitize HTML (remove scripts, trackers)

## Quick Start

```bash
# Build and run with Docker
docker build -t talon-web .
docker run -p 5000:5000 talon-web
```

## API Usage

```bash
curl -X POST http://localhost:5000/reply/extract_from_html \
  -H "Content-Type: text/html" \
  -d '<html><body>Your email HTML here</body></html>'
```

### Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `include_signature` | true | Include signature in output |
| `full_thread` | false | Return all thread messages |

## Response Fields

| Field | Description |
|-------|-------------|
| `html` | Clean HTML reply (no quotes) |
| `text` | Plain text version |
| `original_html` | Original for archival |
| `quoted_html` | Extracted quoted content |
| `signature` | Separated signature |
| `metadata` | Sender, date, thread, subject info |

### Metadata Fields

```json
"metadata": {
  "has_reply": true,
  "is_reply": true,
  "is_forward": false,
  "sender": {"name": "", "email": "", "raw": ""},
  "date": {"raw": "", "parsed": "", "timestamp": null},
  "thread": {"is_thread": false, "message_count": 1},
  "subject": {"original": "", "clean": "", "prefix": "", "is_reply": false},
  "subject_change": {"subject_changed": false, "thread_break": false}
}
```

## Supported Formats

| Format | Status |
|--------|--------|
| O365 Web | ✅ |
| Outlook Desktop | ✅ |
| Gmail | ✅ |
| Apple Mail | ✅ |
| Yahoo | ✅ |
| Word-generated | ✅ |

## Architecture

- **Input**: Raw HTML from email APIs (Microsoft Graph, Gmail API)
- **Processing**: Pre-processing → Talon ML → Post-processing
- **Output**: Structured JSON with HTML/plain text

## Development

```bash
# Run tests
pytest

# Run locally
python app.py

# Run with gunicorn
gunicorn app:app --bind=0.0.0.0:5000 --workers=4
```
