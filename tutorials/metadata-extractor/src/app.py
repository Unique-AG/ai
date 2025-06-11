import json

from dotenv import load_dotenv
from quart import Quart, request

from src.clients.content import ContentClient
from src.clients.event_socket import EventSocketClient
from src.handler import MetadataExtractorHandler
from src.settings import env_file_path, get_settings
from src.verification import verify_encrypted_env
from unique_toolkit.app import (
    init_sdk,
)

# Create Flask app first
app = Quart(__name__)

# Initialize settings
load_dotenv(env_file_path)
settings = get_settings()
event_socket_client = EventSocketClient()


# Setup logging and environment
def setup_app():
    app.logger.setLevel(settings.log_level)
    verify_encrypted_env()
    init_sdk()


async def process_event(payload_decoded, app_logger):
    """Process an event from either webhook or event socket"""
    event_name = payload_decoded.get("event", "")
    company_id = payload_decoded.get("companyId")
    content_id = payload_decoded.get("payload", {}).get("contentId")
    app.logger.info(f"Received event: {event_name} ")

    if event_name in settings.subscriptions:
        app.logger.info(f"Extracting metadata for content ID: {content_id}")
        metadata_handler = MetadataExtractorHandler(company_id, ContentClient())
        try:
            await metadata_handler.run(content_id)
            return True
        except Exception as e:
            app_logger.error(f"Error in run method: {str(e)}", exc_info=True)
            return False
    return True


async def event_socket():
    async with app.app_context():
        for event in event_socket_client.event_socket():
            if not event or not event.data:
                app.logger.warning("Received an empty message.")
                continue

            try:
                payload_decoded = json.loads(event.data)
            except json.decoder.JSONDecodeError as e:
                app.logger.error(f"Error decoding payload: {e}", exc_info=True)

            await process_event(payload_decoded, app.logger)


# Create a separate initialization function
@app.before_serving
async def on_startup():
    setup_app()
    app.add_background_task(event_socket)
    app.logger.info("Event socket listener added as background task")


@app.route("/webhook", methods=["POST"])
async def webhook():
    app.logger.info("metadata-extractor - received webhook request")

    try:
        payload_decoded = json.loads(await request.data)
    except json.decoder.JSONDecodeError as e:
        app.logger.error(f"Error decoding payload: {e}", exc_info=True)
        return "Invalid payload", 400

    success = process_event(payload_decoded, app.logger)

    if not success:
        return "Error", 500

    return "OK", 200
