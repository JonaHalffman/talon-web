# Roadmap

## Goal
Transform raw HTML emails into clean conversation threads for helpdesk applications.

## Current Status: v0.7.0

### Implemented Features

| Feature | Description |
|---------|-------------|
| Quote Extraction | Removes quoted content from replies |
| Signature Detection | Separates signatures from message body |
| Sender/Date Parsing | Extracts metadata from email headers |
| Thread Detection | Identifies multi-message threads |
| Subject Processing | Removes RE:/FW: prefixes, detects changes |
| Thread Break Detection | Flags when subject changes = new conversation |
| HTML Sanitization | Removes scripts, trackers, dangerous elements |
| Multi-format Support | O365, Outlook, Gmail, Apple, Yahoo, Word |

### E2E Test Results

- 29 real emails processed from O365 shared mailbox
- 13 (45%) - Good extraction (<30%) - actual replies
- 2 (7%) - Partial extraction (30-70%)
- 14 (48%) - No extraction (>70%) - system notifications (correct behavior)

## What's Next

### High Priority
1. **Performance optimization** - Benchmark large emails
2. **Gmail/Yahoo preprocessors** - Improve extraction for these formats

### Medium Priority  
1. **Attachment metadata** - Extract file info from emails
2. **Monitoring** - Logging, metrics
3. **Deployment** - Docker Compose, health checks

### Future Ideas
- Custom pre-processors via config
- Gmail API native support

## Version History

- **v0.7.0** - Subject processing, thread break detection
- **v0.6.0** - O365 nested divs, word-generated detection
- **v0.5.0** - Signature handling, thread detection
- **v0.4.0** - Sender/date metadata extraction
- **v0.3.0** - Confidence scoring, error handling
- **v0.2.0** - Pre/post-processing, format detection
- **v0.1.0** - Basic talon integration
