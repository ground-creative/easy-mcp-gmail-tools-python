from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict
from pydantic import Field
from typing_extensions import Annotated

from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
from core.utils.tools import doc_tag, doc_name


@doc_tag("Emails")
@doc_name("Mark emails as read or unread")
def gmail_mark_emails_tool(
    message_ids: Annotated[
        List[str], Field(description="List of Gmail message IDs of emails to modify.")
    ],
    mark_as_read: Annotated[
        bool, Field(description="If True, mark as read. If False, mark as unread.")
    ] = True,
) -> Dict:
    """
    Marks multiple Gmail emails as read or unread.

    Requires Gmail API permission scopes.

    Args:
    - message_ids (List[str]): List of Gmail message IDs of the emails.
    - mark_as_read (bool): True to mark as read, False for unread.

    Returns:
    - dict: Result of the operation or error details.
    """

    # Check access
    auth_response = check_access(True)
    if auth_response:
        return auth_response

    # Get Gmail service
    service = global_state.get("google_gmail_service")
    if service is None:
        logger.error("Google Gmail service is not available in global state.")
        return {
            "status": "error",
            "error": (
                "Gmail permission scope not available, "
                f"please add this scope here: {EnvConfig.get('APP_HOST')}/auth/login"
            ),
        }

    try:
        label_action = "removeLabelIds" if mark_as_read else "addLabelIds"
        label_body = {label_action: ["UNREAD"]}

        # Loop through the list of message IDs and modify each email
        for message_id in message_ids:
            service.users().messages().modify(
                userId="me", id=message_id, body=label_body
            ).execute()

            logger.info(
                f"Email with message ID {message_id} marked as {'read' if mark_as_read else 'unread'}."
            )

        return {
            "status": "success",
            "message": f"Emails marked as {'read' if mark_as_read else 'unread'}",
        }

    except HttpError as error:
        error_message = error._get_reason()
        error_details = error.resp
        error_content = (
            error.content.decode()
            if hasattr(error.content, "decode")
            else str(error.content)
        )

        logger.error(
            "Google API error occurred",
            extra={
                "error_message": error_message,
                "details": str(error_details),
                "content": error_content,
            },
        )

        return {
            "status": "error",
            "error": {
                "error_message": error_message,
                "details": str(error_details),
                "content": error_content,
            },
        }

    except Exception as general_error:
        logger.exception("Unexpected error occurred.")
        return {
            "status": "error",
            "error": {"message": "Unexpected error", "details": str(general_error)},
        }
