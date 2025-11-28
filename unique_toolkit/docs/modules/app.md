# App Module

The App module provides functions for initializing and securing apps that interact with the Unique platform.

## Overview

The `unique_toolkit.app` module encompasses functions for:
- Initializing the SDK and logging
- Handling events from the platform
- Verifying webhook signatures
- Building FastAPI applications
- Running async tasks in parallel

## Components

### Settings
::: unique_toolkit.app.unique_settings.UniqueSettings

### Initialization
::: unique_toolkit.app.init_sdk.init_sdk
::: unique_toolkit.app.init_sdk.init_unique_sdk
::: unique_toolkit.app.init_logging.init_logging

### Event Schemas
::: unique_toolkit.app.schemas.ChatEvent
::: unique_toolkit.app.schemas.Event
::: unique_toolkit.app.schemas.BaseEvent
::: unique_toolkit.app.schemas.EventName

### Verification
::: unique_toolkit.app.verification.verify_signature_and_construct_event
::: unique_toolkit.app.webhook.is_webhook_signature_valid

### FastAPI Factory
::: unique_toolkit.app.fast_api_factory.build_unique_custom_app

