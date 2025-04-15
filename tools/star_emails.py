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
@doc_name("Add or remove star from emails")
def gmail_star_emails_tool(
    message_ids: Annotated[
        List[str], Field(description="List of Gmail message IDs of emails to modify.")
    ],
    star_email: Annotated[
        Optional[bool],
        Field(description="If True, star the email. If False, unstar it."),
    ] = None,
) -> dict:
    """
    Mark multiple Gmail emails as starred or unstar them.

    Requires Gmail API permission scopes.

    Args:
    - message_ids (List[str]): List of Gmail message IDs of the emails to modify.
    - star_email (bool, optional): If True, stars the emails. If False, unstars them.

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
            label_body = {}

            if star_email is not None:
                if star_email:
                    if "STARRED" not in label_body.get("addLabelIds", []):
                        label_body.setdefault("addLabelIds", []).append("STARRED")
                else:
                    if "STARRED" not in label_body.get("removeLabelIds", []):
                        label_body.setdefault("removeLabelIds", []).append("STARRED")

            # Make the API call
            service.users().messages().modify(
                userId="me", id=message_id, body=label_body
            ).execute()

            starred_status = (
                "starred"
                if star_email
                else "unstarred" if star_email is False else "not changed"
            )

            logger.info(f"Email with message ID {message_id} {starred_status}.")

        return {
            "status": "success",
            "message": f"Emails marked as {'starred' if star_email else 'unstarred'}",
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
                "message": error_message,
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
