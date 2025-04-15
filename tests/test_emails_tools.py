import os
import sys
from core.utils.state import global_state
from core.utils.env import EnvConfig
from app.tools.get_emails import gmail_get_emails_tool
from app.tools.get_email_details import gmail_get_email_details_tool
from app.tools.send_email import gmail_send_email_tool
from app.tools.mark_emails import gmail_mark_emails_tool
from app.tools.set_emails_as_spam import gmail_set_emails_as_spam_tool
from app.tools.star_emails import gmail_star_emails_tool
from app.tools.move_emails import gmail_move_emails_tool
from app.tools.archive_emails import gmail_archive_emails_tool
from app.tools.create_reply_email import gmail_reply_email_tool
from app.tools.forward_email import gmail_forward_email_tool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def test_get_emails(auth_setup):
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Helper function for running a test case
    def run_test_case(description, **params):
        response = gmail_get_emails_tool(**params)
        assert "error" not in response, f"{description} failed: {response.get('error')}"
        assert isinstance(
            response.get("messages", []), list
        ), f"{description} returned non-list messages"
        return response

    run_test_case(
        "Example 1 - From specific sender",
        query=f"from:{EnvConfig.get('TEST_EMAIL_RECIPIENT')}",
        max_results=5,
    )
    run_test_case(
        "Example 2 - Unread from label CATEGORY_PROMOTIONS",
        label="CATEGORY_PROMOTIONS",
        is_unread=True,
        max_results=10,
    )
    run_test_case(
        "Example 3 - To recipient",
        query=f"to:{EnvConfig.get('TEST_EMAIL_RECIPIENT')}",
        max_results=5,
    )
    run_test_case("Example 4 - From SPAM folder", folder="SPAM", max_results=5)
    run_test_case(
        "Example 5 - Subject filter", query="subject:Important Meeting", max_results=5
    )
    run_test_case(
        "Example 6 - To recipient with name", query="to:John Doe", max_results=5
    )

    base_response = run_test_case(
        "Example 7 - Base request for pagination",
        query=f"from:{EnvConfig.get('TEST_EMAIL_RECIPIENT')}",
        max_results=5,
    )
    next_token = base_response.get("nextPageToken")
    if next_token:
        run_test_case(
            "Example 6 - Pagination with valid page token",
            query=f"from:{EnvConfig.get('TEST_EMAIL_RECIPIENT')}",
            max_results=5,
            page_token=next_token,
        )
    else:
        pass


def test_get_email_details(auth_setup):
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 1: Fetch a list of emails
    list_response = gmail_get_emails_tool(max_results=1)

    assert (
        "error" not in list_response
    ), f"Failed to get emails: {list_response.get('error')}"
    messages = list_response.get("messages", [])
    assert isinstance(messages, list) and len(messages) > 0, "No emails returned"

    # Step 2: Extract first message ID
    message_id = messages[0].get("id")
    assert message_id, "Message ID is missing from the first email"

    # Step 3: Get the email details
    detail_response = gmail_get_email_details_tool(message_id=message_id)

    # Step 4: Assertions
    assert (
        "error" not in detail_response
    ), f"Failed to get email details: {detail_response.get('error')}"


