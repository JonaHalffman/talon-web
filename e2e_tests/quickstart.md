# Talon-Web E2E Testing Quickstart

This guide gets you from zero to processing real O365 emails in ~15 minutes.

## Prerequisites

- Docker Desktop running
- Python 3.9+ with pip
- Azure AD admin access (for app registration)

---

## Step 1: Register Azure App

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **New registration**
   - Name: `talon-web-e2e`
   - Supported account types: **Single tenant**
3. Register → note **Application (client) ID** and **Directory (tenant ID)**
4. Go to **Certificates & secrets** → **New client secret**
   - Description: `e2e-tests`
   - Expires: 12 months
5. Copy the **secret value** (not the ID)
6. Go to **API permissions** → **Add permission** → **Microsoft Graph** → **Application permissions**
7. Add `Mail.Read` → **Grant admin consent**

---

## Step 2: Grant Mailbox Access

1. Go to [Exchange Admin Center](https://admin.exchange.microsoft.com)
2. **Recipients** → **Shared mailboxes**
3. Open `info@elektrotechnieker.be`
4. **Mailbox delegation** → add your Azure app (use Client ID as user)

---

## Step 3: Configure

```bash
cd e2e_tests

# Copy environment template
cp .env.example .env

# Edit with your values
# AZURE_TENANT_ID=your-tenant-id
# AZURE_CLIENT_ID=your-client-id
# AZURE_CLIENT_SECRET=your-client-secret
# SHARED_MAILBOX_EMAIL=info@elektrotechnieker.be
```

---

## Step 4: Install & Test Auth

```bash
pip install -r requirements.txt
python azure_auth.py
```

Expected output:
```
INFO: Successfully authenticated with app-only flow
Authentication successful!
```

---

## Step 5: Fetch Emails

```bash
# Inbox
python fetch_emails.py --folder Inbox --limit 10

# Or Sent Items
python fetch_emails.py --folder "Sent Items" --limit 10
```

Files saved to `outputs/originals/`

---

## Step 6: Process Emails

```bash
python process_emails.py
```

This will:
1. Start talon-web Docker container
2. Process each email through the extraction API
3. Save results to `outputs/processed/`
4. Generate summary report

---

## Step 7: Review Results

```bash
cat outputs/reports/summary.json
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `AADSTS700016: Application not found` | Check `AZURE_CLIENT_ID` in `.env` |
| `403 Forbidden` | Grant `Mail.Read` permission + admin consent |
| `403 Authorization_RequestDenied` | Grant shared mailbox access in Exchange admin center |
| "No HTML body found" | Email is plain text (not an error) |

---

## Files Overview

| File | Purpose |
|------|---------|
| `azure_auth.py` | Authenticate with Microsoft Graph |
| `fetch_emails.py` | Download emails from O365 |
| `process_emails.py` | Process through talon-web |
| `config.yaml` | Test configuration |
| `docker-compose.e2e.yml` | Docker for talon-web |
