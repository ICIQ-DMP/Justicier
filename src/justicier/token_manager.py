# justicier - Automated employee justifications
# Copyright (C) 2026  Aleix Mariné Tena (AleixMT), Carles de la Cuadra
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Microsoft identity token management for Graph API access."""

import time
from typing import Optional

import requests

from .secret import read_secret


class TokenManager:
    """Manages OAuth 2.0 client-credentials tokens with automatic refresh."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scope: str = "https://graph.microsoft.com/.default",
    ) -> None:
        """Initialise the token manager with Azure AD application credentials.

        Args:
            tenant_id: Azure Active Directory tenant identifier.
            client_id: Application (client) identifier.
            client_secret: Application client secret.
            scope: OAuth 2.0 scope string. Defaults to the Graph API default scope.
        """
        self.token_url = (
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        )
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.access_token: Optional[str] = None
        self.expires_at = 0  # Unix timestamp

    def get_token(self) -> str:
        """Return a valid access token, refreshing it if it expires within 5 minutes.

        Returns:
            A valid Bearer token string.
        """
        if (
            self.access_token is None or time.time() >= self.expires_at - 300
        ):  # Refresh if <5min left
            self._refresh_token()
        assert self.access_token is not None
        return self.access_token

    def _refresh_token(self) -> None:
        """Fetch a new access token from the Microsoft identity endpoint."""
        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }
        response = requests.post(self.token_url, data=token_data)
        response.raise_for_status()
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.expires_at = time.time() + token_data["expires_in"]


def _create_token_manager() -> TokenManager:
    """Create a TokenManager by reading credentials from the secret store."""
    tenant_id = read_secret("TENANT_ID")
    client_id = read_secret("CLIENT_ID")
    client_secret = read_secret("CLIENT_SECRET")
    return TokenManager(
        tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
    )


def _create_sharepoint_token_manager(sharepoint_domain: str) -> TokenManager:
    """Create a TokenManager scoped to the SharePoint REST API.

    The SharePoint REST API (``_api/*``) rejects Graph API tokens. This manager
    requests a token against the SharePoint-specific resource so that calls like
    ``ensureUser`` receive a correctly-scoped Bearer token.

    Args:
        sharepoint_domain: The SharePoint tenant domain,
            e.g. ``"contoso.sharepoint.com"``.

    Returns:
        A fresh TokenManager targeting the SharePoint REST API scope.
    """
    tenant_id = read_secret("TENANT_ID")
    client_id = read_secret("CLIENT_ID")
    client_secret = read_secret("CLIENT_SECRET")
    return TokenManager(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        scope=f"https://{sharepoint_domain}/.default",
    )


_token_manager_instance: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Return the shared TokenManager singleton, creating it on first call.

    Returns:
        The application-wide TokenManager instance.
    """
    global _token_manager_instance
    if _token_manager_instance is None:
        _token_manager_instance = _create_token_manager()
    return _token_manager_instance
