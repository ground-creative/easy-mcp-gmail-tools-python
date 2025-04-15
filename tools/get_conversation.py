from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, Optional
from pydantic import Field
from typing_extensions import Annotated
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
import base64
from core.utils.tools import doc_tag, doc_name
import html


@doc_tag("Threads")
@doc_name("Get thread conversation")
def gmail_get_thread_conversation_tool(
    thread_id: Annotated[
        str,
        Field(
            description="The unique Gmail thread ID for the conversation you want to retrieve."
        ),
    ],
    format: Annotated[
        Optional[str],
        Field(
            description="The format of the email content to return (minimal, full). Defaults to 'full'.",
        ),
    ] = "minimal",
) -> Dict:
    """
    Retrieve the full conversation of a specific thread by thread ID.

    * Requires permission scope for Gmail.

    Args:
    - thread_id (str): The Gmail thread ID to retrieve.
    - format (str, optional): The format of the email content ('minimal', 'full'). Defaults to 'minimal'.

    Returns:
    - dict: Thread metadata, messages (or error details).
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

        # Fetch the thread
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_id, format=format)
            .execute()
        )

        # Prepare the response based on the format
        def extract_message_info(message):
            if format == "minimal":
                snippet = html.unescape(message.get("snippet", ""))
                return {
                    "id": message.get("id"),
                    "subject": snippet,
                    "from": None,
                    "body": snippet,
                }

            headers = message.get("payload", {}).get("headers", [])
            subject = next(
                (
                    html.unescape(h["value"])
                    for h in headers
                    if h["name"].lower() == "subject"
                ),
                None,
            )
            from_ = next(
                (
                    html.unescape(h["value"])
                    for h in headers
                    if h["name"].lower() == "from"
                ),
                None,
            )
            body = (
                base64.urlsafe_b64decode(
                    message.get("payload", {})
                    .get("body", {})
                    .get("data", "")
                    .encode("utf-8")
                ).decode("utf-8")
                if message.get("payload", {}).get("body", {}).get("data", "")
                else get_body_from_parts(
                    message.get("payload", {}).get("parts", []), format
                )
            )
            return {
                "id": message.get("id"),
                "subject": subject,
                "from": from_,
                "body": body,
            }

        # Parse the thread messages
        thread_details = {
            "status": "success",
            "id": thread.get("id"),
            "messages": [
                extract_message_info(message) for message in thread.get("messages", [])
            ],
        }

        return thread_details

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


def get_body_from_parts(parts, format):
    """
    Extracts the email body from parts.
    If the format is 'minimal', return the snippet.
    Otherwise, decode the base64 data from the parts.
    """
    body = ""

    for part in parts:
        mime_type = part.get("mimeType")
        data = part.get("body", {}).get("data")

        # Look for the part with the body data and decode it
        if data:
            decoded_body = base64.urlsafe_b64decode(data).decode("utf-8")
            if format == "minimal":
                return part.get("snippet", decoded_body)
            else:
                return decoded_body

    # If no body found, return empty
    return body
