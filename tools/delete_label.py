import base64
import time
from typing import Optional
from typing_extensions import Annotated
from pydantic import Field
from googleapiclient.errors import HttpError
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.tools import doc_tag, doc_name

# Define the validity duration for the confirmation token (in seconds)
CONFIRMATION_TOKEN_VALIDITY_DURATION = 5 * 60  # 5 minutes


@doc_tag("Labels")
@doc_name("Delete label")
def gmail_delete_label_tool(
    label_id: Annotated[str, Field(description="The ID of the label to delete.")],
    confirmation_token: Annotated[
        Optional[str],
        Field(
            description="An optional token to confirm the deletion. "
            "If not provided, a token will be generated based on the label ID. "
            "This token must be used to confirm the deletion request."
        ),
    ] = None,
) -> dict:
    """
    Deletes a specified label from Gmail with confirmation logic.

    * Requires permission scope for Gmail.

    The function first checks if a confirmation token is provided.
    If not, it generates a token based on the label ID.
    The user must then confirm the deletion using this token.
    If the token is provided, the function validates it before proceeding with the deletion.
    The token is valid for a specified duration.

    Args:
    - label_id (str): The ID of the label to delete.
    - confirmation_token (Optional[str]): An optional token to confirm the deletion. If not provided, a token will be generated based on the label ID.

    Returns:
    - dict: Dictionary indicating success or error.
    """

    logger.info(
        f"Request received to delete label with ID '{label_id}' and confirmation token: {confirmation_token}"
    )

    # Check authentication
    auth_response = check_access(True)
    if auth_response:
        return auth_response

    # Retrieve the Gmail service from global state
    gmail_service = global_state.get("google_gmail_service")
    if gmail_service is None:
        logger.error("Google Gmail service is not available in global state.")
        return {
            "status": "error",
            "error": f"Gmail permission scope not available, please add this scope here: {EnvConfig.get('APP_HOST')}/auth/login",
        }

    # Generate a confirmation token if not provided
    if not confirmation_token:
        # Create a string with the request parameters and current timestamp
        params_string = f"{label_id}:{int(time.time())}"
        confirmation_token = base64.b64encode(params_string.encode()).decode()
        logger.info(f"Generated confirmation token: {confirmation_token}")
        return {
            "message": f"Confirmation required to delete label with ID '{label_id}', confirm deletion with user and use the given confirmation_token with the same request parameters.",
            "confirmation_token": confirmation_token,
            "action": "confirm_deletion",
        }

    # Decode and validate the confirmation token
    try:
        decoded_params = base64.b64decode(confirmation_token).decode()
        token_label_id, token_timestamp = decoded_params.split(":")
        token_timestamp = int(token_timestamp)

        # Check if the token has expired
        if time.time() - token_timestamp > CONFIRMATION_TOKEN_VALIDITY_DURATION:
            return {
                "error": "Confirmation token has expired. Please request a new token."
            }

        # Check if the parameters match
        if token_label_id != label_id:
            return {
                "error": "Invalid confirmation token. Parameters do not match, please request a new token.",
                "details": {
                    "token_params": {
                        "label_id": token_label_id,
                    },
                    "request_params": {
                        "label_id": label_id,
                    },
                },
            }

    except Exception as e:
        logger.error(f"Failed to decode confirmation token: {e}")
        return {"error": "Invalid confirmation token."}

    # Prepare to delete the label
    try:
        gmail_service.users().labels().delete(userId="me", id=label_id).execute()
        logger.info(f"Successfully deleted label with ID: {label_id}")
        return {"status": "success", "message": "Label deleted successfully."}
    except HttpError as e:
        try:
            error_content = (
                e.error_details[0].get("message") if e.error_details else str(e)
            )
        except Exception:
            error_content = str(e)
        logger.error(
            f"Google Gmail API error while deleting label {label_id}: {error_content}"
        )
        return {"status": "error", "error": error_content}
    except Exception as e:
        logger.error(f"Unexpected error while deleting label {label_id}: {str(e)}")
        return {"status": "error", "error": f"Unexpected error: {str(e)}"}
