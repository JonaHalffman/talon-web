# E2E Email Testing for Talon-Web

This directory contains tools to fetch real emails from your O365 shared mailbox and process them through talon-web to analyze quotation extraction results.

## Prerequisites

1. **Docker** installed and running
2. **Python 3.9+** with pip
3. **Azure AD access** to register an application

---

## Step 1: Azure AD Application Setup

### 1.1 Register an Application

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Name it `talon-web-e2e`
5. Supported account types: **Single tenant** (your organization)
6. Click **Register**
7. Note the following values:
   - **Application (client) ID** → `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → `AZURE_TENANT_ID`

### 1.2 Create Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Description: `e2e-tests`
4. Expires: Choose appropriate (12 months recommended)
5. Click **Add**
6. **Copy the secret value** immediately → `AZURE_CLIENT_SECRET`

### 1.3 Grant API Permissions

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Application permissions** (not Delegated)
5. Add: `Mail.Read`
6. Click **Grant admin consent** (or request from your admin)

### 1.4 Grant Shared Mailbox Access

For app-only authentication to access a shared mailbox:

**Option A: Exchange Admin Center (Recommended)**
1. Go to [Exchange Admin Center](https://admin.exchange.microsoft.com)
2. Navigate to **Recipients** → **Shared mailboxes**
3. Open your shared mailbox (`info@elektrotechnieker.be`)
4. Go to **Mailbox delegation**
5. Under **Send as** or **Full access**, add your app's service principal

**Option B: PowerShell**
```powershell
# Install Exchange Online module if needed
Install-Module -Name ExchangeOnlineManagement

Connect-ExchangeOnline

# Grant full access to shared mailbox
Add-MailboxPermission -Identity "info@elektrotechnieker.be" -User "<your-app-service-principal>" -AccessRights FullAccess

# For "Send as" access
Add-RecipientPermission -Identity "info@elektrotechnieker.be" -Trustee "<your-app-service-principal>" -AccessRights SendAs
```

The service principal is identified by your app's Client ID.

---

## Step 2: Configure Environment

```bash
cd e2e_tests

# Copy the example environment file
cp .env.example .env

# Edit .env with your Azure AD credentials
nano .env  # or code .env, or your preferred editor
```

Fill in your `.env` file:
```env
AZURE_TENANT_ID=your-tenant-id-from-azure
AZURE_CLIENT_ID=your-client-id-from-azure
AZURE_CLIENT_SECRET=your-client-secret-from-azure
SHARED_MAILBOX_EMAIL=info@elektrotechnieker.be
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4: Test Authentication

```bash
python azure_auth.py
```

Expected output:
```
INFO: Successfully authenticated with app-only flow
INFO: Connected as: Your Name
INFO: Your email: your.email@yourdomain.com

Authentication successful!
```

If you get errors, check:
- Credentials are correct in `.env`
- App has `Mail.Read` permission
- Admin consent was granted
- Mailbox access was configured

---

## Step 5: Fetch Emails

### Fetch from Inbox
```bash
python fetch_emails.py --folder Inbox --limit 10
```

### Fetch from Sent Items
```bash
python fetch_emails.py --folder "Sent Items" --limit 10
```

### Fetch with filters
```bash
# Only unread emails
python fetch_emails.py --folder Inbox --unread-only

# Date range
python fetch_emails.py --folder Inbox --date-from 2024-01-01 --date-to 2024-03-31

# Skip attachments (faster)
python fetch_emails.py --folder Inbox --no-attachments
```

Emails are saved to:
- `outputs/originals/` - .eml files
- `outputs/originals/metadata.json` - email metadata
- `outputs/originals/*_attachments/` - email attachments

---

## Step 6: Process Emails

```bash
python process_emails.py
```

This will:
1. Start the talon-web Docker container (if not running)
2. Extract HTML from each .eml file
3. Send HTML to talon-web's `/reply/extract_from_html` endpoint
4. Save results to `outputs/processed/`
5. Generate a summary report
6. Stop the Docker container

### Options
```bash
# Don't start Docker (assume already running)
python process_emails.py --no-start-docker

# Don't stop Docker after processing
python process_emails.py --no-stop-docker

# Custom directories
python process_emails.py --input-dir ./my-emails --output-dir ./results
```

---

## Step 7: Review Results

### Summary Report
```bash
cat outputs/reports/summary.json
```

Example output:
```json
{
  "generated_at": "2024-01-15T10:30:00Z",
  "total_processed": 10,
  "successful": 8,
  "failed": 2,
  "total_original_chars": 154320,
  "total_extracted_chars": 45678,
  "avg_processing_time_ms": 45
}
```

### Individual Results
Check `outputs/processed/result_*.json` files:
```json
{
  "success": true,
  "subject": "Quote Request from Customer",
  "original_length": 15432,
  "extracted_length": 2847,
  "ratio": 0.18,
  "processing_time_ms": 45,
  "extracted_text": "Hi,\n\nI'd like to request a quote for..."
}
```

### Failed Emails
Check for errors in failed results:
```json
{
  "success": false,
  "error": "Request timeout",
  "subject": "..."
}
```

---

## Troubleshooting

### Authentication Errors

**Error: "AADSTS700016: Application not found"**
- Check your `AZURE_CLIENT_ID` is correct
- Verify the app is registered in your Azure AD tenant

**Error: "403 Forbidden"**
- App doesn't have `Mail.Read` permission
- Admin consent not granted
- Mailbox access not configured for shared mailbox

**Error: "403 Authorization_RequestDenied"**
- Insufficient privileges to access the shared mailbox
- Check Exchange admin center permissions

### Processing Errors

**"No HTML body found"**
- Email may be plain text only
- Email may have unusual encoding
- Check the original .eml file

**"Request timeout"**
- talon-web may be slow or stuck
- Check Docker logs: `docker logs talon-web-e2e`
- Restart: `docker restart talon-web-e2e`

### Docker Issues

**Build fails**
```bash
# Check Dockerfile is valid
cat ../Dockerfile

# Build manually
cd ..
docker build -t talon-web .
```

**Container won't start**
```bash
# Check logs
docker logs talon-web-e2e

# Check port not in use
netstat -an | grep 5000
```

---

## Files Overview

| File | Description |
|------|-------------|
| `azure_auth.py` | MSAL authentication helper |
| `fetch_emails.py` | Download emails from O365 |
| `process_emails.py` | Process emails through talon-web |
| `config.yaml` | Test configuration |
| `docker-compose.e2e.yml` | Docker compose for talon-web |
| `.env.example` | Environment variables template |

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  1. Setup Azure AD App (once)                              │
│     - Register app, get credentials                        │
│     - Grant Mail.Read permission                           │
│     - Grant mailbox access                                 │
├─────────────────────────────────────────────────────────────┤
│  2. Configure (.env)                                        │
│     - Copy .env.example to .env                           │
│     - Fill in credentials                                 │
├─────────────────────────────────────────────────────────────┤
│  3. Fetch emails                                           │
│     python fetch_emails.py --folder Inbox --limit 20       │
├─────────────────────────────────────────────────────────────┤
│  4. Process emails                                         │
│     python process_emails.py                              │
├─────────────────────────────────────────────────────────────┤
│  5. Review results                                          │
│     cat outputs/reports/summary.json                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Notes

- **Don't commit `.env`** - Add to `.gitignore`
- **Credentials are sensitive** - Store securely
- **Real email data** - May contain PII; handle appropriately
- **Token refresh** - Client credentials don't expire (unless revoked)

For production use, consider:
- Rotating client secrets regularly
- Using managed identities where possible
- Implementing proper secret storage
