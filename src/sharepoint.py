import json
import os
import time
from pathlib import Path
from typing import cast
from urllib.parse import quote

import requests
from requests.exceptions import HTTPError

from TokenManager import TokenManager, get_token_manager
from defines import SharepointListFields
from logger import get_logger
from secret import read_secret

# Type alias for a Microsoft Graph / SharePoint JSON field value
SharepointListFieldType = str | int | bool | None
SharepointItem = dict[SharepointListFields, SharepointListFieldType]

log = get_logger(__name__)


def get_list_id(token_manager: TokenManager, site_id: str, list_name: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return cast(str, response.json()["id"])


def get_site_id(token_manager: TokenManager, domain: str, site_name: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_name}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    the_id = cast(str, response.json()["id"])
    return the_id


def get_drive_id(
    token_manager: TokenManager, site_id: str, drive_name: str = "Documents"
) -> str:
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
    token_manager: TokenManager, drive_id: str, path: str
) -> list[dict[str, str]]:
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{path}:/children"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return cast(list[dict[str, str]], response.json()["value"])


def download_file(
    token_mananger: TokenManager,
    drive_id: str,
    item_path: str,
    local_path: Path,
    max_retries: int = 5,
) -> None:
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
    token_manager: TokenManager, drive_id: str, remote_path: str, local_root: Path
) -> None:
    items = list_folder_contents(token_manager, drive_id, remote_path)
    for item in items:
        name = Path(item["name"])
        item_path = f"{remote_path}/{name}"
        local_path = local_root / name

        if "folder" in item:
            download_folder_recursive(token_manager, drive_id, item_path, local_path)
        elif "file" in item:
            download_file(token_manager, drive_id, item_path, local_path)


def download_input_folder(
    token_manager: TokenManager, drive_id: str, remote_path: str, input_path: Path
) -> None:
    log.info("Starting recusive download from SharePoint...")
    download_folder_recursive(token_manager, drive_id, remote_path, input_path)
    log.info("Download completed.")


# Upload functions
def upload_file(
    token_manager: TokenManager, drive_id: str, remote_path: str, local_file_path: Path
) -> None:

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


def update_resultat_sharepoint_rest(item_id: str, link: str) -> None:
    """
    Updates the 'Resultat' hyperlink field in a SharePoint list item using SharePoint REST API.
    Reads configuration from your secret store.
    """
    # Load secrets
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    # Get token
    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    # Step 1: Get ListItemEntityTypeFullName
    meta_url = f"https://{sharepoint_domain}/sites/{site_name}/_api/web/lists/getbytitle('{list_name}')"
    meta_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json;odata=verbose",
    }

    meta_resp = requests.get(meta_url, headers=meta_headers)
    meta_resp.raise_for_status()
    entity_type = meta_resp.json()["d"]["ListItemEntityTypeFullName"]

    # Step 2: Update the item
    update_url = f"https://{sharepoint_domain}/sites/{site_name}/_api/web/lists/getbytitle('{list_name}')/items({item_id})"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json;odata=verbose",
        "Content-Type": "application/json;odata=verbose",
        "IF-MATCH": "*",
        "X-HTTP-Method": "MERGE",
    }

    payload = {
        "__metadata": {"type": entity_type},
        "Resultats": {
            "__metadata": {"type": "SP.FieldUrlValue"},
            "Url": str(link),
            "Description": "Link a la carpeta de la justificacio",
        },
    }

    response = requests.post(update_url, headers=headers, json=payload)
    response.raise_for_status()
    print("✅ Successfully updated 'Resultat' field via SharePoint REST API.")


def get_result_column(item_id: str) -> None:
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Get list items
    list_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items/{item_id}/fields",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    list_resp.raise_for_status()

    print(list_resp.json())


def print_columns() -> None:
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Get list items
    list_resp = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items?expand=fields,createdBy",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    list_resp.raise_for_status()

    print(list_resp.json())


def get_list_columns() -> list[SharepointItem]:
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/columns"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    columns = response.json().get("value", [])
    for col in columns:
        print(f"🔹 Display Name: {col.get('displayName')}")
        print(f"   Internal Name: {col.get('name')}")
        print(f"   Type: {col.get('columnType')}")
        print(f"   Readonly: {col.get('readOnly')}")
        print(f"   Hidden: {col.get('hidden')}")
        print(f"   Full JSON: {json.dumps(col, indent=2)}")
        print("---")

    return cast(list[SharepointItem], columns)


def update_list_item_field(
    item_id: str, updated_fields: dict[str, str]
) -> SharepointItem:
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Endpoint to patch the item's fields
    patch_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items/{item_id}/fields"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.patch(patch_url, headers=headers, json=updated_fields)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to update item {item_id}: {response.status_code} - {response.text}"
        )

    return cast(SharepointItem, response.json())


def get_parameters_from_list(
    sharepoint_domain: str, site_name: str, list_name: str, job_id: int
) -> SharepointItem:
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
    """
    Given a folder path inside the drive, returns its webUrl for user access.
    Example path: Shared Documents/_output/amarine@iciq.es
    """
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_path}"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    item = response.json()
    return cast(str, item.get("webUrl"))
