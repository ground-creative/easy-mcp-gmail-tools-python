import os
import sys
from core.utils.state import global_state
from core.utils.env import EnvConfig
from app.tools.get_drafts import gmail_get_drafts_tool
from app.tools.create_draft import gmail_create_draft_tool
from app.tools.delete_draft import gmail_delete_draft_tool
from app.tools.send_draft import gmail_send_draft_tool
from app.tools.get_draft_details import gmail_get_draft_details_tool
from app.tools.get_emails import gmail_get_emails_tool
from app.tools.create_reply_draft import gmail_reply_draft_tool
from app.tools.update_draft import gmail_update_draft_tool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def test_list_drafts(auth_setup):
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Helper function for running a test case
    def run_test_case(description, **params):
        response = gmail_get_drafts_tool(**params)
        assert "error" not in response, f"{description} failed: {response.get('error')}"
        assert isinstance(
            response.get("drafts", []), list
        ), f"{description} returned non-list drafts"
        return response

    run_test_case(
        "Example 1 - Drafts with specific subject",
        query="subject:Important",
        max_results=5,
    )
    run_test_case(
        "Example 2 - Drafts with a specific label", label="INBOX", max_results=5
    )
    run_test_case(
        "Example 3 - Drafts with 'from' filter",
        query="from:someone@example.com",
        max_results=5,
    )
    run_test_case(
        "Example 4 - Drafts with specific subject and 'to' filter",
        query="subject:Important to:someone@example.com",
        max_results=5,
    )
    run_test_case(
        "Example 5 - Drafts with 'to' filter only",
        query="to:someone@example.com",
        max_results=5,
    )
    run_test_case(
        "Example 6 - Drafts with 'from' filter and pagination",
        query="from:someone@example.com",
        max_results=5,
    )

    base_response = run_test_case(
        "Example 7 - Base request for pagination",
        query="from:someone@example.com",
        max_results=5,
    )
    next_token = base_response.get("nextPageToken")
    if next_token:
        run_test_case(
            "Example 8 - Pagination with valid page token",
            query="from:someone@example.com",
            max_results=5,
            page_token=next_token,
        )
    else:
        pass


