import os
import sys
from core.utils.state import global_state
from app.tools.get_labels import gmail_list_labels_tool
from app.tools.create_label import gmail_create_label_tool
from app.tools.delete_label import gmail_delete_label_tool
from app.tools.manage_labels import gmail_manage_labels_tool
from app.tools.get_emails import gmail_get_emails_tool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def test_list_labels(auth_setup):
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 1: Fetch a list of labels
    labels_response = gmail_list_labels_tool()

    assert (
        "error" not in labels_response
    ), f"Failed to get labels: {labels_response.get('error')}"
    labels = labels_response.get("labels", [])
    assert isinstance(labels, list) and len(labels) > 0, "No labels returned"

    # Step 2: Validate labels
    for label in labels:
        assert (
            "id" in label and "name" in label
        ), f"Label is missing 'id' or 'name': {label}"

    # Optional: Validate that labels include some known ones, such as 'INBOX' or 'SPAM'
    known_labels = ["INBOX", "SPAM"]
    found_labels = [label["name"] for label in labels]
    for known_label in known_labels:
        assert known_label in found_labels, f"Expected label {known_label} not found"


def test_create_and_delete_label(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Create a new label
    label_name = "Test Label"  # Change this to a desired label name
    create_response = gmail_create_label_tool(label_name=label_name)

    assert (
        "error" not in create_response
    ), f"Failed to create label: {create_response.get('error')}"
    assert (
        create_response.get("status") == "success"
    ), f"Unexpected status: {create_response.get('status')}"

    # Step 3: Get the created label's ID
    created_label = create_response.get("label")
    assert created_label, "Label creation response missing label details"
    label_id = created_label.get("id")
    assert label_id, "Label ID is missing"

    # Step 4: Request a confirmation token for deletion (this mimics the server generating the token)
    confirmation_response = gmail_delete_label_tool(label_id=label_id)

    # Ensure a confirmation token is provided
    assert (
        "confirmation_token" in confirmation_response
    ), "Confirmation token is missing"
    confirmation_token = confirmation_response["confirmation_token"]

    # Step 5: Now delete the label with the confirmation token
    delete_response = gmail_delete_label_tool(
        label_id=label_id, confirmation_token=confirmation_token
    )

    # Step 6: Assert the label was deleted successfully
    assert (
        "error" not in delete_response
    ), f"Failed to delete label: {delete_response.get('error')}"
    assert (
        delete_response.get("status") == "success"
    ), f"Unexpected status: {delete_response.get('status')}"


def test_add_and_remove_labels_to_emails(auth_setup):
    # Step 1: Check if authenticated
    is_authenticated = global_state.get(
        "middleware.GoogleAuthMiddleware.is_authenticated"
    )
    assert is_authenticated, "Not authenticated"

    # Step 2: Get the first email from the inbox
    query = "is:inbox"
    get_email_response = gmail_get_emails_tool(query=query, max_results=1)

    # Step 3: Assert the response and get the first email's ID
    assert (
        get_email_response.get("status") == "success"
    ), f"Failed to fetch emails: {get_email_response}"
    emails = get_email_response.get("messages", [])
    assert emails, "No emails found"

    message_id = emails[0]["id"]

    # Step 4: Add labels to the email
    labels_to_add = ["IMPORTANT", "CATEGORY_PERSONAL"]
    add_labels_response = gmail_manage_labels_tool(
        message_ids=[message_id],
        labels=labels_to_add,
        action="add",
    )
    assert (
        add_labels_response.get("status") == "success"
    ), f"Failed to add labels: {add_labels_response}"

    # Step 5: Remove labels from the email
    remove_labels_response = gmail_manage_labels_tool(
        message_ids=[message_id],
        labels=labels_to_add,
        action="remove",
    )
    assert (
        remove_labels_response.get("status") == "success"
    ), f"Failed to remove labels: {remove_labels_response}"
