import time

import requests

from secret import read_secret


class TokenManager:
    def __init__(self, tenant_id, client_id, client_secret, scope="https://graph.microsoft.com/.default"):
        self.token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.access_token = None
        self.expires_at = 0  # Unix timestamp

    def get_token(self):
        if self.access_token is None or time.time() >= self.expires_at - 300:  # Refresh if <5min left
            self._refresh_token()
        return self.access_token

    def _refresh_token(self):
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default',
        }
        response = requests.post(self.token_url, data=token_data)
        response.raise_for_status()
        token_data = response.json()
        self.access_token = token_data['access_token']
        self.expires_at = time.time() + token_data['expires_in']


def _create_token_manager():
    tenant_id = read_secret('TENANT_ID')
    client_id = read_secret('CLIENT_ID')
    client_secret = read_secret('CLIENT_SECRET')
    return TokenManager(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)


def get_token_manager():
    if not hasattr(get_token_manager, "_instance"):
        # create and store the singleton instance the first time
        get_token_manager._instance = _create_token_manager()
    return get_token_manager._instance
