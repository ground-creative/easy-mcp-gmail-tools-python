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
@doc_name("Archive emails")
def gmail_archive_emails_tool(
    message_ids: Annotated[
        List[str],
        Field(description="List of Gmail message IDs of the emails to modify."),
    ],
) -> Dict:
    """
    Archives the specified Gmail emails

    * Requires permission scope for Gmail.

    Args:
    - message_ids (List[str]): A list of Gmail message IDs for the emails to be archived.

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
        # label_name_to_id = {label["name"]: label["id"] for label in all_labels}

        # Build a list of folder labels (user + system folders)
        folder_label_ids = {
            label["id"]
            for label in all_labels
            if (label["type"] == "system" and label["name"] in system_folder_labels)
            or label["type"] == "user"
        }

        for message_id in message_ids:
            try:
                msg = (
                    service.users().messages().get(userId="me", id=message_id).execute()
                )
                current_labels = set(msg.get("labelIds", []))

                # Remove all labels (user and system)
                labels_to_remove = [
                    label_id
                    for label_id in current_labels
                    if label_id in folder_label_ids
                ]

                # Modify the labels by removing all of them
                service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": labels_to_remove},
                ).execute()

                logger.info(f"Removed all labels from message {message_id}.")

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
            "message": f"Email(s) successfully had all labels removed.",
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
