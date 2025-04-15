from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import Field
from typing_extensions import Annotated
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
from core.utils.tools import doc_tag, doc_name


@doc_tag("Labels")
@doc_name("Create label")
def gmail_create_label_tool(
    label_name: Annotated[
        str, Field(description="The name of the new label to create.")
    ],
) -> dict:
    """
    Create a new label in the user's Gmail account.

    * Requires permission scope for Gmail.

    Args:
    - label_name (str): The name of the label to be created.

    Returns:
    - dict: Success or failure message along with label details or error.
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

        # Create the new label
        label = {
            "name": label_name,
            "labelListVisibility": "labelShow",  # This means the label will be visible in the label list
            "messageListVisibility": "show",  # This means the label will be shown when viewing messages
        }

        created_label = (
            service.users().labels().create(userId="me", body=label).execute()
        )

        # Return the created label details
        return {
            "status": "success",
            "message": f"Label '{label_name}' created successfully.",
            "label": created_label,
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
