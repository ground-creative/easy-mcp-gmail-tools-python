from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, Optional
from pydantic import Field
from typing_extensions import Annotated
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.tools import doc_tag, doc_name
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
import base64
import html


@doc_tag("Emails")
@doc_name("Get email details")
def gmail_get_email_details_tool(
    message_id: Annotated[
        str,
        Field(
            description="The unique Gmail message ID for the email you want to retrieve."
        ),
    ],
    prefer_html: Annotated[
        Optional[bool],
        Field(
            description="If true, prefers HTML body content; otherwise prefers plain text.",
        ),
    ] = False,
) -> Dict:
    """
    Retrieve full details of a specific email by message ID.

    * Requires permission scope for Gmail.

    Args:
    - message_id (str): The Gmail message ID to retrieve.
    - prefer_html (bool, optional): Prefer HTML body if available. Defaults to False.

    Returns:
    - dict: Email metadata, headers, body, attachments (if available), or an error.
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

        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        headers = message.get("payload", {}).get("headers", [])

        def get_header(name: str):
            value = next(
                (h["value"] for h in headers if h["name"].lower() == name.lower()),
                None,
            )
            return html.unescape(value) if value is not None else None

        def extract_body(payload):
            def walk_parts(parts):
                preferred = "text/html" if prefer_html else "text/plain"
                fallback = "text/plain" if prefer_html else "text/html"
                body_text = ""

                for part in parts:
                    mime_type = part.get("mimeType")
                    data = part.get("body", {}).get("data")

                    if mime_type == preferred and data:
                        return base64.urlsafe_b64decode(data).decode("utf-8")
                    elif mime_type == fallback and data and not body_text:
                        body_text = base64.urlsafe_b64decode(data).decode("utf-8")
                    elif part.get("parts"):
                        result = walk_parts(part["parts"])
                        if result:
                            return result
                return body_text

            if "parts" in payload:
                return walk_parts(payload["parts"])
            else:
                data = payload.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")
            return ""

        email_details = {
            "id": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds", []),
            "snippet": html.unescape(message.get("snippet", "")),
            "subject": get_header("Subject"),
            "from": get_header("From"),
            "to": get_header("To"),
            "cc": get_header("Cc"),
            "bcc": get_header("Bcc"),
            "date": get_header("Date"),
            "in_reply_to": get_header("In-Reply-To"),
            "references": get_header("References"),
            "body": extract_body(message.get("payload", {})),
            "gmail_link": f"https://mail.google.com/mail/u/0/#inbox/{message.get('id')}",
            "message_id": get_header("Message-ID"),
        }

        return {"status": "success", "email": email_details}

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
