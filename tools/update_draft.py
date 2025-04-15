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
    to: Annotated[Optional[str], Field(description="Recipient's email address.")] = None,
    subject: Annotated[Optional[str], Field(description="Subject of the email.")] = None,
    body: Annotated[Optional[str], Field(description="Body content of the email.")] = None,
    cc: Annotated[Optional[str], Field(description="CC recipients (optional).")] = "",
    bcc: Annotated[Optional[str], Field(description="BCC recipients (optional).")] = "",
    is_html: Annotated[Optional[bool], Field(description="If the body content is HTML.")] = False,
) -> dict:
    """
    Modify an existing draft by updating the body, subject, and recipients.
    Keeps the previous values for any parameters that are not provided.
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

        # Fetch the existing draft
        draft = service.users().drafts().get(userId="me", id=draft_id).execute()
        message = draft["message"]
        payload = message.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        # Extract original values
        original_to = headers.get("To", "")
        original_subject = headers.get("Subject", "")
        original_cc = headers.get("Cc", "")
        original_bcc = headers.get("Bcc", "")
        original_body = ""

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
<<<<<<< Updated upstream
                original_body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8"
                )
=======
                original_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
>>>>>>> Stashed changes
                break

        # Use existing values if not provided
        to = to or original_to
        subject = subject or original_subject
        cc = cc or original_cc
        bcc = bcc or original_bcc
        body = body or original_body or " "

        # Rebuild the MIME message
        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc

        msg.attach(MIMEText(body, "html" if is_html else "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        # Send updated raw message
<<<<<<< Updated upstream
        updated_draft = (
            service.users()
            .drafts()
            .update(
                userId="me",
                id=draft_id,
                body={"message": {"raw": raw}},
            )
            .execute()
        )
=======
        updated_draft = service.users().drafts().update(
            userId="me",
            id=draft_id,
            body={"message": {"raw": raw}},
        ).execute()
>>>>>>> Stashed changes

        return {
            "status": "success",
            "message": "Draft modified successfully.",
            "draft": updated_draft,
        }

    except HttpError as error:
        logger.error(f"Google API error occurred: {error._get_reason()}")
        logger.error(f"Error details: {error.resp}")
<<<<<<< Updated upstream
        logger.error(
            f"Error content: {error.content.decode() if hasattr(error.content, 'decode') else str(error.content)}"
        )
=======
        logger.error(f"Error content: {error.content.decode() if hasattr(error.content, 'decode') else str(error.content)}")
>>>>>>> Stashed changes
        return {
            "status": "error",
            "error": {
                "message": error._get_reason(),
                "details": error.resp,
<<<<<<< Updated upstream
                "content": (
                    error.content.decode()
                    if hasattr(error.content, "decode")
                    else str(error.content)
                ),
=======
                "content": error.content.decode() if hasattr(error.content, "decode") else str(error.content),
>>>>>>> Stashed changes
            },
        }

    except Exception as general_error:
        logger.error(f"Unexpected error occurred: {str(general_error)}")
        return {
            "status": "error",
            "error": {"message": "Unexpected error", "details": str(general_error)},
        }
