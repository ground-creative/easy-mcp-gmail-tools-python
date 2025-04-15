from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict
from pydantic import Field
from typing_extensions import Annotated
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.middleware.google.GoogleAuthMiddleware import check_access
from core.utils.tools import doc_tag, doc_name
from core.utils.logger import logger
from core.utils.state import global_state
from core.utils.env import EnvConfig
import html


@doc_tag("Emails")
@doc_name("Get emails")
def gmail_get_emails_tool(
    query: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Search query to filter emails (e.g., 'from:someone@example.com').",
        ),
    ] = None,
    label: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Label to filter emails by (e.g., 'STARRED', 'CATEGORY_PERSONAL', 'CATEGORY_PROMOTIONS').",
        ),
    ] = None,
    folder: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Folder ID to filter emails by (e.g., 'INBOX', 'SENT').",
        ),
    ] = None,
    is_unread: Annotated[
        Optional[bool],
        Field(
            default=None,
            description="If True, only show unread emails.",
        ),
    ] = None,
    max_results: Annotated[
        int,
        Field(
            default=10,
            description="Maximum number of emails to return in a single request (max 100).",
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
    Fetch a list of emails from Gmail based on specified filters.

    * Requires permission scope for Gmail.

    Args:
    - query (str, optional): Search query to filter emails (e.g., 'from:someone@example.com is:unread').
    - label (str, optional): Label to filter emails by (e.g., 'STARRED', 'CATEGORY_PERSONAL', 'CATEGORY_PROMOTIONS').
    - folder (str, optional): The label of the folder to filter emails by (e.g., 'INBOX', 'SENT').
    - is_unread (bool, optional): If True, only show unread emails will be returned.
    - max_results (int, optional): The maximum number of emails to return in a single request (default is 10, max is 100).
    - page_token (str, optional): Token to retrieve the next page of results for pagination.

    Returns:
    - dict: A dictionary containing the list of emails and any pagination information, or an error message.

    Example Payloads:

    # Example 1: Get emails from a specific sender
    gmail_get_emails_tool(query="from:someone@example.com", max_results=5)

    # Example 2: Get unread emails from a specific label
    gmail_get_emails_tool(label="CATEGORY_PROMOTIONS", is_unread=True, max_results=10)

    # Example 3: Get emails sent to a specific recipient
    gmail_get_emails_tool(query="to:someone@example.com", max_results=5)

    # Example 4: Get emails from a specific folder
    gmail_get_emails_tool(folder="INBOX", max_results=5)

    # Example 5: Get emails with a specific subject
    gmail_get_emails_tool(query="subject:Important Meeting", max_results=5)

    # Example 6: Pagination Example - Get emails from a specific sender with pagination
    gmail_get_emails_tool(query="from:someone@example.com", max_results=5, page_token="some_page_token")

    # Example 7: Get unread emails sent to a specific recipient name
    gmail_get_emails_tool(query="to:'John Doe' is:unread", max_results=5)

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

        if query and "to:" in query:
            parts = query.split("to:", 1)
            recipient = parts[1].strip()
            if " " in recipient:
                query = f'to:"{recipient}"'

        filters = []
        if query:
            filters.append(query)
        if is_unread:
            filters.append("is:unread")
        if label:
            filters.append(f"label:{label}")
        if folder:
            filters.append(f"label:{folder}")

        query_string = " ".join(filters) if filters else None

        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query_string,
                maxResults=max_results,
                pageToken=page_token,
            )
            .execute()
        )

        messages = results.get("messages", [])

        def _fetch_message_details(msg):
            try:
                msg_id = msg["id"]
                # Ensure each thread has a fresh service object to avoid SSL/TLS issues
                service = build(
                    "gmail",
                    "v1",
                    credentials=global_state.get("google_oauth_credentials"),
                )

                # Fetch the message details
                full_msg = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_id,
                        format="metadata",
                        metadataHeaders=["Subject", "From", "To", "Date"],
                    )
                    .execute()
                )

                # Extract headers
                headers = {
                    h["name"]: h["value"]
                    for h in full_msg.get("payload", {}).get("headers", [])
                }

                # Define a helper function to get and clean header values
                def get_header_value(name: str):
                    value = headers.get(name, None)
                    return html.unescape(value) if value is not None else ""

                # Build the return dictionary
                return {
                    "id": msg_id,
                    "threadId": full_msg.get("threadId"),
                    "subject": get_header_value("Subject"),
                    "from": get_header_value("From"),
                    "to": get_header_value("To"),
                    "date": get_header_value("Date"),
                    "snippet": html.unescape(full_msg.get("snippet", "")),
                }

            except Exception as e:
                logger.error(f"Error fetching message {msg.get('id')}: {str(e)}")
                return None

        # Process multiple messages concurrently with threading
        def fetch_messages_in_threads(messages):
            detailed_messages = []

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(_fetch_message_details, msg) for msg in messages
                ]

                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        detailed_messages.append(result)

            return detailed_messages

        detailed_messages = fetch_messages_in_threads(messages)

        return {
            "status": "success",
            "messages": detailed_messages,
            "nextPageToken": results.get("nextPageToken"),
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
