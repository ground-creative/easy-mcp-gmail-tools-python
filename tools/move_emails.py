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
@doc_name("Move emails")
def gmail_move_emails_tool(
    message_ids: Annotated[
        List[str],
        Field(description="List of Gmail message IDs of the emails to modify."),
    ],
    new_folder_label: Annotated[
        str,
        Field(
            description="The folder name to add as the new folder for the email (e.g., 'INBOX', 'SPAM', 'TRASH')."
        ),
    ],
) -> Dict:
    """
    Moves Gmail emails to a new folder by removing current folder labels (system/user) and adding a new one.

    * Requires permission scope for Gmail.

    Args:
    - message_ids (List[str]): List of Gmail message IDs of the emails.
    - new_folder_label (str): The new folder label to apply (e.g., 'INBOX', 'SPAM', 'TRASH').

    Returns:
        - dict: Result of the operation or error details.
    """

    auth_response = check_access(True)
    if auth_response:
        return auth_response

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
        # System-defined folder labels (actual Gmail folders)
        system_folder_labels = {
            "INBOX",
            # "SENT",
            "DRAFT",
            "TRASH",
            "SPAM",
            "CHAT",
            "[Imap]/Sent",
        }

        all_labels = (
            service.users().labels().list(userId="me").execute().get("labels", [])
        )

        # Create a map of label name to ID for later use
        label_name_to_id = {label["name"]: label["id"] for label in all_labels}

        # Ensure new folder label exists
        if new_folder_label not in label_name_to_id:
            return {
                "status": "error",
                "error": f"Label '{new_folder_label}' not found.",
            }

        # Build a list of folder labels (user + system folders)
        folder_label_ids = {
            label["id"]
            for label in all_labels
            if (label["type"] == "system" and label["name"] in system_folder_labels)
            or label["type"] == "user"
        }

        new_folder_label_id = label_name_to_id[new_folder_label]

        for message_id in message_ids:
            try:
                msg = (
                    service.users().messages().get(userId="me", id=message_id).execute()
                )
                current_labels = set(msg.get("labelIds", []))

                # Determine folder labels to remove (excluding the one we want to keep)
                labels_to_remove = [
                    label_id
                    for label_id in current_labels
                    if label_id in folder_label_ids and label_id != new_folder_label_id
                ]

                # Modify the labels
                service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={
                        "removeLabelIds": labels_to_remove,
                        "addLabelIds": [new_folder_label_id],
                    },
                ).execute()

                logger.info(f"Moved message {message_id} to '{new_folder_label}'.")

            except HttpError as email_error:
                error_message = email_error._get_reason()
                logger.error(
                    f"Error modifying email {message_id}",
                    extra={"error_message": error_message},
                )
                return {
                    "status": "error",
                    "error": f"Failed to modify email {message_id}: {error_message}",
                }

        return {
            "status": "success",
            "message": f"Email(s) successfully moved to '{new_folder_label}'",
        }

    except HttpError as email_error:
        error_message = getattr(email_error, "_get_reason", lambda: str(email_error))()
        logger.error(f"Error modifying email {message_id}: {error_message}")
        return {
            "status": "error",
            "error": f"Failed to modify email {message_id}: {error_message}",
        }

    except Exception as general_error:
        logger.exception("Unexpected error occurred.")
        return {
            "status": "error",
            "error": {"message": "Unexpected error", "details": str(general_error)},
        }
