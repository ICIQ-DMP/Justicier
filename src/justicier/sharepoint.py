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

"""SharePoint / Microsoft Graph API helpers for file and list operations."""

import os
import time
from pathlib import Path
from typing import cast
from urllib.parse import quote

import requests
from requests.exceptions import HTTPError

from .naf import NAF
from .nif import NIF
from .token_manager import TokenManager, get_token_manager
from .custom_except import BadSharepointListUpdateRequestError
from .defines import SharepointListFields
from .logger import get_logger
from .secret import read_secret
from .custom_except import PersonDoesNotExistInSharepointError

# Type alias for a Microsoft Graph / SharePoint JSON field value
SharepointListFieldType = str | int | bool | None
SharepointItem = dict[SharepointListFields, SharepointListFieldType]

log = get_logger(__name__)


def get_list_id(token_manager: TokenManager, site_id: str, list_name: str) -> str:
    """Return the GUID of the named SharePoint list.

    Args:
        token_manager: Authenticated token manager.
        site_id: SharePoint site identifier.
        list_name: Display name of the target list.

    Returns:
        The list's Graph API GUID string.
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return cast(str, response.json()["id"])


def get_site_id(token_manager: TokenManager, domain: str, site_name: str) -> str:
    """Return the compound site identifier for a SharePoint site.

    Args:
        token_manager: Authenticated token manager.
        domain: SharePoint tenant domain, e.g. ``"contoso.sharepoint.com"``.
        site_name: Name of the SharePoint site.

    Returns:
        The site's compound identifier string.
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_name}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    the_id = cast(str, response.json()["id"])
    return the_id


