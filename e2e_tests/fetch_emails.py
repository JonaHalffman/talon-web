"""
Fetch emails from O365 shared mailbox using Microsoft Graph API.
Downloads emails as .eml files and saves attachments.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from azure_auth import AzureAuth

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class EmailFetcher:
    """Fetches emails from Microsoft Graph API."""

    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, auth: AzureAuth, config_path: str = None):
        self.auth = auth
        self.config = self._load_config(config_path)
        self.base_output_dir = Path(self.config.get("output", {}).get("base_dir", "outputs"))
        self.originals_dir = self.base_output_dir / self.config.get("output", {}).get("originals_subdir", "originals")
        self.html_dir = self.base_output_dir / "html_bodies"
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.html_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        if Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}

    def _build_query_params(self, limit: int = 10, folder: str = None,
                           date_from: str = None, date_to: str = None,
                           unread_only: bool = False) -> dict:
        """Build query parameters for the API request."""
        params = {
            "$top": limit,
            "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,sentDateTime,hasAttachments,isRead,internetMessageId",
            "$orderby": "receivedDateTime desc"
        }

        filters = []
        if date_from:
            filters.append(f"receivedDateTime ge {date_from}T00:00:00Z")
        if date_to:
            filters.append(f"receivedDateTime le {date_to}T23:59:59Z")
        if unread_only:
            filters.append("isRead eq false")

        if filters:
            params["$filter"] = " and ".join(filters)

        return params

    def get_folder_id(self, mailbox: str, folder_name: str) -> Optional[str]:
        """Get folder ID by name (e.g., 'Inbox', 'Sent Items')."""
        headers = self.auth.get_shared_mailbox_headers() if mailbox else self.auth.get_headers()

        url = f"{self.GRAPH_API_BASE}/users/{mailbox}/mailFolders"
        if not mailbox:
            url = f"{self.GRAPH_API_BASE}/me/mailFolders"

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to get folders: {response.status_code}")
            return None

        folders = response.json().get("value", [])
        for folder in folders:
            if folder.get("displayName", "").lower() == folder_name.lower():
                logger.info(f"Found folder '{folder_name}': {folder.get('id')}")
                return folder.get("id")

        logger.warning(f"Folder '{folder_name}' not found, using default well-known folder")
        known_folders = {
            "inbox": "AQMkADhhMGQ5LWE3MzktNDdiYS1iMDdjLTRlNDMtOGE4Yy1hOGQ1ZDg1OTJkYzRAZAAuZXcwZS0xa3MGkAaS5TPEtKq4gAA4ibOiEKukAAiocm9nW7gAA==",
            "sent items": "AQMkADhhMGQ5LWE3MzktNDdiYS1iMDdjLTRlNDMtOGE4Yy1hOGQ1ZDg1OTJkYzRAZAAuZXcwZS0xa3MGkAaS5TPEtKq4gAA4ibOiEKukAAiocm9uZ1u4AAAA"
        }
        return known_folders.get(folder_name.lower())

    def list_messages(self, mailbox: str, folder: str = None,
                     limit: int = 10, **filters) -> list:
        """List messages in a folder."""
        headers = self.auth.get_shared_mailbox_headers() if mailbox else self.auth.get_headers()
        params = self._build_query_params(limit=limit, folder=folder, **filters)

        if folder:
            folder_id = self.get_folder_id(mailbox, folder)
            if not folder_id:
                logger.error(f"Could not find folder: {folder}")
                return []
            url = f"{self.GRAPH_API_BASE}/users/{mailbox}/mailFolders/{folder_id}/messages"
        else:
            url = f"{self.GRAPH_API_BASE}/me/mailFolders/Inbox/messages"

        logger.info(f"Fetching messages from: {url}")
        logger.info(f"Query params: {params}")

        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to list messages: {response.status_code}")
            logger.error(response.text)
            return []

        messages = response.json().get("value", [])
        logger.info(f"Found {len(messages)} messages")
        return messages

    def get_html_body(self, mailbox: str, message_id: str) -> Optional[str]:
        """Get HTML body directly from Graph API."""
        headers = self.auth.get_shared_mailbox_headers() if mailbox else self.auth.get_headers()

        url = f"{self.GRAPH_API_BASE}/users/{mailbox}/messages/{message_id}"
        if not mailbox:
            url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}"

        params = {
            "$select": "id,subject,body"
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to get message: {response.status_code}")
            return None

        msg = response.json()
        body = msg.get("body", {})
        
        if body.get("contentType") == "html":
            return body.get("content")
        
        logger.warning(f"Body is not HTML (type: {body.get('contentType')})")
        return None

    def get_message_as_eml(self, mailbox: str, message_id: str) -> bytes:
        """Get message as MIME content (for .eml export)."""
        headers = self.auth.get_shared_mailbox_headers() if mailbox else self.auth.get_headers()
        headers["Accept"] = "message/rfc822"

        url = f"{self.GRAPH_API_BASE}/users/{mailbox}/messages/{message_id}/$value"
        if not mailbox:
            url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}/$value"

        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Failed to get message as eml: {response.status_code}")
            return b""

        return response.content

    def get_attachments(self, mailbox: str, message_id: str) -> list:
        """Get attachments for a message."""
        headers = self.auth.get_shared_mailbox_headers() if mailbox else self.auth.get_headers()

        url = f"{self.GRAPH_API_BASE}/users/{mailbox}/messages/{message_id}/attachments"
        if not mailbox:
            url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}/attachments"

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to get attachments: {response.status_code}")
            return []

        return response.json().get("value", [])

    def download_attachment(self, mailbox: str, message_id: str,
                           attachment_id: str) -> bytes:
        """Download a specific attachment."""
        headers = self.auth.get_shared_mailbox_headers() if mailbox else self.auth.get_headers()

        url = f"{self.GRAPH_API_BASE}/users/{mailbox}/messages/{message_id}/attachments/{attachment_id}/$value"
        if not mailbox:
            url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}/attachments/{attachment_id}/$value"

        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Failed to download attachment: {response.status_code}")
            return b""

        return response.content

    def sanitize_filename(self, name: str, max_length: int = 50) -> str:
        """Sanitize filename for filesystem."""
        import re
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = name[:max_length].strip()
        return name or "unnamed"

    def fetch_and_save(self, mailbox: str, folder: str = None,
                      limit: int = 10, include_attachments: bool = True,
                      html_only: bool = False,
                      **filters) -> list:
        """
        Fetch emails and save to disk.
        
        Args:
            html_only: If True, only fetch HTML body via Graph API (no .eml files).
        """
        messages = self.list_messages(mailbox, folder, limit, **filters)

        saved_emails = []
        for idx, msg in enumerate(messages):
            message_id = msg.get("id")
            subject = msg.get("subject", "No Subject")
            received = msg.get("receivedDateTime", "")

            logger.info(f"\n[{idx+1}/{len(messages)}] Processing: {subject[:50]}...")

            safe_subject = self.sanitize_filename(subject)
            timestamp = received.replace(":", "-").replace(".", "-") if received else f"idx_{idx}"
            
            html_content = None
            html_path = None
            eml_path = None
            
            if html_only:
                html_content = self.get_html_body(mailbox, message_id)
                if not html_content:
                    logger.warning(f"  Skipping - no HTML body available")
                    continue
                    
                html_filename = f"email_{idx:03d}_{timestamp}_{safe_subject}.html"
                html_path = self.html_dir / html_filename
                
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"  Saved HTML: {html_path.name}")
            else:
                eml_content = self.get_message_as_eml(mailbox, message_id)
                if not eml_content:
                    logger.warning(f"  Skipping - could not fetch email content")
                    continue

                eml_filename = f"email_{idx:03d}_{timestamp}_{safe_subject}.eml"
                eml_path = self.originals_dir / eml_filename

                with open(eml_path, "wb") as f:
                    f.write(eml_content)
                logger.info(f"  Saved: {eml_path.name}")

            attachments_info = []
            if include_attachments and msg.get("hasAttachments"):
                attachments = self.get_attachments(mailbox, message_id)
                attachments_dir = self.originals_dir / f"email_{idx:03d}_attachments"
                attachments_dir.mkdir(exist_ok=True)

                for att in attachments:
                    att_name = self.sanitize_filename(att.get("name", "attachment"))
                    att_id = att.get("id")
                    att_size = att.get("size", 0)

                    if att.get("@odata.type") == "#microsoft.graph.fileAttachment":
                        content = self.download_attachment(mailbox, message_id, att_id)
                        if content:
                            att_path = attachments_dir / att_name
                            with open(att_path, "wb") as f:
                                f.write(content)
                            logger.info(f"  Attachment: {att_name} ({att_size} bytes)")
                            attachments_info.append({
                                "name": att_name,
                                "size": att_size,
                                "path": str(att_path)
                            })

            email_meta = {
                "index": idx,
                "message_id": message_id,
                "subject": subject,
                "from": str(msg.get("from", {}).get("emailAddress", {})),
                "received": received,
                "has_attachments": msg.get("hasAttachments", False),
                "attachment_count": len(attachments_info),
                "eml_file": str(eml_path) if not html_only else None,
                "html_file": str(html_path) if html_only else None,
                "attachments": attachments_info
            }
            saved_emails.append(email_meta)

        metadata_path = self.originals_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(saved_emails, f, indent=2)
        logger.info(f"\nSaved metadata to: {metadata_path}")
        logger.info(f"Total emails fetched: {len(saved_emails)}")

        return saved_emails


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fetch emails from O365 shared mailbox")
    parser.add_argument("--mailbox", default="info@elektrotechnieker.be",
                       help="Shared mailbox email address")
    parser.add_argument("--folder", default="Inbox",
                       help="Folder name (e.g., Inbox, Sent Items)")
    parser.add_argument("--limit", type=int, default=10,
                       help="Number of emails to fetch")
    parser.add_argument("--date-from", 
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-to",
                       help="End date (YYYY-MM-DD)")
    parser.add_argument("--no-attachments", action="store_true",
                       help="Skip downloading attachments")
    parser.add_argument("--unread-only", action="store_true",
                       help="Only fetch unread emails")
    parser.add_argument("--html-only", action="store_true",
                       help="Only fetch HTML body via Graph API (no .eml files)")
    parser.add_argument("--config", help="Path to config.yaml")
    args = parser.parse_args()

    auth = AzureAuth()
    if not auth.authenticate_app_only():
        print("Authentication failed!")
        sys.exit(1)

    fetcher = EmailFetcher(auth, args.config)

    filters = {}
    if args.date_from:
        filters["date_from"] = args.date_from
    if args.date_to:
        filters["date_to"] = args.date_to
    if args.unread_only:
        filters["unread_only"] = True

    saved = fetcher.fetch_and_save(
        mailbox=args.mailbox,
        folder=args.folder,
        limit=args.limit,
        include_attachments=not args.no_attachments,
        html_only=args.html_only,
        **filters
    )

    print(f"\nDone! Fetched {len(saved)} emails.")
    if args.html_only:
        print(f"HTML files saved to: {fetcher.html_dir}")
    else:
        print(f"Files saved to: {fetcher.originals_dir}")


if __name__ == "__main__":
    main()
