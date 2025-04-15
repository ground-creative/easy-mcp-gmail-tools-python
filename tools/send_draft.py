import base64
from typing import Annotated
from pydantic import Field
from googleapiclient.errors import HttpError
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.tools import doc_tag, doc_name


@doc_tag("Drafts")
@doc_name("Send draft")
def gmail_send_draft_tool(
    draft_id: Annotated[str, Field(description="The ID of the draft to send.")],
) -> dict:
    """
    Sends an existing draft email using Gmail API.

    * Requires Gmail permission scope.

    Args:
    - draft_id (str): The ID of the draft to send.

    Returns:
    - dict: Dictionary indicating success or error.
    """

    logger.info(f"Request received to send draft with ID '{draft_id}'")

    # Check authentication
    auth_response = check_access(True)
    if auth_response:
        return auth_response

    # Retrieve the Gmail service
    gmail_service = global_state.get("google_gmail_service")
    if gmail_service is None:
        logger.error("Google Gmail service is not available in global state.")
        return {
            "status": "error",
            "error": f"Gmail permission scope not available, please add this scope here: {EnvConfig.get('APP_HOST')}/auth/login",
        }

    # Send the draft
    try:
        sent_response = (
            gmail_service.users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )
        logger.info(f"Successfully sent draft with ID: {draft_id}")
        return {
            "status": "success",
            "message": "Draft sent successfully.",
            "response": sent_response,
        }
    except HttpError as error:
        # Extract detailed error message from HttpError
        error_message = error._get_reason()  # Detailed error message from Google API
        error_details = error.resp  # Raw HTTP response from Google API
        error_content = (
            error.content.decode()
            if hasattr(error.content, "decode")
            else str(error.content)
        )

        logger.error(f"Gmail API error sending draft {draft_id}: {error_message}")
        logger.error(f"Error details: {error_details}")
        logger.error(f"Error content: {error_content}")

        return {
            "status": "error",
            "error": {
                "message": error_message,
                "details": str(error_details),
                "content": error_content,
            },
        }
    except Exception as e:
        logger.error(f"Unexpected error sending draft {draft_id}: {str(e)}")
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
        }