def get_drive_id(
    token_manager: TokenManager, site_id: str, drive_name: str = "Documents"
) -> str:
    """Return the drive ID of the named document library.

    Args:
        token_manager: Authenticated token manager.
        site_id: SharePoint site identifier.
        drive_name: Display name of the drive/library. Defaults to ``"Documents"``.

    Returns:
        The drive's Graph API identifier string.

    Raises:
        Exception: If no drive with the given name is found.
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    drives = response.json()["value"]
    for drive in drives:
        if drive["name"] == drive_name:
            return cast(str, drive["id"])
    raise Exception(f"Drive '{drive_name}' no encontrado.")


def list_folder_contents(
    token_manager: TokenManager, drive_id: str, path: Path
) -> list[dict[str, str]]:
    """Return the children items of a remote drive folder.

    Args:
        token_manager: Authenticated token manager.
        drive_id: Graph API drive identifier.
        path: Remote folder path relative to the drive root.

    Returns:
        List of Graph API item dictionaries for each child.
    """
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{path}:/children"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return cast(list[dict[str, str]], response.json()["value"])


def download_file(
    token_mananger: TokenManager,
    drive_id: str,
    item_path: Path,
    local_path: Path,
    max_retries: int = 5,
) -> None:
    """Download a single file from the drive, retrying on HTTP 503.

    Args:
        token_mananger: Authenticated token manager.
        drive_id: Graph API drive identifier.
        item_path: Remote file path relative to the drive root.
        local_path: Local destination path (parent dirs are created as needed).
        max_retries: Maximum number of retry attempts on 503 responses.

    Raises:
        RuntimeError: If the file cannot be downloaded after *max_retries* attempts.
        HTTPError: For non-503 HTTP errors.
    """
    url = (
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{item_path}:/content"
    )
    headers = {"Authorization": f"Bearer {token_mananger.get_token()}"}

    retry_count = 0
    backoff = 2  # segundos

    while retry_count <= max_retries:
        response = None
        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            log.trace(f"Downloaded: {item_path}")
            return

        except HTTPError as e:
            if response is None:
                raise e
            if response.status_code == 503:
                retry_count += 1
                wait_time = backoff * retry_count
                log.warning(
                    f"Error 503 in '{item_path}' - retrying in {wait_time}s (attempt {retry_count}/{max_retries})..."
                )
                time.sleep(wait_time)
            else:
                raise e  # If it is not 503, reraise exception immediately

    raise RuntimeError(
        f"Permanent fail when downloading '{item_path}' after {max_retries} attempts."
    )


def download_folder_recursive(
    token_manager: TokenManager, drive_id: str, remote_path: Path, local_root: Path
) -> None:
    """Recursively download all files under *remote_path* to *local_root*.

    Args:
        token_manager: Authenticated token manager.
        drive_id: Graph API drive identifier.
        remote_path: Remote folder path to download from.
        local_root: Local root path where files are mirrored.
    """
    items = list_folder_contents(token_manager, drive_id, remote_path)

    print(items)
    input()
    for item in items:
        name = Path(item["name"])
        item_path = remote_path / name
        local_path = local_root / name

        if "folder" in item:
            download_folder_recursive(token_manager, drive_id, item_path, local_path)
        elif "file" in item:
            download_file(token_manager, drive_id, item_path, local_path)


def download_input_folder(
    token_manager: TokenManager, drive_id: str, remote_path: Path, input_path: Path
) -> None:
    """Download the entire input folder from SharePoint to a local path.

    Args:
        token_manager: Authenticated token manager.
        drive_id: Graph API drive identifier.
        remote_path: Remote folder path to download.
        input_path: Local destination directory.
    """
    log.info("Starting recusive download from SharePoint...")
    download_folder_recursive(token_manager, drive_id, remote_path, input_path)
    log.info("Download completed.")


# Upload functions
def upload_file(
    token_manager: TokenManager, drive_id: str, remote_path: str, local_file_path: Path
) -> None:
    """Upload a local file to the given remote path in the drive.

    Args:
        token_manager: Authenticated token manager.
        drive_id: Graph API drive identifier.
        remote_path: Destination path in the drive (including filename).
        local_file_path: Local file to upload.
    """
    log.info(f"Uploading from local path {local_file_path} to {remote_path}")
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/content"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Content-Type": "application/octet-stream",
    }

    with open(local_file_path, "rb") as f:
        data = f.read()

    response = requests.put(url, headers=headers, data=data)
    response.raise_for_status()
    log.info("✅ Upload Done")


def ensure_remote_folder(
    token_manager: TokenManager, drive_id: str, parent_path: str, folder_name: str
) -> str:
    """Create a folder in the drive (or replace if it exists) and return its path.

    Args:
        token_manager: Authenticated token manager.
        drive_id: Graph API drive identifier.
        parent_path: Remote path of the parent folder.
        folder_name: Name of the folder to create.

    Returns:
        Full remote path of the created folder.
    """
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{parent_path}:/children"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Content-Type": "application/json",
    }
    data = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "replace",
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code not in (200, 201):
        response.raise_for_status()

    return f"{parent_path.rstrip('/')}/{folder_name}"


def upload_folder_recursive(
    token_manager: TokenManager,
    drive_id: str,
    local_folder_path: Path,
    remote_folder_path: str,
) -> None:
    """Recursively upload all files under *local_folder_path* to *remote_folder_path*.

    Args:
        token_manager: Authenticated token manager.
        drive_id: Graph API drive identifier.
        local_folder_path: Root of the local directory tree to upload.
        remote_folder_path: Remote destination path in the drive.
    """
    for root, dirs, files in os.walk(local_folder_path):
        if (
            len(files) == 0 and len(dirs) == 0
        ):  # Ignore empty folders because they cause issue
            continue

        log.debug(f"root: {root} dirs: {dirs} files: {files}")
        rel_path = Path(root).relative_to(local_folder_path)
        log.debug(f"rel path: {rel_path}")
        sharepoint_current_path = (
            remote_folder_path.rstrip("/") + "/" + rel_path.as_posix()
        ).strip("/")
        log.debug(f"sharepoint current path: {sharepoint_current_path}")

        for file_name in files:
            local_file = Path(root) / file_name
            remote_file = f"{sharepoint_current_path}/{file_name}".strip("/")
            upload_file(token_manager, drive_id, remote_file, local_file)


def update_list_item_field(
    item_id: int, updated_fields: dict[str, str]
) -> SharepointItem:
    """Patch one or more fields of a SharePoint list item.

    Args:
        item_id: Numeric identifier of the list item to update.
        updated_fields: Dict mapping internal field names to new values.

    Returns:
        The updated item as a SharepointItem dict.

    Raises:
        BadSharepointListUpdateRequestError: If the PATCH request returns a non-200 status.
    """
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Endpoint to patch the item's fields
    patch_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items/{str(item_id)}/fields"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.patch(patch_url, headers=headers, json=updated_fields)

    if response.status_code != 200:
        raise BadSharepointListUpdateRequestError(
            f"Failed to update item {str(item_id)}: {response.status_code} - {response.text}"
        )
    else:
        log.trace(f"Patched item {str(item_id)} with 200 OK: {response.text}")

    return cast(SharepointItem, response.json())


def resolve_user_to_sharepoint_id(email: str) -> int:
    """Resolve an email address to its SharePoint integer user ID via the User Information List.

    Args:
        email: Microsoft 365 email address of the user to resolve.

    Returns:
        The SharePoint internal integer user ID.

    Raises:
        PersonDoesNotExistInSharepointError: If the user does not exist in Microsoft 365
            or cannot be added to the SharePoint site.
    """
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")

    # Use the Graph API to query the hidden "User Information List" that every
    # SharePoint site maintains. This avoids the SharePoint REST ensureUser endpoint
    # which consistently returns 401 with app-only (client_credentials) tokens even
    # when Sites.FullControl.All is granted.
    token_manager = get_token_manager()
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/User Information List/items"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly",
    }
    params = {
        "$expand": "fields($select=EMail,Id)",
        "$filter": f"fields/EMail eq '{email}'",
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise PersonDoesNotExistInSharepointError(
            f"Could not query User Information List for '{email}': "
            f"Error code: {response.status_code} - {response.text}"
        )

    items = response.json().get("value", [])
    if not items:
        raise PersonDoesNotExistInSharepointError(
            f"User '{email}' not found in SharePoint User Information List. "
            "The user may exist in M365 but has never accessed this site."
        )

    try:
        sp_user_id: int = int(items[0]["fields"]["id"])
    except IndexError as e:
        raise PersonDoesNotExistInSharepointError(
            f"Error parsing the response from Microsoft API, the content was {str(items[0])}"
        ) from e

    log.trace(f"Resolved '{email}' to SharePoint user ID {sp_user_id}")
    return sp_user_id


def get_parameters_from_list(
    sharepoint_domain: str, site_name: str, list_name: str, job_id: int
) -> SharepointItem:
    """Fetch all known fields of a single list item by job ID.

    Args:
        sharepoint_domain: SharePoint tenant domain.
        site_name: Name of the SharePoint site.
        list_name: Name of the target list.
        job_id: Numeric item identifier.

    Returns:
        SharepointItem containing all SharepointListFields values for the item.
    """
    token_manager = get_token_manager()
    access_token = token_manager.get_token()
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Build query in a clearer way: expand fields and select only needed fields
    # Note: requests will correctly encode $ and parentheses in params
    select_fields = ",".join(v.value for v in SharepointListFields)

    params = {
        "$expand": f"fields($select={select_fields})",
        "$select": "fields,createdBy",
    }

    list_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{quote(list_name, safe='')}/items/{job_id}"
    list_resp = requests.get(
        list_url, headers={"Authorization": f"Bearer {access_token}"}, params=params
    )
    list_resp.raise_for_status()

    # The request already targets /items/{job_id}, so raise_for_status() above
    # guarantees we have the right item. No further ID verification is needed.
    fields = list_resp.json()["fields"]
    data: SharepointItem = {
        field: fields.get(field.value) for field in SharepointListFields
    }
    return data


def get_sharepoint_web_url(
    token_manager: TokenManager, site_id: str, drive_id: str, folder_path: str
) -> str:
    """Return the browser-accessible webUrl for a folder inside the drive.

    Args:
        token_manager: Authenticated token manager.
        site_id: SharePoint site identifier.
        drive_id: Graph API drive identifier.
        folder_path: Folder path relative to the drive root,
            e.g. ``"Shared Documents/_output/user@example.com"``.

    Returns:
        The ``webUrl`` string that can be opened in a browser.
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_path}"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    item = response.json()
    return cast(str, item.get("webUrl"))


