"""
Azure AD Authentication module for Microsoft Graph API.
Supports both app-only (client credentials) and delegated (device code) authentication.
"""

import os
import sys
import logging
from pathlib import Path

import msal
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class AzureAuth:
    """Handles authentication with Microsoft Graph API using MSAL."""

    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, env_file: str = None):
        self.env_file = env_file or ".env"
        self.tenant_id = None
        self.client_id = None
        self.client_secret = None
        self.shared_mailbox = None
        self.user_email = None
        self.token = None
        self.app = None

    def load_credentials(self) -> bool:
        """Load credentials from .env file."""
        env_path = Path(self.env_file)
        if not env_path.exists():
            logger.error(f"Environment file not found: {self.env_file}")
            logger.info("Copy .env.example to .env and fill in your credentials")
            return False

        load_dotenv(env_path)

        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.shared_mailbox = os.getenv("SHARED_MAILBOX_EMAIL")
        self.user_email = os.getenv("O365_USER_EMAIL")

        if not all([self.tenant_id, self.client_id, self.client_secret]):
            logger.error("Missing required credentials in .env file")
            logger.error("Required: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
            return False

        logger.info(f"Loaded credentials for tenant: {self.tenant_id}")
        logger.info(f"Client ID: {self.client_id[:8]}...")
        if self.shared_mailbox:
            logger.info(f"Shared mailbox: {self.shared_mailbox}")
        return True

    def authenticate_app_only(self) -> bool:
        """
        Authenticate using client credentials (app-only).
        Best for automated scripts and background processes.
        
        For shared mailbox access, you need to:
        1. Grant Mail.Read application permission in Azure AD
        2. Grant access to the shared mailbox via Exchange admin center
        """
        if not self.load_credentials():
            return False

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=authority
        )

        scopes = ["https://graph.microsoft.com/.default"]
        result = self.app.acquire_token_for_client(scopes=scopes)

        if "access_token" in result:
            self.token = result["access_token"]
            logger.info("Successfully authenticated with app-only flow")
            return True
        else:
            error = result.get("error", "Unknown error")
            description = result.get("error_description", "No description")
            logger.error(f"Authentication failed: {error}")
            logger.error(f"Details: {description}")
            return False

    def authenticate_delegated(self) -> bool:
        """
        Authenticate using device code flow (delegated).
        Best for initial setup and manual testing.
        User logs in via browser.
        """
        if not self.load_credentials():
            return False

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=authority
        )

        scopes = [
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/Mail.Read.Shared",
            "offline_access"
        ]

        result = self.app.acquire_token_by_device_flow(
            scopes=scopes,
            timeout=60
        )

        if "access_token" in result:
            self.token = result["access_token"]
            logger.info("Successfully authenticated with delegated flow")
            return True
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Authentication failed: {error}")
            return False

    def get_token(self) -> str:
        """Get the current access token."""
        if not self.token:
            logger.error("Not authenticated. Call authenticate_app_only() or authenticate_delegated() first.")
        return self.token

    def get_headers(self) -> dict:
        """Get HTTP headers with authorization token."""
        if not self.token:
            raise ValueError("Not authenticated. Call authenticate first.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_shared_mailbox_headers(self) -> dict:
        """
        Get HTTP headers for accessing a shared mailbox.
        Uses the X-AnchorMailbox header for shared mailbox routing.
        """
        headers = self.get_headers()
        if self.shared_mailbox:
            headers["X-AnchorMailbox"] = self.shared_mailbox
        return headers

    def test_connection(self) -> bool:
        """Test the Graph API connection."""
        if not self.token:
            logger.error("Not authenticated")
            return False

        try:
            response = requests.get(
                f"{self.GRAPH_API_BASE}/me/",
                headers=self.get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"Connected as: {user_info.get('displayName', 'Unknown')}")
                logger.info(f"Email: {user_info.get('mail', user_info.get('userPrincipalName'))}")
                return True
            elif response.status_code == 403:
                logger.warning("Connected but limited permissions")
                return True
            else:
                logger.error(f"Connection test failed: {response.status_code}")
                logger.error(response.text)
                return False
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False


def main():
    """Quick test of authentication."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Azure AD authentication")
    parser.add_argument("--mode", choices=["app-only", "delegated"], default="app-only",
                        help="Authentication mode")
    args = parser.parse_args()

    auth = AzureAuth()

    if args.mode == "app-only":
        success = auth.authenticate_app_only()
    else:
        success = auth.authenticate_delegated()

    if success:
        auth.test_connection()
        print("\nAuthentication successful!")
        print(f"Token: {auth.token[:50]}..." if auth.token else "No token")
    else:
        print("\nAuthentication failed. Check your credentials.")
        sys.exit(1)


if __name__ == "__main__":
    main()
