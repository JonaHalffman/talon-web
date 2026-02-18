# Roadmap

## Goal
Transform raw HTML emails into clean conversation threads for helpdesk applications.

## Current Status: v0.7.0

### Core Features Implemented

| Feature | Status |
|---------|--------|
| Quote extraction | ✅ |
| Signature detection | ✅ |
| Sender/date parsing | ✅ |
| Thread detection | ✅ |
| HTML sanitization | ✅ |
| Multi-format support | ✅ |
| O365 nested div handling | ✅ |
| Word-generated detection | ✅ |
| Subject line processing | ✅ |
| Thread break detection | ✅ |

### Subject Processing Features

- **clean_subject()** - Removes RE:, FW:, AW:, etc. prefixes
- **detect_subject_change()** - Detects when subject changes in thread
- Multi-language support (Dutch, German, French, etc.)

### E2E Test Results

- 29 real emails processed
- 13 (45%) - Good extraction (<30%) - actual replies
- 2 (7%) - Partial extraction (30-70%)
- 14 (48%) - No extraction (>70%) - system notifications

### Format Detection

- outlook_desktop: 11
- word_generated: 8
- unknown: 9
- apple_mail: 1

## What's Next

### Improvements

1. **Performance** - Benchmark and optimize for large emails
2. **More preprocessors** - Gmail, Yahoo, Apple Mail handling
3. **Testing** - More real-world E2E tests

### Production Readiness

1. **Deployment** - Docker compose, health checks
2. **Monitoring** - Logging, metrics
3. **API versioning** - Stable API contract

### Future Ideas

- Attachment handling (extract metadata)
- Gmail API native support
- Custom pre-processors via config

## Completed Phases

- **v0.1.0** - Basic talon integration
- **v0.2.0** - Pre/post-processing, format detection
- **v0.3.0** - Confidence scoring, error handling
- **v0.4.0** - Sender/date metadata extraction
- **v0.5.0** - Signature handling, thread detection
- **v0.6.0** - O365 nested divs, word-generated detection
- **v0.7.0** - Subject line processing, thread break detection
