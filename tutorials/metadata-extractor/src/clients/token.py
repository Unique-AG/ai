import base64

import httpx
from src.settings import get_settings


class TokenClient:
    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.client_id
        self.client_secret = self.settings.client_secret
        self.project_id = self.settings.project_id
        self.url = self.settings.token_url
        self.env = self.settings.env
        self.user_token = self.settings.user_token

    async def get_access_token(self):
        if self.env == "local":
            if not self.user_token:
                raise ValueError("User token is not set for local environment")
            return self.user_token

        # Encode the client ID and client secret using base64
        basic_auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        # Define the URL and headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_auth}",
        }

        # Define the data payload
        data = {
            "grant_type": "client_credentials",
            "scope": "openid profile email urn:zitadel:iam:user:resourceowner "
            "urn:zitadel:iam:org:projects:roles "
            f"urn:zitadel:iam:org:project:id:{self.project_id}:aud",
        }

        # Make the POST request
        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, headers=headers, data=data)

        # Check if the request was successful
        if response.status_code == 200:
            response = response.json()
            token = response.get("access_token")
            return token
        else:
            return None