def _connect_sharepoint() -> tuple[TokenManager, str, str]:
    """Authenticate with SharePoint and return the connection handles.

    Returns:
        Tuple of ``(token_manager, site_id, drive_id)``.
    """
    token_manager = get_token_manager()
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)
    drive_id = get_drive_id(token_manager, site_id, drive_name="Documents")
    return token_manager, site_id, drive_id


def update_list_with_person_ids(request: int, naf: NAF, dni: NIF, email: str) -> None:
    """Update the justification history list with NAF, DNI, and email identifiers.

    Name is intentionally skipped because the A3 name format does not match SharePoint.

    Args:
        request: Numeric list item identifier for the justification request.
        naf: Employee NAF to write.
        dni: Employee NIF/DNI to write.
        email: Employee email address to write.

    Raises:
        PersonDoesNotExistInSharepointError: If the employee no longer exists in SharePoint.
    """
    update_list_item_field(request, {SharepointListFields.NIF.value: str(dni)})
    update_list_item_field(request, {SharepointListFields.NAF.value: str(naf)})
    update_list_item_field(request, {SharepointListFields.TARGET_EMAIL.value: email})

    sp_user_id = resolve_user_to_sharepoint_id(email)
    update_list_item_field(
        request, {SharepointListFields.TARGET_NAME.value + "LookupId": str(sp_user_id)}
    )
