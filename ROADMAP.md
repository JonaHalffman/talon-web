# Roadmap: Email Thread Extraction Service

## Vision

Transform raw HTML emails from Microsoft Graph API / Gmail API into clean, structured conversation messages for Freshdesk/Intercom/Zendesk-like thread views with:
- Sanitized HTML output
- Separated quotes for thread reconstruction
- Extracted signatures
- Attachment metadata

## Current State (v0.1.0)

### ✅ Completed
- Basic quotation extraction with talon
- Pre-processing for O365 and Outlook Desktop
- JSON API with ratio reporting
- Plain text output option
- Docker containerization
- E2E testing with real O365 emails

### 📊 Test Results
- **29 emails tested**: 18+ successfully extracted quotations
- **Improvement**: 27% reduction in extracted content (more quote removal)
- **Supported formats**: Gmail, Apple Mail, Outlook Desktop, O365

---

## Milestones

### Phase 1: Core Extraction (v0.2.0)
**Goal**: Reliable quotation extraction for all supported email formats

- [ ] **O365 Complete Fix**: Handle all O365 nested div structures
- [ ] **Gmail Support**: Full Gmail API HTML extraction
- [ ] **Format Detection**: Auto-detect email client format
- [ ] **Confidence Scoring**: Return confidence level for extraction
- [ ] **Error Handling**: Better error messages for edge cases
- [ ] **HTML Sanitization**: Strip scripts, tracking pixels, dangerous elements

### Phase 2: Message Parsing (v0.3.0)
**Goal**: Extract full message metadata

- [ ] **Sender Extraction**: Parse sender from email headers
- [ ] **Timestamp Extraction**: Parse received date from HTML
- [ ] **Subject Handling**: Pass through subject for threading
- [ ] **Reply Detection**: Flag if email is a reply (RE:, FW:, etc.)
- [ ] **Attachment Metadata**: Extract attachment info (name, size, type)

### Phase 3: Signature Handling (v0.4.0)
**Goal**: Properly handle email signatures

- [ ] **Signature Detection**: Identify common signature patterns
- [ ] **Signature Separation**: Return signature as separate field
- [ ] **Configurable Handling**: Option to include/exclude signatures
- [ ] **Corporate Signatures**: Handle complex HTML signatures

### Phase 4: Thread Support (v0.5.0)
**Goal**: Handle multi-message emails

- [ ] **Thread Splitting**: Detect multiple messages in single email
- [ ] **Message Ordering**: Identify newest vs older messages
- [ ] **Forward Detection**: Handle forwarded emails differently
- [ ] **Full Thread Output**: Option to return full thread with quotes

### Phase 5: Output Formats (v0.6.0)
**Goal**: Multiple output formats for different helpdesk systems

- [ ] **Freshdesk Format**: conversation.reply format
- [ ] **Intercom Format**: conversation_part format
- [ ] **Zendesk Format**: ticket comment format
- [ ] **Unified Format**: Internal standard format

### Phase 6: Additional Sources (v0.7.0)
**Goal**: Support more email sources

- [ ] **Gmail API Integration**: Full Gmail support
- [ ] **IMAP Support**: Generic IMAP connector
- [ ] **SendGrid Inbound**: Handle SendGrid inbound emails

### Testing (Ongoing)
**Goal**: Comprehensive test coverage

- [ ] **Unit Tests**: Test individual pre/post-processors
- [ ] **Integration Tests**: Test API endpoints
- [ ] **E2E Tests**: Test with real O365 and Gmail emails
- [ ] **CI Integration**: Run tests on commit/PR
- [ ] **Test Fixtures**: Store sample emails for regression testing

---

## Technical Decisions

### 1. Pre vs Post Processing

**Decision**: Use both pre and post processing in the same Docker container.

Rationale:
- Pre-processing: Normalize HTML before talon runs (fixes O365 issues)
- Post-processing: Clean talon output (sanitize, extract signatures)
- Single container: Simpler deployment, no external dependencies

### 2. Output Format

**Decision**: JSON with separate fields for different use cases.

