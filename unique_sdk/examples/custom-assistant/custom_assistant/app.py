import json
from http import HTTPStatus
from logging.config import dictConfig
from pprint import pprint

from flask import Flask, jsonify, make_response, request

import unique_sdk
from custom_assistant.external_module_handler import handle_module_message
from custom_assistant.user_event_handler import handle_user_message

unique_sdk.api_key = "YOUR_API_KEY"
unique_sdk.app_id = "YOUR_APP_ID"
endpoint_secret = "YOUR_ENDPOINT_SECRET"
user_id = "USER_ID"
company_id = "COMPANY_ID"

dictConfig(
    {
        "version": 1,
        "root": {"level": "DEBUG", "handlers": ["console"]},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
            }
        },
    }
)

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello! This is an example on how to use the Unique SDK!"


@app.route("/search", methods=["POST"])
def search():
    payload = request.get_json()

    try:
        search = unique_sdk.Search.create(
            user_id,
            company_id,
            chatId=payload.get("chatId"),
            searchString=payload["searchString"],
            searchType=payload["searchType"],
        )

        return jsonify(search)
    except unique_sdk.InvalidRequestError as e:
        message = str(e)
        params = e.params
        return make_response(
            jsonify({"message": message, "params": params}), e.http_status
        )
    except unique_sdk.UniqueError as e:
        return make_response(jsonify(str(e)), e.http_status)
    except Exception as e:
        return jsonify(str(e)), HTTPStatus.INTERNAL_SERVER_ERROR


@app.route("/search/string", methods=["POST"])
def search_string():
    payload = request.get_json()

    try:
        search_string = unique_sdk.SearchString.create(
            user_id,
            company_id,
            prompt=payload["prompt"],
        )

        return jsonify(search_string)
    except unique_sdk.InvalidRequestError as e:
        message = str(e)
        params = e.params
        return make_response(
            jsonify({"message": message, "params": params}), e.http_status
        )
    except unique_sdk.UniqueError as e:
        return make_response(jsonify(str(e)), e.http_status)
    except Exception as e:
        return jsonify(str(e)), HTTPStatus.INTERNAL_SERVER_ERROR


@app.route("/azure-openai/chat/completion", methods=["POST"])
def azure_openai_chat_completion():
    payload = request.get_json()

    try:
        chat_completion = unique_sdk.ChatCompletion.create(
            company_id=company_id,
            model="AZURE_GPT_35_TURBO",
            messages=payload["messages"],
            options={"temperature": 0.5},
        )

        return jsonify(chat_completion)
    except unique_sdk.InvalidRequestError as e:
        message = str(e)
        params = e.params
        return make_response(
            jsonify({"message": message, "params": params}), e.http_status
        )
    except unique_sdk.UniqueError as e:
        return make_response(jsonify(str(e)), e.http_status)
    except Exception as e:
        return jsonify(str(e)), HTTPStatus.INTERNAL_SERVER_ERROR


@app.route("/litellm/chat/completion", methods=["POST"])
def litellm_chat_completion():
    payload = request.get_json()

    try:
        chat_completion = unique_sdk.ChatCompletion.create(
            company_id=company_id,
            model="litellm:anthropic-claude-3-7-sonnet-thinking",
            messages=payload["messages"],
            options={"temperature": 0.5},
        )

        return jsonify(chat_completion)
    except unique_sdk.InvalidRequestError as e:
        message = str(e)
        params = e.params
        return make_response(
            jsonify({"message": message, "params": params}), e.http_status
        )
    except unique_sdk.UniqueError as e:
        return make_response(jsonify(str(e)), e.http_status)
    except Exception as e:
        return jsonify(str(e)), HTTPStatus.INTERNAL_SERVER_ERROR


@app.route("/chat/<chat_id>/messages")
def chat_messages(chat_id: str):
    try:
        messages = unique_sdk.Message.list(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
        )

        return jsonify(messages)
    except unique_sdk.UniqueError as e:
        return make_response(jsonify(str(e)), e.http_status)
    except Exception as e:
        return jsonify(e), HTTPStatus.INTERNAL_SERVER_ERROR


@app.route("/chat/<chat_id>/messages/<message_id>")
def chat_message(chat_id: str, message_id: str):
    message = unique_sdk.Message.retrieve(
        user_id=user_id,
        company_id=company_id,
        id=message_id,
        chatId=chat_id,
    )

    return jsonify(message)


@app.route("/chat/<chat_id>/messages", methods=["POST"])
def create_chat_message(chat_id: str):
    payload = request.get_json()

    message = unique_sdk.Message.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        assistantId=payload["assistantId"],
        text=payload["text"],
        role="ASSISTANT",
    )

    return jsonify(message)


@app.route("/chat/<chat_id>/messages/<message_id>", methods=["PATCH"])
def update_chat_message(chat_id: str, message_id: str):
    payload = request.get_json()

    message = unique_sdk.Message.modify(
        user_id=user_id,
        company_id=company_id,
        id=message_id,
        chatId=chat_id,
        text=payload["text"],
    )

    return jsonify(message)


@app.route("/chat/<chat_id>/messages/<message_id>", methods=["DELETE"])
def delete_chat_message(chat_id: str, message_id: str):
    message = unique_sdk.Message.delete(
        message_id,
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
    )

    return jsonify(message)


@app.route("/webhook", methods=["POST"])
def webhook():
    event = None
    payload = request.data

    app.logger.info("Received webhook request.")

    try:
        event = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        print("⚠️  Webhook error while parsing basic request. " + str(e))
        return jsonify(success=False)

    if endpoint_secret:
        # Only verify the event if there is an endpoint secret defined
        # Otherwise use the basic event deserialized with json
        sig_header = request.headers.get("X-Unique-Signature")
        timestamp = request.headers.get("X-Unique-Created-At")

        if not sig_header or not timestamp:
            print("⚠️  Webhook signature or timestamp headers missing.")
            return jsonify(success=False), HTTPStatus.BAD_REQUEST

        try:
            event = unique_sdk.Webhook.construct_event(
                payload, sig_header, timestamp, endpoint_secret
            )
        except unique_sdk.SignatureVerificationError as e:
            print("⚠️  Webhook signature verification failed. " + str(e))
            return jsonify(success=False), HTTPStatus.BAD_REQUEST

    app.logger.debug("Request headers: %s", request.headers)
    pprint(event)

    if event and event["event"] == "unique.chat.user-message.created":
        print("User message event")
        handle_user_message(event["payload"], event["userId"], event["companyId"])
    elif event and event["event"] == "unique.chat.external-module.chosen":
        print("External module chosen event")
        handle_module_message(event["payload"], event["userId"], event["companyId"])
    else:
        # Unexpected event type
        app.logger.error("Unhandled event type {}".format(event["type"]))

    return jsonify(success=True)
