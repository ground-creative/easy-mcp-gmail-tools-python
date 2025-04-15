from core.utils.logger import logger
from core.utils.state import global_state  # Import global state
from core.utils.env import EnvConfig
from cryptography.fernet import Fernet
from googleapiclient.discovery import build


def decode_access_token(access_token: str):
    """Decode the access token to retrieve the original user ID."""
    # Retrieve the encryption key from environment variables
    encryption_key = EnvConfig.get("CYPHER").encode()  # Ensure it's in bytes

    # Create a Fernet instance with the encryption key
    fernet = Fernet(encryption_key)

    try:
        # Decrypt the access token
        decrypted_user_id = fernet.decrypt(access_token.encode()).decode()
        return decrypted_user_id  # Return the original user ID
    except Exception as e:
        # Handle decryption errors
        logger.error(f"Failed to decode access token: {str(e)}")
        return None  # Return None or handle as needed


def credentials_to_json(credentials):
    """Convert credentials to a JSON serializable format."""
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }


def attach_google_services(credentials):
    """Attach Google API services to the global state."""
    gmail_service = build("gmail", "v1", credentials=credentials)

    global_state.set("google_oauth_credentials", credentials, True)

    global_state.set(
        "google_gmail_service", gmail_service, True
    )  # Save Gmail service to global state
