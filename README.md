# Easy MCP Gmail Tools

This is a set of tools for gmail to be used with easy mcp server.<br>
https://github.com/ground-creative/easy-mcp-python

## Key Features

- **Drafts**: Create, reply, modify, delete, send, and fetch drafts.
- **Emails**: Send, reply, forward, archive, move, mark as read/unread or spam, and star emails.
- **Labels**: Create, delete, assign, and remove labels.
- **Threads**: View and manage email threads.

## Authentication

This application uses Google's OAuth service to authenticate users.
To use this app, you must create an OAuth 2.0 Client ID in the Google Cloud Console and configure the appropriate scopes for your application.

## Installation

1. Clone the repository from the root folder of the easy mcp installation:

```
git clone https://github.com/ground-creative/easy-mcp-gmail-tools-python.git app
```

2. Install requirements:

```
pip install -r app/requirements.txt
```

3. Generate encryption key:

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

4. Add parameters to env file:

```
APP_HOST=http://localhost:8000
DB_PATH=storage/sqlite_credentials.db
CYPHER=Your Encryption Key Here

# Optional
SITE_URL=Full application site URL
SITE_NAME=Application Name
```

5. Add `client_secrets.json` in storage folder

6. Run the server:

```
# Run via fastapi wrapper
python3 run.py -s fastapi
```

## Available MCP Tools

The following tools are provided by this MCP server:

## Tools and Specifications

| Tool Name                 | Description                                                                         | Parameters Required                                                                                                                                       |
| ------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Create Draft              | Composes and saves an email to the user's draft folder.                             | to (str), subject (str), body (str), cc (Optional[str]), bcc (Optional[str]), is_html (Optional[bool])                                                    |
| Create Draft Reply        | Composes and saves a reply to an existing email message in the user's draft folder. | message_id (str), body (str), to (Optional[str]), cc (Optional[str]), bcc (Optional[str]), is_html (bool)                                                 |
| Delete Draft              | Deletes a specified Gmail draft with confirmation logic.                            | draft_id (str), confirmation_token (Optional[str])                                                                                                        |
| Get Draft Details         | Retrieves details of a specific draft by its ID.                                    | draft_id (str), prefer_html (Optional[bool])                                                                                                              |
| Get Drafts                | Lists all drafts with optional filters and pagination.                              | query (Optional[str]), label (Optional[str]), max_results (Optional[int]), page_token (Optional[str])                                                     |
| Modify Draft              | Updates the body, subject, and recipients of an existing draft.                     | draft_id (str), to (Optional[str]), subject (Optional[str]), body (Optional[str]), cc (Optional[str]), bcc (Optional[str]), is_html (Optional[bool])      |
| Send Draft                | Sends an existing draft email using Gmail API.                                      | draft_id (str)                                                                                                                                            |
| Add/Remove Star           | Marks multiple Gmail emails as starred or unstarred.                                | message_ids (List[str]), star_email (bool)                                                                                                                |
| Archive Emails            | Archives the specified Gmail emails.                                                | message_ids (List[str])                                                                                                                                   |
| Forward Email             | Forwards a Gmail message to another recipient.                                      | message_id (str), forward_to (str), body (str), cc (Optional[str]), bcc (Optional[str])                                                                   |
| Get Email Details         | Retrieves full details of a specific email by message ID.                           | message_id (str), prefer_html (Optional[bool])                                                                                                            |
| Get Emails                | Fetches a list of emails based on filters (query, labels, folders, etc.).           | query (Optional[str]), label (Optional[str]), folder (Optional[str]), is_unread (Optional[bool]), max_results (Optional[int]), page_token (Optional[str]) |
| Mark Emails Read/Unread   | Marks multiple emails as read or unread.                                            | message_ids (List[str]), mark_as_read (bool)                                                                                                              |
| Mark Emails Spam/Not Spam | Marks multiple Gmail emails as spam or not spam.                                    | message_ids (List[str]), mark_as_spam (bool), new_label (Optional[str])                                                                                   |
| Move Emails               | Moves Gmail emails to a different folder/label.                                     | message_ids (List[str]), new_folder_label (str)                                                                                                           |
| Reply to Email            | Sends a reply to an email with the specified message ID.                            | message_id (str), body (str), cc (Optional[str]), bcc (Optional[str]), is_html (bool)                                                                     |
| Send Email                | Composes and sends an email to the specified recipients.                            | to (str), subject (str), body (str), cc (Optional[str]), bcc (Optional[str]), is_html (bool)                                                              |
| Add/Remove Labels         | Adds or removes Gmail labels from multiple emails.                                  | message_ids (List[str]), labels (List[str]), action (str: 'add' or 'remove')                                                                              |
| Create Label              | Creates a new Gmail label.                                                          | label_name (str)                                                                                                                                          |
| Delete Label              | Deletes a Gmail label with confirmation token logic.                                | label_id (str), confirmation_token (Optional[str])                                                                                                        |
| Get Labels                | Retrieves a list of Gmail labels.                                                   | None                                                                                                                                                      |
| Get Thread Conversation   | Retrieves the full conversation of a thread by ID.                                  | thread_id (str), format (Optional[str] — 'minimal' or 'full', default: 'minimal')                                                                         |
|                           |

\* Make sure you have granted the appropriate scopes for the application to perform the operations.

## How to Create a Google OAuth 2.0 Client ID

1. Go to Google Cloud Console:
   https://console.cloud.google.com/

2. Create or Select a Project:

   - Click on the project dropdown at the top.
   - Select an existing project or click "New Project" to create a new one.

3. Enable Required APIs:

   - Navigate to: APIs & Services > Library
   - Search for and enable the following APIs:
     - Google Drive API
     - Google Docs API
     - Google Sheets API (if needed)

4. Configure OAuth Consent Screen:

   - Go to: APIs & Services > OAuth consent screen
   - Choose "External" for public apps, or "Internal" for private use.
   - Fill in the required fields:
     - App name
     - User support email
     - Developer contact info
   - Add necessary scopes:
     - `https://www.googleapis.com/auth/drive`
     - `https://www.googleapis.com/auth/documents`
     - `https://www.googleapis.com/auth/spreadsheets`
     - `openid`
   - Save and continue

5. Create OAuth 2.0 Credentials:

   - Go to: APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Choose the type based on your application:
     - Web application
     - Desktop app
     - Other
   - For web apps, add authorized redirect URIs (e.g. `https://your-app.com/auth/callback`)
   - Add authorized JavaScript origins if required

6. Save Your Credentials:
   - After creating, Google will show:
     - Client ID
     - Client Secret
   - Store these securely. You’ll need them in your app to authenticate users.

# Screenshots

Server info page:
![Server info page](screenshots/1.png)

Google oAuth page
![Google oAuth page](screenshots/3.png)

Google psermission scopes page
![Google psermission scopes page](screenshots/4.png)

User authenticated page
![User Aunthenticated page](screenshots/5.png)
