# ============================================================================
# MOCK FILE - SDK DEPLOYMENT EXAMPLE
# ============================================================================
# This is a mock utilities file for demonstration purposes only.
# This file is NOT production-ready and should be adapted to your specific
# utility requirements.
# ============================================================================

import os


def get_app_name() -> str:
    app_name = os.getenv("APP_NAME")
    assert app_name is not None, "APP_NAME is not set"
    return app_name
