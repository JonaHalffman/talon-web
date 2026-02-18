# talon-web

A Flask microservice that extracts email quotations and transforms raw HTML emails into structured conversation messages for Freshdesk/Intercom/Zendesk-like thread views.

## Purpose

This service receives raw HTML emails from email connectors (Microsoft Graph API, Gmail API) and returns clean, structured data:

1. **Clean HTML** - Sanitized HTML without quotes, scripts, or trackers
2. **Extracted quotes** - Original quoted content for thread reconstruction
3. **Signatures** - Separated from content for clean display
4. **Thread data** - Metadata for threading conversations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT                                    │
│  Microsoft Graph API / Gmail API                                  │
│  Raw HTML email body                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PRE-PROCESSING                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │ Auto-detect     │  │ O365 Reply Div  │  │ Outlook Desk  │ │
│  │ Email Client    │  │ Removal         │  │ Border Strip  │ │
│  └─────────────────┘  └─────────────────┘  └───────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TALON QUOTATION EXTRACTION                   │
│  Extracts quoted content from various email clients              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POST-PROCESSING                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │ HTML            │  │ Signature       │  │ Sanitize      │ │
│  │ Sanitization   │  │ Detection       │  │ Scripts/Pix  │ │
│  └─────────────────┘  └─────────────────┘  └───────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUT                                  │
│  {                                                               │
│    "success": true,                                              │
│    "html": "<p>Clean reply...</p>",                            │
│    "text": "Clean reply...",                                    │
│    "original_html": "...",  // For thread reconstruction       │
│    "quoted_html": "...",     // Removed quotes                  │
│   ",       "signature": "... // Extracted signature            │
│    "attachments": [...],     // Attachment metadata             │
│    "ratio": 0.05,            // extraction confidence           │
│    "format_detected": "o365",                                   │
│    "metadata": {                                                │
│      "has_reply": true,                                        │
│      "is_forward": false,                                       │
│      "is_reply": true                                          │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### POST /reply/extract_from_html

Extract quotations and return clean HTML with full response data.

```bash
curl -X POST http://localhost:5000/reply/extract_from_html \
  -H "Content-Type: text/html" \
  -d '<html>...email body...</html>'
```

Response:
```json
{
  "success": true,
  "html": "<p>The actual reply content...</p>",
  "text": "The actual reply content...",
  "original_html": "<html>...full original...</html>",
  "quoted_html": "<blockquote>...quoted content...</blockquote>",
  "signature": "John Doe\nCEO\n...",
  "attachments": [
    {"name": "document.pdf", "size": 12345, "content_type": "application/pdf"}
  ],
  "original_length": 22717,
  "extracted_length": 1318,
  "ratio": 0.058,
  "format_detected": "o365",
  "metadata": {
    "has_reply": true,
    "is_forward": false,
    "is_reply": true
  }
}
```

### POST /reply/extract_from_html/plain

Same as above but returns plain text as primary output.

```bash
curl -X POST http://localhost:5000/reply/extract_from_html/plain \
  -H "Content-Type: text/html" \
  -d '<html>...email body...</html>'
```

### GET /health

Health check endpoint.

```bash
curl http://localhost:5000/health
# Returns: OK
```

## Configuration

No environment variables required. Configure via code in:
- `preprocessing.py` - Add new email format handlers
- `postprocessing.py` - Add output transformers
- `app.py` - Add new endpoints

## Development

### Run Locally
```bash
pip install -r requirements.txt
python app.py
```

### Run with Docker
```bash
docker build -t talon-web .
docker run -p 5000:5000 talon-web
```

### Run Tests
```bash
pytest
```

## Email Client Support

| Email Client | Format | Status | Notes |
|--------------|--------|--------|-------|
| O365 Web | `divRplyFwdMsg` nested divs | ✅ Supported | Full extraction |
| Outlook Desktop | `border-top:solid` | ✅ Supported | Pre-processing + Talon |
| Gmail | `<blockquote class="gmail_quote">` | ✅ Supported | Talon handles natively |
| Apple Mail | `<blockquote type="cite">` | ✅ Supported | Talon handles natively |
| Yahoo | `<blockquote>` | ✅ Supported | Talon handles some cases |
| Other | Various | 🔄 Extendable | Add pre-processors |

## Security Features

The service sanitizes HTML output:
- ✅ Removes `<script>` tags and inline JavaScript
- ✅ Removes 1x1 tracking pixels
- ✅ Strips potentially dangerous HTML elements

## Ratio Interpretation

The `ratio` field indicates quotation extraction success:

| Ratio | Meaning | Action |
|-------|---------|--------|
| 1.0 | No quoted content detected | Original email, no reply |
| 0.5 - 0.9 | Partial extraction | Check if reply is complete |
| 0.01 - 0.5 | Successful extraction | New reply extracted |
| < 0.01 | Very short reply | May need review |

## File Structure

```
talon-web/
├── app.py                    # Flask application & endpoints
├── preprocessing.py          # HTML pre-processing functions
├── postprocessing.py         # HTML post-processing functions
├── healthcheck.py            # Docker health check
├── requirements.txt          # Python dependencies
├── Dockerfile                # Multi-stage Docker build
├── README.md                 # This file
├── AGENTS.md                 # Developer guidelines
├── ROADMAP.md                # Feature roadmap
├── e2e_tests/                # End-to-end tests
│   ├── azure_auth.py         # Microsoft Graph authentication
│   ├── fetch_emails.py       # Email fetching from O365
│   ├── process_emails.py     # E2E processing script
│   ├── config.yaml           # Configuration
│   └── outputs/              # Test outputs
└── tests/                    # Unit & integration tests
    ├── test_app.py           # Flask endpoint tests
    ├── test_processors.py    # Pre/post-processor tests
    └── fixtures/             # Test email samples
```

## Deduplication Note

**Email deduplication is handled at the email ingestion layer**, not in this service. Use the `Message-ID` header from Microsoft Graph/Gmail APIs to deduplicate before sending to this service.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed feature timeline.

## License

MIT
