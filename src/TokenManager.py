import time
from typing import Optional

import requests

from secret import read_secret


class TokenManager:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scope: str = "https://graph.microsoft.com/.default",
    ) -> None:
        self.token_url = (
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        )
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.access_token: Optional[str] = None
        self.expires_at = 0  # Unix timestamp

    def get_token(self) -> str:
        if (
            self.access_token is None or time.time() >= self.expires_at - 300
        ):  # Refresh if <5min left
            self._refresh_token()
        assert self.access_token is not None
        return self.access_token

    def _refresh_token(self) -> None:
        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        response = requests.post(self.token_url, data=token_data)
        response.raise_for_status()
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.expires_at = time.time() + token_data["expires_in"]


def _create_token_manager() -> TokenManager:
    tenant_id = read_secret("TENANT_ID")
    client_id = read_secret("CLIENT_ID")
    client_secret = read_secret("CLIENT_SECRET")
    return TokenManager(
        tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
    )


_token_manager_instance: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    global _token_manager_instance
    if _token_manager_instance is None:
        _token_manager_instance = _create_token_manager()
    return _token_manager_instance