def test_create_update_and_delete_draft(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Create a new draft
    draft_data = {
        "to": "recipient@example.com",
        "subject": "Simple Draft Test",
        "body": "Just testing draft creation without attachments.",
        "cc": "",
        "bcc": "",
    }

    create_response = gmail_create_draft_tool(**draft_data)

    assert (
        create_response.get("status") == "success"
    ), f"Draft creation failed: {create_response}"
    assert "draft" in create_response, "No draft object returned"
    draft = create_response["draft"]
    assert "id" in draft, "Draft ID missing"
    draft_id = draft["id"]

    # Step 3: Modify the draft
    modified_draft_data = {
        "draft_id": draft_id,
        "subject": "Updated Subject",
        "body": "This is an updated draft body content.",
        "to": "updatedrecipient@example.com",  # Optionally update recipient
        "cc": "cc@example.com",  # Optionally add CC
        "bcc": "bcc@example.com",  # Optionally add BCC
        "is_html": True,  # Specify if the body should be HTML
    }

    modify_response = gmail_update_draft_tool(**modified_draft_data)

    assert (
        modify_response.get("status") == "success"
    ), f"Draft modification failed: {modify_response}"
    updated_draft = modify_response.get("draft")
    assert updated_draft, "No updated draft returned"
    assert updated_draft.get("id") == draft_id, "Draft ID mismatch after update"

    # Step 4: Request a confirmation token for deletion
    confirmation_response = gmail_delete_draft_tool(draft_id=draft_id)

    assert (
        "confirmation_token" in confirmation_response
    ), "Confirmation token is missing"
    confirmation_token = confirmation_response["confirmation_token"]

    # Step 5: Delete the draft using the confirmation token
    delete_response = gmail_delete_draft_tool(
        draft_id=draft_id, confirmation_token=confirmation_token
    )

    # Step 6: Assert the draft was deleted successfully
    assert (
        "error" not in delete_response
    ), f"Failed to delete draft: {delete_response.get('error')}"
    assert (
        delete_response.get("status") == "success"
    ), f"Unexpected status: {delete_response.get('status')}"


def test_create_and_send_draft(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Create a new draft
    draft_data = {
        "to": EnvConfig.get("TEST_EMAIL_RECIPIENT"),
        "subject": "Simple Draft Send Test",
        "body": "Just testing draft sending without attachments.",
    }

    create_response = gmail_create_draft_tool(**draft_data)

    assert (
        create_response.get("status") == "success"
    ), f"Draft creation failed: {create_response}"
    assert "draft" in create_response, "No draft object returned"
    draft = create_response["draft"]
    assert "id" in draft, "Draft ID missing"
    draft_id = draft["id"]

    # Step 3: Send the draft using the draft ID
    send_response = gmail_send_draft_tool(draft_id=draft_id)

    # Step 4: Assert the draft was sent successfully
    assert (
        "error" not in send_response
    ), f"Failed to send draft: {send_response.get('error')}"
    assert (
        send_response.get("status") == "success"
    ), f"Unexpected status: {send_response.get('status')}"
    assert "response" in send_response, "No response object returned from sending draft"


def test_get_draft_details(auth_setup):
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 1: Fetch a list of drafts
    list_response = gmail_get_drafts_tool(max_results=1)

    assert (
        "error" not in list_response
    ), f"Failed to get drafts: {list_response.get('error')}"
    drafts = list_response.get("drafts", [])
    assert isinstance(drafts, list) and len(drafts) > 0, "No drafts returned"

    # Step 2: Extract first draft ID
    draft_id = drafts[0].get("id")
    assert draft_id, "Draft ID is missing from the first draft"

    # Step 3: Get the draft details
    detail_response = gmail_get_draft_details_tool(draft_id=draft_id)

    # Step 4: Assertions
    assert (
        "error" not in detail_response
    ), f"Failed to get draft details: {detail_response.get('error')}"
    assert isinstance(
        detail_response, dict
    ), "Draft detail response is not a dictionary"
    assert (
        "subject" in detail_response["draft"] and "body" in detail_response["draft"]
    ), "Draft detail missing expected fields (subject, body)"
    assert (
        "from" in detail_response["draft"] and "to" in detail_response["draft"]
    ), "Draft detail missing expected header fields (from, to)"
    assert (
        "gmail_link" in detail_response["draft"]
    ), "Draft detail missing Gmail link field"


def test_create_and_delete_reply_draft(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Get the emails
    email_response = gmail_get_emails_tool(
        folder="INBOX",
        max_results=1,
        query=f"from:{EnvConfig.get("TEST_EMAIL_RECIPIENT")}",
    )

    assert "messages" in email_response, f"Failed to fetch emails: {email_response}"

    # Assuming we have at least one email to reply to
    email = email_response["messages"][0]
    assert "id" in email, "Email ID is missing"
    message_id = email["id"]

    # Step 3: Create a reply draft using the email's message_id and thread_id
    draft_data = {
        "body": f"Just replying to your email: {message_id}",
        "message_id": message_id,
    }

    create_response = gmail_reply_draft_tool(**draft_data)

    assert (
        create_response.get("status") == "success"
    ), f"Draft creation failed: {create_response}"
    assert "draft" in create_response, "No draft object returned"
    draft = create_response["draft"]
    assert "id" in draft, "Draft ID missing"
    draft_id = draft["id"]

    # Step 3: Request a confirmation token for deletion
    confirmation_response = gmail_delete_draft_tool(draft_id=draft_id)

    assert (
        "confirmation_token" in confirmation_response
    ), "Confirmation token is missing"
    confirmation_token = confirmation_response["confirmation_token"]

    # Step 4: Delete the draft using the confirmation token
    delete_response = gmail_delete_draft_tool(
        draft_id=draft_id, confirmation_token=confirmation_token
    )

    # Step 5: Assert the draft was deleted successfully
    assert (
        "error" not in delete_response
    ), f"Failed to delete draft: {delete_response.get('error')}"
    assert (
        delete_response.get("status") == "success"
    ), f"Unexpected status: {delete_response.get('status')}"


def test_create_and_send_reply_draft(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Get the emails
    email_response = gmail_get_emails_tool(
        folder="INBOX",
        max_results=1,
        query=f"from:{EnvConfig.get("TEST_EMAIL_RECIPIENT")}",
    )

    assert "messages" in email_response, f"Failed to fetch emails: {email_response}"

    # Assuming we have at least one email to reply to
    email = email_response["messages"][0]
    assert "id" in email, "Email ID is missing"
    message_id = email["id"]

    # Step 3: Create a reply draft using the email's message_id and thread_id
    draft_data = {
        "body": f"Just replying to your email: {message_id}",
        "message_id": message_id,
    }

    create_response = gmail_reply_draft_tool(**draft_data)

    assert (
        create_response.get("status") == "success"
    ), f"Draft creation failed: {create_response}"
    assert "draft" in create_response, "No draft object returned"
    draft = create_response["draft"]
    assert "id" in draft, "Draft ID missing"
    draft_id = draft["id"]

    # Step 3: Send the draft using the draft ID
    send_response = gmail_send_draft_tool(draft_id=draft_id)

    # Step 4: Assert the draft was sent successfully
    assert (
        "error" not in send_response
    ), f"Failed to send draft: {send_response.get('error')}"
    assert (
        send_response.get("status") == "success"
    ), f"Unexpected status: {send_response.get('status')}"
    assert "response" in send_response, "No response object returned from sending draft"
