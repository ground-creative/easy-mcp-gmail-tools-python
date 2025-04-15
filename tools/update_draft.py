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


@doc_tag("Drafts")
@doc_name("Update draft")
def gmail_update_draft_tool(
    draft_id: Annotated[str, Field(description="ID of the draft to modify.")],
    to: Annotated[
        Optional[str], Field(description="Recipient's email address.")
    ] = None,
    subject: Annotated[
        Optional[str], Field(description="Subject of the email.")
    ] = None,
    body: Annotated[
        Optional[str], Field(description="Body content of the email.")
    ] = None,
    cc: Annotated[Optional[str], Field(description="CC recipients (optional).")] = "",
    bcc: Annotated[Optional[str], Field(description="BCC recipients (optional).")] = "",
    is_html: Annotated[
        Optional[bool], Field(description="If the body content is HTML.")
    ] = False,
) -> dict:
    """
    Modify an existing draft by updating the body, subject, and recipients.
    Keeps the previous values for any parameters that are not provided.

    * Requires permission scope for Gmail.

    Args:
    - draft_id (str): The ID of the draft to modify.
    - to (str, optional): The recipient's email address (optional).
    - subject (str, optional): The subject of the email (optional).
    - body (str, optional): The body content of the email (optional).
    - cc (str, optional): CC recipients (optional).
    - bcc (str, optional): BCC recipients (optional).
    - is_html (bool, optional): If True, the body content is HTML (optional).

    Returns:
    - dict: Success or failure message along with updated draft details or error.
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

        # Fetch the existing draft to modify
        draft = service.users().drafts().get(userId="me", id=draft_id).execute()
        message = draft["message"]
        payload = message["payload"]

        # Use existing values if 'to' or 'subject' is not provided
        if not to:
            to = next(
                (
                    header["value"]
                    for header in payload["headers"]
                    if header["name"] == "To"
                ),
                "",
            )
        if not subject:
            subject = next(
                (
                    header["value"]
                    for header in payload["headers"]
                    if header["name"] == "Subject"
                ),
                "",
            )

        # Retain existing values for parameters not provided
        # Modify the subject if provided
        if subject:
            payload["headers"] = [
                header for header in payload["headers"] if header["name"] != "Subject"
            ]
            payload["headers"].append({"name": "Subject", "value": subject})

        # Modify the recipient if provided
        if to:
            for header in payload["headers"]:
                if header["name"] == "To":
                    header["value"] = to
                    break
            else:
                payload["headers"].append({"name": "To", "value": to})

        # Modify the CC if provided
        if cc:
            for header in payload["headers"]:
                if header["name"] == "Cc":
                    header["value"] = cc
                    break
            else:
                payload["headers"].append({"name": "Cc", "value": cc})

        # Modify the BCC if provided
        if bcc:
            for header in payload["headers"]:
                if header["name"] == "Bcc":
                    header["value"] = bcc
                    break
            else:
                payload["headers"].append({"name": "Bcc", "value": bcc})

        # Rebuild the email message body (plain text or HTML) if body is provided
        if body:
            new_msg = MIMEMultipart("alternative")
            new_msg["to"] = to if to else payload.get("To", "unknown@example.com")
            new_msg["subject"] = (
                subject if subject else payload.get("Subject", "No Subject")
            )
            if is_html is not None:
                if is_html:
                    msg_body_html = MIMEText(body, "html")
                    new_msg.attach(msg_body_html)
                else:
                    msg_body_plain = MIMEText(body, "plain")
                    new_msg.attach(msg_body_plain)
            elif not is_html and body:
                msg_body_plain = MIMEText(body, "plain")
                new_msg.attach(msg_body_plain)

            # Encode the new message in base64
            raw_message = base64.urlsafe_b64encode(new_msg.as_bytes()).decode()

            # Update the draft with the new message content
            draft["message"]["raw"] = raw_message

        # Update the draft
        updated_draft = (
            service.users()
            .drafts()
            .update(userId="me", id=draft_id, body=draft)
            .execute()
        )

        # Return the updated draft details
        return {
            "status": "success",
            "message": "Draft modified successfully.",
            "draft": updated_draft,
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
