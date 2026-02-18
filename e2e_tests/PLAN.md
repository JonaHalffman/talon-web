# E2E Testing Plan for New Agent Session

## Current Status

### What Was Accomplished
- Created `e2e_tests/` directory with:
  - `azure_auth.py` - MSAL authentication for Microsoft Graph API
  - `fetch_emails.py` - Downloads emails from O365 shared mailbox
  - `process_emails.py` - Processes emails through talon-web API
  - `config.yaml` - Configuration file
  - `.env` / `.env.example` - Environment variables

- Successfully authenticated to Microsoft Graph API
- Fetched emails from O365 shared mailbox

### Key Finding from Previous Investigation
Talon quotation extraction has limitations with specific O365 HTML structures:
- O365 emails have splitter + quoted content in separate `<div>` elements
- Talon's algorithm expects them in the same parent container
- This is a talon library limitation, not a Graph API issue

### Changes Made
- Modified `fetch_emails.py` to support `--html-only` flag
  - Uses Graph API `body` endpoint directly instead of downloading .eml files
  - Saves HTML to `outputs/html_bodies/` directory
- Modified `process_emails.py` to handle both EML and HTML modes
  - Reads from `html_file` in metadata (new) or falls back to EML extraction

## Commands to Run

### Step 1: Fetch emails with HTML only (no .eml files)
```bash
cd e2e_tests
python fetch_emails.py --mailbox info@elektrotechnieker.be --folder "Sent Items" --limit 10 --html-only
```

### Step 2: Process emails through talon-web
```bash
cd e2e_tests
python process_emails.py
```

### Step 3: Check results
```bash
cat outputs/reports/summary.json
```

## Key Files Modified
- `e2e_tests/fetch_emails.py` - Added `get_html_body()` method and `--html-only` flag
- `e2e_tests/process_emails.py` - Updated to read HTML files directly

## Next Steps for New Agent

1. **Test the new flow**:
   - Run `fetch_emails.py --html-only` to get HTML directly from Graph API
   - Run `process_emails.py` to test talon extraction
   - Compare results with previous EML-based approach

2. **If talon still doesn't work**:
   - Try different email sources (Inbox vs Sent Items)
   - Consider using quotequail library instead of talon
   - Or implement custom post-processing for Outlook-style quotations

3. **Alternative approaches**:
   - Use Graph API's `preview` endpoint
   - Use delta sync for incremental processing
   - Add caching to avoid re-fetching

## Environment Requirements
- Python dependencies in `e2e_tests/requirements.txt`
- Docker running (for talon-web container)
- Azure AD app with:
  - `Mail.Read` application permission
  - Access to shared mailbox granted in Exchange admin center
