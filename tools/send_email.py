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


@doc_tag("Emails")
@doc_name("Send email")
def gmail_send_email_tool(
    to: Annotated[str, Field(description="Recipient's email address.")],
    subject: Annotated[str, Field(description="Subject of the email.")],
    body: Annotated[str, Field(description="Body content of the email.")],
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
    Compose and send an email to the specified recipients.

    * Requires permission scope for Gmail.

    Args:
    - to (str): The recipient's email address.
    - subject (str): The subject of the email.
    - body (str): The body content of the email.
    - cc (str): Carbon copy recipients (optional).
    - bcc (str): Blind carbon copy recipients (optional).
    - is_html (bool): Whether to send the email as HTML (default is False for plain text).

    Returns:
    - dict: Success or failure message along with email details or error.
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

        # Build the email message
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc

        # Attach the body content based on is_html flag
        if is_html:
            msg_body = MIMEText(body, "html")
        else:
            msg_body = MIMEText(body, "plain")

        message.attach(msg_body)

        # Base64 encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send the email using the Gmail API
        sent_message = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        # Return the sent email details
        return {
            "status": "success",
            "message": "Email sent successfully.",
            "sent_message": sent_message,
        }

    except HttpError as error:
        error_message = error._get_reason()
        error_details = error.resp
        error_content = (
            error.content.decode()
            if hasattr(error.content, "decode")
            else str(error.content)
        )

        logger.error(f"Google API error occurred: {error_message}")
        logger.error(f"Error details: {error_details}")
        logger.error(f"Error content: {error_content}")

        return {
            "status": "error",
            "error": {
                "message": error_message,
                "details": error_details,
                "content": error_content,
            },
        }

    except Exception as general_error:
        logger.error(f"Unexpected error occurred: {str(general_error)}")
        return {
            "status": "error",
            "error": {"message": "Unexpected error", "details": str(general_error)},
        }
