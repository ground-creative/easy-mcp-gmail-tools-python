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

# Confirmation token validity in seconds
CONFIRMATION_TOKEN_VALIDITY_DURATION = 5 * 60  # 5 minutes


@doc_tag("Drafts")
@doc_name("Delete draft")
def gmail_delete_draft_tool(
    draft_id: Annotated[str, Field(description="The ID of the draft to delete.")],
    confirmation_token: Annotated[
        Optional[str],
        Field(
            description="An optional token to confirm the deletion. "
            "If not provided, a token will be generated based on the draft ID. "
            "This token must be used to confirm the deletion request."
        ),
    ] = None,
) -> dict:
    """
    Deletes a specified Gmail draft with confirmation logic.

    * Requires Gmail permission scope.

    The function first checks if a confirmation token is provided.
    If not, it generates a token based on the label ID.
    The user must then confirm the deletion using this token.
    If the token is provided, the function validates it before proceeding with the deletion.
    The token is valid for a specified duration.

    Args:
    - draft_id (str): The ID of the draft to delete.
    - confirmation_token (Optional[str]): A token to confirm deletion.

    Returns:
    - dict: Result message indicating success or required confirmation.

    Example Corret Usage:

    User: Delete draft with ID '123'
    # Get a confirmation token
    Action: gmail_delete_draft_tool(draft_id="123")
    # Ask confirmation
    Confirmation: Please confirm delete draft with id `123`.
    User: Ok.
    # Use token from previous request with same parameters
    Action: gmail_delete_draft_tool(draft_id="123", confirmation_token="XXXXX")

    Example Incorrect Usage:

    Incorrect Example 1:
    User: Delete draft with ID '123'
    Action: gmail_delete_draft_tool(draft_id="123", confirmation_token="made up token")
    What went wrong: A request to get a confirmation token was not issued and a made up token was used instead.

    Incorrect Example 2:
    User: Delete draft with ID '123'
    # Get a confirmation token
    Action: gmail_delete_draft_tool(draft_id="123")
    Action: gmail_delete_draft_tool(draft_id="123", confirmation_token="XXXXX")
    What went wrong: No confirmation was asked before deleting the draft.

    Incorrect Example 3:
    User: Delete draft with ID '123'
    # Get a confirmation token
    Action: gmail_delete_draft_tool(draft_id="123")
    # Ask confirmation
    Confirmation: Please confirm delete draft with id `123`.
    User: Ok.
    Action: gmail_delete_draft_tool(draft_id="456", confirmation_token="XXXXX")
    What went wrong: The draft ID in the request does not match the one in the confirmation token.

    Incorrect Example 4:
    User: Delete draft with ID '123'
    # Get a confirmation token
    Action: gmail_delete_draft_tool(draft_id="123")
    # Ask confirmation
    Confirmation: Please confirm delete draft with id `123`.
    User: Wait, I want to delete draft with ID '456' instead.
    Action: gmail_delete_draft_tool(draft_id="456", confirmation_token="XXXXX")
    What went wrong: The draft ID in the request does not match the one in the confirmation token. We need a new confirmation token.
    """
    logger.info(
        f"Request received to delete draft with ID '{draft_id}' and confirmation token: {confirmation_token}"
    )

    # Check authentication
    auth_response = check_access(True)
    if auth_response:
        return auth_response

    gmail_service = global_state.get("google_gmail_service")
    if gmail_service is None:
        logger.error("Google Gmail service is not available in global state.")
        return {
            "status": "error",
            "error": f"Gmail permission scope not available, please add this scope here: {EnvConfig.get('APP_HOST')}/auth/login",
        }

    if not confirmation_token:
        params_string = f"{draft_id}:{int(time.time())}"
        confirmation_token = base64.b64encode(params_string.encode()).decode()
        logger.info(f"Generated confirmation token: {confirmation_token}")
        return {
            "message": f"Confirmation required to delete draft with ID '{draft_id}'. Use the confirmation_token to confirm deletion.",
            "confirmation_token": confirmation_token,
            "action": "confirm_deletion",
        }

    try:
        decoded_params = base64.b64decode(confirmation_token).decode()
        token_draft_id, token_timestamp = decoded_params.split(":")
        token_timestamp = int(token_timestamp)

        if time.time() - token_timestamp > CONFIRMATION_TOKEN_VALIDITY_DURATION:
            return {
                "error": "Confirmation token has expired. Please request a new token."
            }

        if token_draft_id != draft_id:
            return {
                "error": "Invalid confirmation token. Parameters do not match.",
                "details": {
                    "token_params": {"draft_id": token_draft_id},
                    "request_params": {"draft_id": draft_id},
                },
            }

    except Exception as e:
        logger.error(f"Failed to decode confirmation token: {e}")
        return {"error": "Invalid confirmation token."}

    try:
        gmail_service.users().drafts().delete(userId="me", id=draft_id).execute()
        logger.info(f"Successfully deleted draft with ID: {draft_id}")
        return {"status": "success", "message": "Draft deleted successfully."}
    except HttpError as e:
        try:
            error_content = (
                e.error_details[0].get("message") if e.error_details else str(e)
            )
        except Exception:
            error_content = str(e)
        logger.error(
            f"Google Gmail API error while deleting draft {draft_id}: {error_content}"
        )
        return {"status": "error", "error": error_content}
    except Exception as e:
        logger.error(f"Unexpected error while deleting draft {draft_id}: {str(e)}")
        return {"status": "error", "error": f"Unexpected error: {str(e)}"}
