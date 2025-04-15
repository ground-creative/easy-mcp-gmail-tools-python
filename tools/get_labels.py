from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict
from core.utils.state import global_state
from core.utils.env import EnvConfig
from core.utils.logger import logger
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.tools import doc_tag, doc_name


@doc_tag("Labels")
@doc_name("Get labels")
def gmail_list_labels_tool() -> Dict:
    """
    Retrieve a list of all Gmail labels for the authenticated user.

    * Requires permission scope for Gmail.

    Returns:
    - dict: A dictionary containing label names, IDs, or error information.
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

        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        return {
            "status": "success",
            "labels": [{"id": label["id"], "name": label["name"]} for label in labels],
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