def test_send_email_tool(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Set up email data
    to = EnvConfig.get("TEST_EMAIL_RECIPIENT")  # Pass as a string, not a tuple
    subject = "Test Email from Gmail API"
    body = "This is a test email sent via Gmail API for testing purposes."

    # Call the function to send the email
    send_response = gmail_send_email_tool(
        to=to,
        subject=subject,
        body=body,
    )

    # Step 3: Assert the response
    assert (
        send_response.get("status") == "success"
    ), f"Failed to send email: {send_response}"

    # Check if 'sent_message' is in the response
    sent_message = send_response.get("sent_message")
    assert sent_message is not None, "No sent_message returned"

    # Assert that 'sent_message' contains 'id'
    assert "id" in sent_message, "Sent message ID missing"


def test_send_html_email_tool(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Set up email data
    to = EnvConfig.get("TEST_EMAIL_RECIPIENT")  # Pass as a string, not a tuple
    subject = "Test HTML Email from Gmail API"
    # HTML body for the email
    body = """
    <html>
        <body>
            <h1>This is a test email</h1>
            <p>Sent via <strong>Gmail API</strong> for testing purposes.</p>
            <p><em>HTML email test content</em></p>
        </body>
    </html>
    """

    # Call the function to send the email
    send_response = gmail_send_email_tool(
        to=to,
        subject=subject,
        body=body,
        is_html=True,  # Indicate that the body is in HTML format
    )

    # Step 3: Assert the response
    assert (
        send_response.get("status") == "success"
    ), f"Failed to send email: {send_response}"

    # Check if 'sent_message' is in the response
    sent_message = send_response.get("sent_message")
    assert sent_message is not None, "No sent_message returned"

    # Assert that 'sent_message' contains 'id'
    assert "id" in sent_message, "Sent message ID missing"


def test_mark_email_as_unread_and_read(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Get the first email from the inbox
    query = "is:inbox"  # You can adjust the query if needed
    get_email_response = gmail_get_emails_tool(query=query, max_results=1)

    # Step 3: Assert the response and get the first email's ID
    assert (
        get_email_response.get("status") == "success"
    ), f"Failed to fetch emails: {get_email_response}"
    emails = get_email_response.get("messages", [])
    assert emails, "No emails found"

    message_id = emails[0]["id"]

    # Step 4: Mark the email as unread
    mark_as_unread_response = gmail_mark_emails_tool(
        message_ids=[message_id], mark_as_read=False
    )
    assert (
        mark_as_unread_response.get("status") == "success"
    ), f"Failed to mark email as unread: {mark_as_unread_response}"

    # Step 5: Mark the email as read
    mark_as_read_response = gmail_mark_emails_tool(
        message_ids=[message_id], mark_as_read=True
    )
    assert (
        mark_as_read_response.get("status") == "success"
    ), f"Failed to mark email as read: {mark_as_read_response}"


def test_mark_email_as_spam_and_not_spam(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Get the first email from the inbox
    query = "is:inbox"  # You can adjust the query if needed
    get_email_response = gmail_get_emails_tool(query=query, max_results=1)

    # Step 3: Assert the response and get the first email's ID
    assert (
        get_email_response.get("status") == "success"
    ), f"Failed to fetch emails: {get_email_response}"
    emails = get_email_response.get("messages", [])
    assert emails, "No emails found"

    message_id = emails[0]["id"]

    # Step 4: Mark the email as spam
    mark_as_spam_response = gmail_set_emails_as_spam_tool(
        message_ids=[message_id], mark_as_spam=True
    )
    assert (
        mark_as_spam_response.get("status") == "success"
    ), f"Failed to mark email as spam: {mark_as_spam_response}"

    # Step 5: Unmark the email as spam (move it out of spam)
    mark_as_not_spam_response = gmail_set_emails_as_spam_tool(
        message_ids=[message_id], mark_as_spam=False
    )
    assert (
        mark_as_not_spam_response.get("status") == "success"
    ), f"Failed to unmark email as spam: {mark_as_not_spam_response}"


def test_star_and_unstar_email(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Get the first email from the inbox
    query = "is:inbox"  # You can adjust the query if needed
    get_email_response = gmail_get_emails_tool(query=query, max_results=1)

    # Step 3: Assert the response and get the first email's ID
    assert (
        get_email_response.get("status") == "success"
    ), f"Failed to fetch emails: {get_email_response}"
    emails = get_email_response.get("messages", [])
    assert emails, "No emails found"

    message_id = emails[0]["id"]

    # Step 4: Star the email
    star_email_response = gmail_star_emails_tool(
        message_ids=[message_id], star_email=True
    )
    assert (
        star_email_response.get("status") == "success"
    ), f"Failed to star email: {star_email_response}"

    # Step 5: Unstar the email
    unstar_email_response = gmail_star_emails_tool(
        message_ids=[message_id], star_email=False
    )
    assert (
        unstar_email_response.get("status") == "success"
    ), f"Failed to unstar email: {unstar_email_response}"


def test_move_email_to_trash_and_back(auth_setup):
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 1: Fetch a list of emails
    list_response = gmail_get_emails_tool(folder="INBOX", max_results=1)
    assert list_response["status"] == "success", "Failed to fetch emails"

    email_ids = [email["id"] for email in list_response.get("messages", [])]
    assert email_ids, "No emails found"

    message_id = email_ids[0]  # Get the ID of the first email

    # Step 2: Move the email to the Trash
    move_to_trash_response = gmail_move_emails_tool(
        message_ids=[message_id], new_folder_label="TRASH"
    )
    assert (
        move_to_trash_response["status"] == "success"
    ), "Failed to move email to Trash"
    assert "TRASH" in move_to_trash_response["message"], "Email was not moved to Trash"

    # Step 3: Move the email back to the Inbox
    move_to_inbox_response = gmail_move_emails_tool(
        message_ids=[message_id], new_folder_label="INBOX"
    )
    assert (
        move_to_inbox_response["status"] == "success"
    ), "Failed to move email back to Inbox"
    assert (
        "INBOX" in move_to_inbox_response["message"]
    ), "Email was not moved back to Inbox"


def test_archive_email_and_move_back_to_inbox(auth_setup):
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 1: Fetch a list of emails
    list_response = gmail_get_emails_tool(folder="INBOX", max_results=1)
    assert list_response["status"] == "success", "Failed to fetch emails"

    email_ids = [email["id"] for email in list_response.get("messages", [])]
    assert email_ids, "No emails found"

    message_id = email_ids[0]  # Get the ID of the first email

    # Step 2: Move the email to the Trash
    move_to_trash_response = gmail_archive_emails_tool(message_ids=[message_id])
    assert move_to_trash_response["status"] == "success", "Failed to archive email"

    # Step 3: Move the email back to the Inbox
    move_to_inbox_response = gmail_move_emails_tool(
        message_ids=[message_id], new_folder_label="INBOX"
    )
    assert (
        move_to_inbox_response["status"] == "success"
    ), "Failed to move email back to Inbox"
    assert (
        "INBOX" in move_to_inbox_response["message"]
    ), "Email was not moved back to Inbox"


def test_reply_email_tool(auth_setup):
    # Step 1: Fetch a list of emails
    list_response = gmail_get_emails_tool(
        folder="INBOX",
        query=f"from:{EnvConfig.get('TEST_EMAIL_RECIPIENT')}",
        max_results=1,
    )
    assert list_response["status"] == "success", "Failed to fetch emails"

    email_ids = [email["id"] for email in list_response.get("messages", [])]
    assert email_ids, "No emails found"

    message_id = email_ids[0]  # Get the ID of the first email

    # Step 2: Set up reply data
    body = "This is a test reply sent via Gmail API."

    # Call the function to reply to the email
    reply_response = gmail_reply_email_tool(
        message_id=message_id,
        body=body,
    )

    # Step 3: Assert the response
    assert (
        reply_response.get("status") == "success"
    ), f"Failed to reply to email: {reply_response}"


def test_reply_html_email_tool(auth_setup):
    # Step 1: Fetch a list of emails
    list_response = gmail_get_emails_tool(
        folder="INBOX",
        query=f"from:{EnvConfig.get('TEST_EMAIL_RECIPIENT')}",
        max_results=1,
    )
    assert list_response["status"] == "success", "Failed to fetch emails"

    email_ids = [email["id"] for email in list_response.get("messages", [])]
    assert email_ids, "No emails found"

    message_id = email_ids[0]  # Get the ID of the first email

    # Step 2: Set up reply data with HTML body
    body = """
    <html>
        <body>
            <h1>This is a test reply</h1>
            <p>Sent via <strong>Gmail API</strong> as an HTML reply.</p>
            <p><em>HTML email reply test content</em></p>
        </body>
    </html>
    """

    # Call the function to reply to the email
    reply_response = gmail_reply_email_tool(
        message_id=message_id,
        body=body,
        is_html=True,  # Indicate that the body is in HTML format
    )

    # Step 3: Assert the response
    assert (
        reply_response.get("status") == "success"
    ), f"Failed to reply to email: {reply_response}"

    # Check if 'sent_message' is in the response
    sent_message = reply_response.get("sent_message")
    assert sent_message is not None, "No sent_message returned"

    # Assert that 'sent_message' contains 'id'
    assert "id" in sent_message, "Sent message ID missing"


def test_forward_email_tool(auth_setup):
    # Step 1: Fetch a list of emails to forward
    list_response = gmail_get_emails_tool(
        folder="INBOX",
        max_results=1,
    )
    assert list_response["status"] == "success", "Failed to fetch emails"

    email_ids = [email["id"] for email in list_response.get("messages", [])]
    assert email_ids, "No emails found to forward"

    message_id = email_ids[0]  # Get the ID of the first email

    # Step 2: Set up forward data
    forward_to = EnvConfig.get("TEST_EMAIL_RECIPIENT")

    # Call the function to forward the email
    forward_response = gmail_forward_email_tool(
        message_id=message_id,
        forward_to=forward_to,
        body="testing forwarding",
    )

    # Step 3: Assert the response
    assert (
        forward_response.get("status") == "success"
    ), f"Failed to forward email: {forward_response}"