```json
{
  "success": true,
  "html": "<p>Reply content...</p>",
  "text": "Reply content...",
  "original_html": "<html>...original...</html>",
  "quoted_html": "<blockquote>...quotes...</blockquote>",
  "signature": "John Doe\nCEO\n...",
  "attachments": [{"name": "file.pdf", "size": 1234, "content_type": "application/pdf"}],
  "ratio": 0.05,
  "format_detected": "o365",
  "metadata": {
    "has_reply": true,
    "is_forward": false,
    "is_reply": true
  }
}
```

Rationale:
- Separate html/text for different consumers
- original_html + quoted_html for thread reconstruction
- signature separate field as requested
- ratio indicates extraction confidence

### 3. HTML Sanitization

**Decision**: Always sanitize HTML output.

Sanitized:
- `<script>` tags and inline JavaScript
- 1x1 tracking pixels
- Dangerous elements (iframes, objects, etc.)

Rationale:
- Production systems need clean HTML
- Prevent email-born security issues
- 1-pixel trackers are privacy concerns

### 4. Thread Handling Strategy

**Decision**: Handle thread splitting at the application level, not in talon.

Rationale:
- Talon extracts the NEWEST message (correctly)
- For multi-message emails, detect and split using markers
- Provide both "new reply only" and "full thread" options

### 5. Signature Strategy

**Decision**: Detect and separate signatures as a separate field.

Common patterns:
- `--` followed by name/contact info
- Multiple newlines at end
- Contact info (phone, email, company)
- Social media links
- `<div class="signature">` or similar

### 6. Deduplication

**Decision**: NOT handled in this service.

Rationale:
- This service focuses on content extraction, not data integrity
- Use `Message-ID` header at email ingestion layer (Graph/Gmail API)
- Simplifies service, no state/storage needed

---

## Integration Architecture

### Email Connector → talon-web → Helpdesk

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Email Connector │     │    talon-web     │     │    Helpdesk      │
│  (Graph/Gmail)  │     │  (This Service)  │     │  (Integration)   │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │  Raw HTML             │                        │
         │───────────────────────>│                        │
         │                        │  JSON Response         │
         │                        │  - html (clean)        │
         │                        │  - quoted_html         │
         │                        │  - signature           │
         │                        │  - attachments         │
         │                        │───────────────────────>│
         │                        │                        │
```

### Deduplication Flow (Recommended)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Microsoft 365  │     │  Email Ingestion │     │    talon-web     │
│  Graph API      │     │  Service        │     │  (This Service)  │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │  Fetch emails          │  Check Message-ID     │
         │───────────────────────>│  Skip if duplicate    │
         │                        │───────────────────────>│
         │                        │  Unique emails only   │
```

---

## Testing Strategy

### Test Categories

1. **Unit Tests** (`tests/`)
   - Individual pre/post-processor functions
   - Signature detection
   - HTML sanitization
   - Format detection

2. **Integration Tests** (`tests/`)
   - API endpoint responses
   - JSON schema validation
   - Error handling

3. **E2E Tests** (`e2e_tests/`)
   - Real O365 email processing
   - Real Gmail processing (future)
   - Batch processing
   - Performance benchmarking

### Test Fixtures

Store sample emails in `tests/fixtures/`:
- `gmail_simple_reply.html` - Gmail with reply
- `apple_mail_reply.html` - Apple Mail with reply
- `outlook_desktop_thread.html` - Outlook Desktop thread
- `o365_forward.html` - O365 forwarded email
- `signature_simple.html` - Email with signature
- `o365_nested_divs.html` - O365 complex nested structure

---

## Open Questions

1. **Thread Handling**: How to handle 10+ message threads?
   - Option A: Extract only newest (simpler)
   - Option B: Split all (more complex, more data)

2. **Signature Storage**: Include signatures in reply or separate?
   - Current: Separate field (as requested)

3. **Reply Detection**: Use ratio threshold or heuristic?
   - Current: ratio < 1.0
   - Future: Also check for "RE:" prefix

4. **Performance**: Large HTML emails?
   - Current: < 100ms per email
   - Need: Benchmarks for production

---

## Contributing

See [AGENTS.md](AGENTS.md) for development guidelines.

### Adding New Email Formats

1. Add pre-processor in `preprocessing.py`
2. Add to `PRE_PROCESSORS` list
3. Add test case in `tests/fixtures/`
4. Run E2E tests to verify

### Adding New Output Formats

1. Add post-processor in `postprocessing.py`
2. Add new endpoint in `app.py`
3. Add tests
4. Document in README.md
