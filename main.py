import time
import json
import base64
import smtplib
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from msal import ConfidentialClientApplication
import requests

# Constants for Gmail and Microsoft API scopes
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.send"]
MICROSOFT_SCOPES = ["https://graph.microsoft.com/.default"]

# Gmail Handler
class GmailHandler:
    def __init__(self, credentials_file):
        self.credentials_file = credentials_file
        self.creds = None
        self.authenticate()

    def authenticate(self):
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, GMAIL_SCOPES)
                self.creds = flow.run_local_server(port=0)

    def send_email(self, to, subject, body):
        service = build("gmail", "v1", credentials=self.creds)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

    def move_out_of_spam(self, email_id):
        service = build("gmail", "v1", credentials=self.creds)
        service.users().messages().modify(
            userId="me",
            id=email_id,
            body={"removeLabelIds": ["SPAM"]}
        ).execute()

# Microsoft Handler
class MicrosoftHandler:
    def __init__(self, client_id, client_secret, tenant_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.token = None
        self.authenticate()

    def authenticate(self):
        app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        self.token = app.acquire_token_for_client(scopes=MICROSOFT_SCOPES)

    def send_email(self, to, subject, body):
        headers = {
            "Authorization": f"Bearer {self.token['access_token']}",
            "Content-Type": "application/json"
        }
        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [{"emailAddress": {"address": to}}]
            }
        }
        response = requests.post(
            url="https://graph.microsoft.com/v1.0/me/sendMail",
            headers=headers,
            json=email_data
        )
        response.raise_for_status()

    def move_out_of_spam(self, email_id):
        headers = {"Authorization": f"Bearer {self.token['access_token']}"}
        url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/move"
        json_data = {"destinationId": "inbox"}
        response = requests.post(url, headers=headers, json=json_data)
        response.raise_for_status()

# IP Reputation Management
class IPReputationManager:
    def __init__(self):
        self.ip_reputation_data = {}

    def monitor(self, ip):
        # Replace with actual reputation monitoring API if available
        print(f"Monitoring IP reputation for: {ip}")
        self.ip_reputation_data[ip] = {"status": "Good"}  # Mock response

    def is_reputation_good(self, ip):
        return self.ip_reputation_data.get(ip, {}).get("status", "Unknown") == "Good"

# Main Email Controller
class EmailController:
    def __init__(self, gmail_credentials, microsoft_config):
        self.gmail_handler = GmailHandler(gmail_credentials)
        self.microsoft_handler = MicrosoftHandler(
            client_id=microsoft_config["client_id"],
            client_secret=microsoft_config["client_secret"],
            tenant_id=microsoft_config["tenant_id"]
        )
        self.ip_manager = IPReputationManager()

    def send_email(self, to, subject, body, provider):
        if provider == "gmail":
            self.gmail_handler.send_email(to, subject, body)
        elif provider == "microsoft":
            self.microsoft_handler.send_email(to, subject, body)
        else:
            raise ValueError("Invalid email provider")

    def move_email_out_of_spam(self, email_id, provider):
        if provider == "gmail":
            self.gmail_handler.move_out_of_spam(email_id)
        elif provider == "microsoft":
            self.microsoft_handler.move_out_of_spam(email_id)

# Example Usage
if __name__ == "__main__":
    gmail_credentials_file = "path/to/your/gmail/credentials.json"
    microsoft_config = {
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "tenant_id": "your-tenant-id"
    }

    email_controller = EmailController(gmail_credentials_file, microsoft_config)

    # Monitor IP reputation
    email_controller.ip_manager.monitor("192.168.1.1")

    # Check IP reputation
    if email_controller.ip_manager.is_reputation_good("192.168.1.1"):
        print("IP reputation is good.")

    # Send email via Gmail
    email_controller.send_email(
        to="recipient@example.com",
        subject="Hello from Gmail",
        body="This is a test email.",
        provider="gmail"
    )

    # Send email via Microsoft
    email_controller.send_email(
        to="recipient@example.com",
        subject="Hello from Microsoft",
        body="This is a test email.",
        provider="microsoft"
    )
