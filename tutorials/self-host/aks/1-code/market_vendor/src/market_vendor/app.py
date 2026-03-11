# ============================================================================
# MOCK FILE - SDK DEPLOYMENT EXAMPLE
# ============================================================================
# This is a mock Flask application for demonstration purposes only.
# It shows how an SDK assistant might be structured using the Unique toolkit.
# This file is NOT production-ready and should be adapted to your specific
# assistant logic and requirements.
# ============================================================================

import logging
import os

from dotenv import load_dotenv
from flask import Flask, request

from market_vendor.utils import get_app_name
from unique_toolkit.app import (
    Event,
    init_logging,
    init_sdk,
)
from unique_toolkit.app.verification import verify_request_and_construct_event
from unique_toolkit.chat import ChatService
from unique_toolkit.language_model import (
    LanguageModelMessages,
    Prompt,
)
from unique_toolkit.language_model.infos import LanguageModelInfo

from .config import MarketVendorConfig

APP_NAME = get_app_name()
init_logging()
logger = logging.getLogger(f"{APP_NAME}.{__name__}")

# On Kubernetes, we can not write onto the containers native filesystem, the env file was decrypted from the Dockerfile and mounted as a volume
# The load_dotenv must load the decrypted file from the volume
env_path = os.environ.get("DECRYPTED_ENV_FILE_ABSOLUTE")
logger.info("DECRYPTED_ENV_FILE_ABSOLUTE: %s", env_path)
if env_path:
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Environment file not found at path: {env_path}")

    if not os.access(env_path, os.R_OK):
        raise PermissionError(f"No read permission for environment file at: {env_path}")

    if os.path.getsize(env_path) == 0:
        raise ValueError(f"Environment file is empty: {env_path}")

    try:
        loaded = load_dotenv(env_path, override=True)
        if not loaded:
            raise EnvironmentError(
                f"Failed to load environment variables from: {env_path}, file may have invalid format"
            )
    except Exception as e:
        raise EnvironmentError(f"Error loading environment file: {str(e)}")

    logger.info(f"API Key starts with: -{os.environ.get('API_KEY', '')[:5]}****-")
    logger.info(
        f"ENDPOINT Secret starts with: -{os.environ.get('ENDPOINT_SECRET', '')[:5]}****-"
    )

init_sdk()

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    logger.info(f"{APP_NAME} - received webhook request")

    event, status_code = verify_request_and_construct_event(
        assistant_name=APP_NAME,
        payload=request.data,
        headers=dict(request.headers),
        event_constructor=Event,
    )

    if isinstance(event, str):
        return event, status_code

    try:
        config = MarketVendorConfig(**event.payload.configuration)

        language_model_info = LanguageModelInfo.from_name(
            model_name=config.language_model_name
        )
        chat_service = ChatService(event=event)
        chat_service.modify_assistant_message(content="Generating response...")

        system_prompt = Prompt(
            """You are a friendly ${product} vendor at a bustling market. You know all about your products, their prices, and can make personalized recommendations based on customer preferences.""",
            product=APP_NAME,
        )
        user_prompt = Prompt(
            "What are your top 3 most popular products today and their prices? Also, what would you recommend for someone looking for something fresh and seasonal?"
        )

        messages = LanguageModelMessages(
            [
                system_prompt.to_system_msg(),
                user_prompt.to_user_msg(),
            ]
        )

        chat_service.stream_complete(
            messages=messages,
            model_name=language_model_info.name,
        )

        chat_service.modify_assistant_message(set_completed_at=True)

    except Exception as e:
        error_message = "Error generating response"
        logger.error(f"{error_message}: {e}")
        chat_service.modify_assistant_message(
            content=error_message, set_completed_at=True
        )
        return error_message, 500

    return "OK", status_code
