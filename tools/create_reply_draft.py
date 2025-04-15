from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import Field
from typing import Optional
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


@doc_tag("Drafts")
@doc_name("Create draft reply")
def gmail_reply_draft_tool(
    message_id: Annotated[str, Field(description="Gmail API message ID.")],
    body: Annotated[str, Field(description="Body content of the email.")],
    to: Annotated[
        Optional[str],
        Field(
            description="Recipient's email address. If not provided, will be extracted from the original message."
        ),
    ] = None,
    cc: Annotated[
        Optional[str], Field(description="Carbon copy recipients (optional).")
    ] = "",
    bcc: Annotated[
        Optional[str], Field(description="Blind carbon copy recipients (optional).")
    ] = "",
    is_html: Annotated[
        bool, Field(description="Whether the email is HTML or plain text.")
    ] = False,
) -> dict:
    """
    Compose and save a reply to an existing email message in the user's Gmail draft folder.

    * Requires permission scope for Gmail.

    Args:
    - message_id (str): The Gmail API message ID of the email you are replying to.
    - body (str): The body content of the reply email.
    - to (Optional[str]): The recipient's email address. If not provided, it will be extracted from the original message.
    - cc (Optional[str]): Carbon copy recipients (optional).
    - bcc (Optional[str]): Blind carbon copy recipients (optional).
    - is_html (bool): Whether the reply is in HTML format (True) or plain text (False).

    Returns:
    - dict: Success or failure message along with draft details or error.
    """

    auth_response = check_access(True)
    if auth_response:
        return auth_response

    try:
        service = global_state.get("google_gmail_service")
        if service is None:
            logger.error("Google Gmail service is not available in global state.")
            return {
                "status": "error",
                "error": f"Gmail permission scope not available, please add this scope here: {EnvConfig.get('APP_HOST')}/auth/login",
            }

        original_email = gmail_get_email_details_tool(
            message_id=message_id, prefer_html=is_html
        )
        original = original_email["email"]
        original_message_id = original["message_id"]
        subject = original["subject"]
        date = original["date"]
        from_address = original["from"]
        to = to if to is not None else original["from"]
        combined_references = (
            f"{original['references']} {original_message_id}".strip()
            if original["references"]
            else original_message_id
        )

        if not original_message_id:
            return {
                "status": "error",
                "error": "Original Message-ID not found in email headers.",
            }

        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        formatted_date = format_date(date)
        original_body = original["body"]

        reply_body = (
            f"{body}\n\nOn {formatted_date}, {from_address} wrote:\n{original_body}"
        )

        # Build the reply MIME message
        reply_message = MIMEMultipart()
        reply_message["to"] = to
        reply_message["subject"] = subject
        reply_message["In-Reply-To"] = original_message_id
        reply_message["References"] = combined_references

        if cc:
            reply_message["cc"] = cc
        if bcc:
            reply_message["bcc"] = bcc

        reply_message["Thread-Id"] = original["threadId"]

        if is_html:
            msg_body = MIMEText(reply_body, "html")
        else:
            msg_body = MIMEText(reply_body, "plain")

        reply_message.attach(msg_body)

        # Encode to base64
        raw_message = base64.urlsafe_b64encode(reply_message.as_bytes()).decode()
        draft = {
            "message": {"threadId": reply_message["Thread-Id"], "raw": raw_message}
        }

        # Create the draft
        created_draft = (
            service.users().drafts().create(userId="me", body=draft).execute()
        )

        return {
            "status": "success",
            "message": "Reply draft created successfully.",
            "draft": created_draft,
        }

    except HttpError as error:
        logger.error(f"Google API error occurred: {error._get_reason()}")
        return {
            "status": "error",
            "error": {
                "message": error._get_reason(),
                "details": str(error.resp),
                "content": str(error.content),
            },
        }

    except Exception as general_error:
        logger.error(f"Unexpected error occurred: {str(general_error)}")
        return {
            "status": "error",
            "error": {"message": "Unexpected error", "details": str(general_error)},
        }


from datetime import datetime
from email.utils import parsedate_tz, mktime_tz


def format_date(date_str):
    # Parse the date string into a tuple (as returned by parsedate_tz)
    date_tuple = parsedate_tz(date_str)
    if date_tuple:
        # Convert the date tuple into a timestamp
        timestamp = mktime_tz(date_tuple)
        # Return the formatted date
        return datetime.utcfromtimestamp(timestamp).strftime("%b %d, %Y %I:%M %p")
    return date_str  # Return original if parsing fails
