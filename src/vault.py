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

import os
from typing import cast

import requests
import urllib3
from pathlib import Path

from logger import get_logger

_VAULT_BASE_PATH = "secret/data/justicier/runtime"

# Maps app-level secret names to (vault subpath, vault field key)
_SECRET_MAP = {
    # sharepoint
    "CLIENT_ID": ("sharepoint", "client_id"),
    "CLIENT_NAME": ("sharepoint", "client_name"),
    "CLIENT_SECRET": ("sharepoint", "client_secret"),
    "OBJECT_ID": ("sharepoint", "object_id"),
    "SHAREPOINT_DOMAIN": ("sharepoint", "domain"),
    "DRIVE_ID": ("sharepoint", "drive_id"),
    "SHAREPOINT_FOLDER": ("sharepoint", "folder"),
    "SHAREPOINT_FOLDER_INPUT": ("sharepoint", "folder_input"),
    "SHAREPOINT_FOLDER_OUTPUT": ("sharepoint", "folder_output"),
    "SHAREPOINT_LIST_GUID": ("sharepoint", "list_guid"),
    "SHAREPOINT_LIST_NAME": ("sharepoint", "list_name"),
    "SITE_NAME": ("sharepoint", "site_name"),
    "TENANT_ID": ("sharepoint", "tenant_id"),
    # smtp
    "SMTP_PASSWORD": ("smtp", "password"),
    "SMTP_PORT": ("smtp", "port"),
    "SMTP_SERVER": ("smtp", "server"),
    "SMTP_USERNAME": ("smtp", "username"),
}


_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

log = get_logger(__name__)


def _read_credential(name: str) -> str:
    """Read a credential from (in order):
    1. /run/secrets/<name>
    2. <project_root>/secrets/<name>
    3. environment variable
    """
    for path in (Path("/run/secrets") / name, _PROJECT_ROOT / "secrets" / name):
        if path.is_file():
            with open(path) as f:
                value = f.read().strip()
            if value:
                return value
    value = os.environ.get(name, "").strip()
    log.debug(f"Read secret from {name}")
    if value:
        return value
    raise KeyError(f"Vault credential '{name}' not found in secrets or environment")


class _VaultClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._cache: dict[str, dict[str, str]] = {}  # subpath -> {field: value}

        self._session = requests.Session()
        ca_cert = _read_credential("VAULT_CACERT").strip()
        if ca_cert:
            self._session.verify = ca_cert
        elif _read_credential("VAULT_SKIP_VERIFY").lower() in ("1", "true", "yes"):
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self._session.verify = False
        # If neither is set, requests will use its default CA bundle.

    def _authenticate(self) -> None:
        # 1. Try a pre-issued Vault token.
        try:
            self._token = _read_credential("VAULT_TOKEN")
            return
        except KeyError:
            pass

        # 2. Try AppRole (VAULT_ROLE_ID + VAULT_SECRET_ID).
        role_id = _read_credential("VAULT_ROLE_ID")
        secret_id = _read_credential("VAULT_SECRET_ID")
        vault_addr = _read_credential("VAULT_ADDR")
        resp = self._session.post(
            f"{vault_addr}/v1/auth/approle/login",
            json={"role_id": role_id, "secret_id": secret_id},
            timeout=10,
        )
        resp.raise_for_status()
        self._token = cast(str, resp.json()["auth"]["client_token"])

    def _fetch_subpath(self, subpath: str) -> dict[str, str]:
        if subpath in self._cache:
            return self._cache[subpath]

        if self._token is None:
            self._authenticate()

        assert self._token is not None
        vault_addr = _read_credential("VAULT_ADDR")
        url = f"{vault_addr}/v1/{_VAULT_BASE_PATH}/{subpath}"
        resp = self._session.get(
            url,
            headers={"X-Vault-Token": self._token},
            timeout=10,
        )
        resp.raise_for_status()
        data = cast(dict[str, str], resp.json()["data"]["data"])
        self._cache[subpath] = data
        return data

    def read_secret(self, secret_name: str) -> str:
        if secret_name not in _SECRET_MAP:
            raise KeyError(f"No vault mapping defined for secret '{secret_name}'")
        subpath, field = _SECRET_MAP[secret_name]
        data = self._fetch_subpath(subpath)
        if field not in data:
            raise KeyError(
                f"Field '{field}' not found at vault path '{_VAULT_BASE_PATH}/{subpath}'"
            )
        value = data[field]
        if value is None or str(value).strip() == "":
            raise ValueError(f"Vault secret '{secret_name}' (field '{field}') is empty")
        return str(value)


_client = None


def read_vault_secret(secret_name: str) -> str:
    """Return the value of *secret_name* fetched from Vault.

    Raises KeyError  if the secret has no vault mapping or the field is absent.
    Raises ValueError if the field exists but is empty.
    Raises requests.HTTPError / ConnectionError on network / auth failures.
    """
    log.trace(f"requested secret from vault: {secret_name}")
    global _client
    if _client is None:
        _client = _VaultClient()
    return _client.read_secret(secret_name)
