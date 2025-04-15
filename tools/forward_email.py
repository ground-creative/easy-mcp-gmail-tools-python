from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, Optional
from pydantic import Field
from typing_extensions import Annotated
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
from core.utils.tools import doc_tag, doc_name
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.tools.get_email_details import gmail_get_email_details_tool


@doc_tag("Emails")
@doc_name("Forward email")
def gmail_forward_email_tool(
    message_id: Annotated[str, Field(description="Message ID of the original email.")],
    forward_to: Annotated[
        str, Field(description="Recipient email address for forwarding.")
    ],
    body: Annotated[
        Optional[str], Field(description="Optional message to include when forwarding.")
    ] = "",
    cc: Annotated[
        Optional[str], Field(description="Carbon copy recipients (optional).")
    ] = "",
    bcc: Annotated[
        Optional[str], Field(description="Blind carbon copy recipients (optional).")
    ] = "",
) -> Dict:
    """
    Forward an email message with the given message ID.

    * Requires permission scope for Gmail.

    Args:
    - message_id (str): The Gmail API message ID of the email you are forwarding.
    - forward_to (str): The recipient email address to forward the message to.
    - body (str): Optional message to include in the forward.
    - cc (Optional[str]): Carbon copy recipients.
    - bcc (Optional[str]): Blind carbon copy recipients.

    Returns:
    - dict: Success or error details.
    """
    auth_response = check_access(True)
    if auth_response:
        return auth_response

    try:
        service = global_state.get("google_gmail_service")
        if service is None:
            logger.error("Google Gmail service not initialized.")
            return {
                "status": "error",
                "error": f"Gmail permission scope not available, please re-authenticate at {EnvConfig.get('APP_HOST')}/auth/login",
            }

        original_email = gmail_get_email_details_tool(
            message_id=message_id, prefer_html=True
        )
        original = original_email["email"]
        # Build the forward message
        forward_msg = MIMEMultipart()
        forward_msg["to"] = forward_to
        forward_msg["subject"] = f"Fwd: {original['subject']}"

        if cc:
            forward_msg["cc"] = cc
        if bcc:
            forward_msg["bcc"] = bcc

        body_is_html = is_html(original["body"])
        content_type = "html" if body_is_html else "plain"

        # Build the forwarded body
        if body_is_html:
            forward_body = f"""
<p>{body}</p>
<br>
---------- Forwarded message ---------<br>
<p><strong>From:</strong> {original['from']}<br>
<strong>Date:</strong> {original['date']}<br>
<strong>Subject:</strong> {original['subject']}</p>
{original['body']}
"""
        else:
            forward_body = f"""{body}

---------- Forwarded message ---------
From: {original['from']}
Date: {original['date']}
Subject: {original['subject']}

{original['body']}
"""

        forward_msg.attach(MIMEText(forward_body, content_type))

        # Encode the message
        raw_message = base64.urlsafe_b64encode(forward_msg.as_bytes()).decode()
        send_body = {"raw": raw_message}

        sent_message = (
            service.users().messages().send(userId="me", body=send_body).execute()
        )

        return {
            "status": "success",
            "message": "Email forwarded successfully.",
            "sent_message": sent_message,
        }

    except HttpError as e:
        logger.error(f"HTTP Error: {e._get_reason()}")
        return {"status": "error", "error": {"message": e._get_reason()}}

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "status": "error",
            "error": {"message": "Unexpected error", "details": str(e)},
        }


def is_html(text):
    return bool(text) and (
        "<html" in text.lower() or "<body" in text.lower() or "</" in text
    )
