import time

import requests


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
