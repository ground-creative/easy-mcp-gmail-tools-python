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


@doc_tag("Labels")
@doc_name("Add or remove labels from emails")
def gmail_manage_labels_tool(
    message_ids: Annotated[
        List[str],
        Field(description="List of Gmail message IDs of emails to modify."),
    ],
    labels: Annotated[
        List[str],
        Field(
            description=(
                "List of Gmail label names to apply or remove. "
                "Examples include: 'IMPORTANT', 'CATEGORY_PROMOTIONS', "
                "'CATEGORY_SOCIAL', 'SNOOZED', etc."
            ),
        ),
    ],
    action: Annotated[
        str,
        Field(
            description=(
                "Action to perform: 'add' to add labels, 'remove' to remove labels."
                " Default is 'add'."
            ),
            default="add",
        ),
    ] = "add",
) -> Dict:
    """
    Adds or removes Gmail labels to/from multiple emails based on the provided action.

    Requires Gmail API permission scopes.

    Args:
    - message_ids (List[str]): List of Gmail message IDs of the emails to modify.
    - labels (List[str]): List of Gmail label names to apply or remove. These must be valid Gmail system or custom labels.
      Examples: 'IMPORTANT', 'CATEGORY_UPDATES'.
    - action (str): Action to perform. 'add' to add labels, 'remove' to remove labels.

    Returns:
    - dict: A result object indicating success or failure, with any relevant error details from the Gmail API.
    """

    auth_response = check_access(True)
    if auth_response:
        return auth_response

    service = global_state.get("google_gmail_service")
    if not service:
        logger.error("Google Gmail service is not available in global state.")
        return {
            "status": "error",
            "error": (
                "Gmail permission scope not available, "
                f"please add this scope here: {EnvConfig.get('APP_HOST')}/auth/login"
            ),
        }

    try:
        all_labels = (
            service.users().labels().list(userId="me").execute().get("labels", [])
        )
        label_map = {label["name"]: label["id"] for label in all_labels}
        label_ids = [label_map[name] for name in labels if name in label_map]

        if not label_ids:
            return {
                "status": "error",
                "error": "None of the provided label names matched existing Gmail labels.",
            }

        action_field = "addLabelIds" if action == "add" else "removeLabelIds"
        if action not in ["add", "remove"]:
            return {
                "status": "error",
                "error": "Invalid action. Use 'add' or 'remove'.",
            }

        for msg_id in message_ids:
            try:
                service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={action_field: label_ids},
                ).execute()
                logger.info(f"Labels {action}ed to/from message {msg_id}")
            except HttpError as e:
                error_msg = (
                    e.error_details if hasattr(e, "error_details") else e.content
                )
                logger.error(f"Failed to {action} labels on {msg_id}: {error_msg}")
                return {
                    "status": "error",
                    "message_id": msg_id,
                    "error": f"Google API error while {action}ing labels: {error_msg}",
                }

        return {"status": "success", "message": f"Labels {action}ed to/from emails."}

    except Exception as e:
        logger.exception(f"Unexpected error while {action}ing labels.")
        return {"status": "error", "error": str(e)}
