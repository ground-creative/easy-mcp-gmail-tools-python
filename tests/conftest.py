import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from app.middleware.google.database import init_db
from core.utils.state import global_state
from core.utils.logger import logger
from core.utils.env import EnvConfig
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from app.utils.credentials import attach_google_services


@pytest.fixture(scope="module")
def auth_setup():
    root_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    init_db("test", f"{root_folder}/storage/sqlite_credentials.db")
    global_state.set("middleware.GoogleAuthMiddleware.is_authenticated", False, True)
    db_handler = global_state.get("db_handler")
    cred = db_handler.get_credentials(EnvConfig.get("TEST_TOKEN"))

    credentials = cred["credentials"]
    try:
        creds = Credentials.from_authorized_user_info(credentials)
    except Exception as e:
        logger.error(f"Error initializing credentials: {str(e)}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("GoogleAuthMiddleware: Refreshing expired credentials.")
            try:
                creds = Credentials(
                    None,
                    refresh_token=creds.refresh_token,
                    client_id=creds.client_id,
                    client_secret=creds.client_secret,
                    token_uri="https://oauth2.googleapis.com/token",
                )
                creds.refresh(GoogleRequest())
                id_info = id_token.verify_oauth2_token(
                    creds.id_token,
                    google_requests.Request(),
                    creds.client_id,
                )
                user_id = id_info["sub"]
                logger.info(
                    f"GoogleAuthMiddleware new access token for user {user_id}: {creds.token}"
                )
                db_handler.update_access_token(user_id, creds.token)

            except Exception as e:
                logger.error(
                    f"GoogleAuthMiddleware error refreshing credentials: {str(e)}",
                    exc_info=True,
                )
                global_state.set(
                    "middleware.GoogleAuthMiddleware.error_message",
                    f"There has been an error with authenticating, please go to {EnvConfig.get('APP_HOST')}/auth/login and authenticate again",
                    True,
                )
                return
        else:
            logger.warning("GoogleAuthMiddleware: Invalid credentials.")
            global_state.set(
                "middleware.GoogleAuthMiddleware.error_message",
                f"There has been an error with authenticating, please deauthenticate the app and go to {EnvConfig.get('APP_HOST')}/auth/login",
                True,
            )
            return

    global_state.set("middleware.GoogleAuthMiddleware.is_authenticated", True, True)
    attach_google_services(creds)
