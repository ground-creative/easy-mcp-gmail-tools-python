from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import Field
from typing import List, Optional
from typing_extensions import Annotated
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
from core.utils.tools import doc_tag, doc_name


@doc_tag("Emails")
@doc_name("Mark emails as spam or not spam")
def gmail_set_emails_as_spam_tool(
    message_ids: Annotated[
        List[str], Field(description="List of Gmail message IDs of emails to modify.")
    ],
    mark_as_spam: Annotated[
        bool,
        Field(
            description="If True, mark as spam. If False, unmark (move out of spam)."
        ),
    ] = True,
    new_label: Annotated[
        Optional[str],
        Field(
            description="Optional label to add when unmarking the email from spam. Ex: 'INBOX'."
        ),
    ] = None,
) -> dict:
    """
    Marks multiple Gmail emails as spam or not spam.

    Requires Gmail API permission scopes.

    Args:
    - message_ids (List[str]): List of Gmail message IDs of the emails to modify.
    - mark_as_spam (bool): If True, marks the emails as spam. If False, removes the spam label.
    - new_label (str, optional): Optional label to add when unmarking the emails from spam. Default is 'INBOX'.

    Returns:
    - dict: Result of the operation, including a success message or error details.
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
        # Process each email in the list of message IDs
        for message_id in message_ids:
            if mark_as_spam:
                label_body = {"addLabelIds": ["SPAM"]}
            else:
                label_body = {"removeLabelIds": ["SPAM"]}
                label_to_add = new_label or "INBOX"
                label_body["addLabelIds"] = [label_to_add]

            service.users().messages().modify(
                userId="me", id=message_id, body=label_body
            ).execute()

            logger.info(
                f"Email with message ID {message_id} marked as {'spam' if mark_as_spam else 'not spam'}."
            )

        return {
            "status": "success",
            "message": f"Emails marked as {'spam' if mark_as_spam else 'not spam'}",
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
                "message": error_message,
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
