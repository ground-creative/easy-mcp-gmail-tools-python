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
@doc_name("Reply to email")
def gmail_reply_email_tool(
    message_id: Annotated[str, Field(description="Message ID of the original email.")],
    body: Annotated[str, Field(description="Body content of the reply.")],
    cc: Annotated[
        Optional[str], Field(description="Carbon copy recipients (optional).")
    ] = "",
    bcc: Annotated[
        Optional[str], Field(description="Blind carbon copy recipients (optional).")
    ] = "",
    is_html: Annotated[
        Optional[bool],
        Field(description="Flag to determine if the email should be sent as HTML."),
    ] = False,  # Default to False for plain text email
) -> Dict:
    """
    Send a reply to an email message with the given message ID.

    * Requires permission scope for Gmail.

    Args:
    - message_id (str): The Gmail API message ID of the email you are replying to.
    - body (str): The body content of the reply email.
    - cc (Optional[str]): Carbon copy recipients (optional).
    - bcc (Optional[str]): Blind carbon copy recipients (optional).
    - is_html (bool): Whether to send the email as HTML (default is False for plain text).

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

        # Get the original email details
        original_email = gmail_get_email_details_tool(
            message_id=message_id, prefer_html=is_html
        )
        original = original_email["email"]
        original_message_id = original["message_id"]
        to = original["from"]
        subject = original["subject"]
        original_body = original["body"]

        if is_html:
            original_email_formatted = f"<blockquote>{original_body}</blockquote>"
        else:
            original_email_formatted = f"\n\n-- Original Message --\n{original_body}"

        # Combine the original email and the reply body
        combined_body = f"{body}\n\n{original_email_formatted}"

        # Build the reply message
        reply_msg = MIMEMultipart()
        reply_msg["to"] = to
        reply_msg["subject"] = f"Re: {subject}"
        reply_msg["In-Reply-To"] = original_message_id
        reply_msg["References"] = (
            f"{original['references']} {original_message_id}".strip()
            if original["references"]
            else original_message_id
        )

        if cc:
            reply_msg["cc"] = cc
        if bcc:
            reply_msg["bcc"] = bcc

        # Attach body based on is_html flag
        if is_html:
            msg_body = MIMEText(combined_body, "html")
        else:
            msg_body = MIMEText(combined_body, "plain")

        reply_msg.attach(msg_body)

        # Add thread ID if exists
        thread_id = original.get("threadId")
        raw_message = base64.urlsafe_b64encode(reply_msg.as_bytes()).decode()
        send_body = {"raw": raw_message}
        if thread_id:
            send_body["threadId"] = thread_id

        # Send the reply message
        sent_message = (
            service.users().messages().send(userId="me", body=send_body).execute()
        )

        return {
            "status": "success",
            "message": "Reply sent successfully.",
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
