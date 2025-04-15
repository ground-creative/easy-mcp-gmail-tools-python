import os
import sys
from core.utils.state import global_state
from core.utils.env import EnvConfig
from app.tools.get_conversation import gmail_get_thread_conversation_tool
from app.tools.get_emails import gmail_get_emails_tool
from app.tools.get_email_details import gmail_get_email_details_tool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def test_get_conversation(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    # Step 1: Fetch a list of emails
    list_response = gmail_get_emails_tool(
        folder="INBOX",
        query=f"from:{EnvConfig.get('TEST_EMAIL_RECIPIENT')}",
        max_results=1,
    )
    assert list_response["status"] == "success", "Failed to fetch emails"

    # Step 2: Extract first message ID
    message_id = list_response["messages"][0].get("id")
    assert message_id, "Message ID is missing from the first email"

    # Step 3: Get the email details
    detail_response = gmail_get_email_details_tool(message_id=message_id)

    conversations = gmail_get_thread_conversation_tool(
        thread_id="1963546d69facbbb", format="minimal"
    )

    print(conversations)

    assert conversations["status"] == "success", "Failed to get conversation"
