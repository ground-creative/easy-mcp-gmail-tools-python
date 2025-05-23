from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict
from pydantic import Field
from typing_extensions import Annotated
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.tools import doc_tag, doc_name
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
import html
import base64
import email

@doc_tag("Drafts")
@doc_name("Get drafts")
def gmail_get_drafts_tool(
    query: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Search query to filter drafts (e.g., 'subject:Important').",
        ),
    ] = None,
    label: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Label to filter drafts (e.g., 'INBOX', 'IMPORTANT').",
        ),
    ] = None,
    max_results: Annotated[
        int,
        Field(
            default=10,
            description="Maximum number of drafts to return in a single request (max 100).",
        ),
    ] = 10,
    page_token: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Token to retrieve the next page of results, used for pagination.",
        ),
    ] = None,
) -> Dict:
    """
    List all drafts in the user's Gmail account with optional label and query filters, pagination, and result limits.

    * Requires Gmail API scope.

    Args:
    - query (str, optional): Gmail search query (e.g., 'subject:Important').
    - label (str, optional): Gmail label to filter drafts (e.g., 'INBOX').
    - max_results (int, optional): Number of results to return (max 100).
    - page_token (str, optional): Pagination token to fetch the next page.

    Returns:
    - dict: Drafts data or error details.

    Example Payloads:

    # Example 1: Get drafts with a specific subject
    gmail_list_drafts_tool(query="subject:Important", max_results=5)

    # Example 2: Get drafts filtered by recipient email
    gmail_list_drafts_tool(query="to:someone@example.com", max_results=5)

    # Example 3: Get drafts with a specific label (if applicable)
    gmail_list_drafts_tool(label="INBOX", max_results=5)

    # Example 4: Get drafts with pagination - Get drafts with a specific subject, and the next page of results
    gmail_list_drafts_tool(query="subject:Important", max_results=5, page_token="next_page_token")

    # Example 5: Get drafts with a specific search query and a higher result limit
    gmail_list_drafts_tool(query="from:someone@example.com", max_results=20)
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

        # Build the Gmail search query
        filters = []
        if label:
            filters.append(f"label:{label}")
        if query:
            filters.append(query)
        query_string = " ".join(filters) if filters else None

        # List drafts
        drafts = (
            service.users()
            .drafts()
            .list(
                userId="me",
                q=query_string,
                maxResults=max_results,
                pageToken=page_token,
            )
            .execute()
        )

        if "drafts" not in drafts:
            return {
                "status": "success",
                "drafts": [],
                "nextPageToken": None,
            }

        drafts_data = drafts["drafts"]

        # Fetch detailed info for each draft sequentially
        detailed_drafts = []
        for draft in drafts_data:
            try:
                draft_id = draft["id"]
                draft_msg = (
                    service.users()
                    .drafts()
                    .get(userId="me", id=draft_id, format="raw")
                    .execute()
                )

                raw_data = draft_msg.get("message", {}).get("raw")
                if not raw_data:
                    continue

                msg_bytes = base64.urlsafe_b64decode(raw_data.encode("ASCII"))
                mime_msg = email.message_from_bytes(msg_bytes)

                detailed_drafts.append({
                    "id": draft_id,
                    "subject": mime_msg.get("Subject", ""),
                    "from": mime_msg.get("From", ""),
                    "to": mime_msg.get("To", ""),
                    "date": mime_msg.get("Date", ""),
                    "snippet": html.unescape(draft_msg.get("message", {}).get("snippet", "")),
                })

            except Exception as e:
                logger.error(f"Error fetching draft {draft.get('id')}: {str(e)}")
                continue

        return {
            "status": "success",
            "drafts": detailed_drafts,
            "nextPageToken": drafts.get("nextPageToken"),
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
