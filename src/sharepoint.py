import json
import logging
import os
import time

import requests
from requests.exceptions import HTTPError

from TokenManager import TokenManager, get_token_manager
from logger import build_process_logger
from secret import read_secret


def get_list_id(token_manager, site_id, list_name):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["id"]


def get_site_id(token_manager, domain, site_name):
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_name}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    the_id = response.json()['id']
    return the_id


def get_drive_id(token_manager, site_id, drive_name="Documents"):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    drives = response.json()['value']
    for drive in drives:
        if drive['name'] == drive_name:
            return drive['id']
    raise Exception(f"Drive '{drive_name}' no encontrado.")


def list_folder_contents(token_manager, drive_id, path):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{path}:/children"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['value']


def download_file(token_mananger, drive_id, item_path, local_path, max_retries=5):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{item_path}:/content"
    headers = {"Authorization": f"Bearer {token_mananger.get_token()}"}

    retry_count = 0
    backoff = 2  # segundos

    while retry_count <= max_retries:
        response = None
        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"✅ Descargado: {item_path}")
            return

        except HTTPError as e:
            if response is None:
                raise e
            if response.status_code == 503:
                retry_count += 1
                wait_time = backoff * retry_count
                print(
                    f"⚠️ Error 503 en '{item_path}' - Reintentando en {wait_time}s (intento {retry_count}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e  # Si no es 503, relanzamos la excepción inmediatamente

    raise RuntimeError(f"❌ Fallo permanente al descargar '{item_path}' tras {max_retries} reintentos.")


def download_folder_recursive(token_manager: TokenManager, drive_id, remote_path, local_root):
    items = list_folder_contents(token_manager, drive_id, remote_path)
    for item in items:
        name = item['name']
        item_path = f"{remote_path}/{name}"
        local_path = os.path.join(local_root, name)

        if 'folder' in item:
            download_folder_recursive(token_manager, drive_id, item_path, local_path)
        elif 'file' in item:
            download_file(token_manager, drive_id, item_path, local_path)


def download_input_folder(token_manager, drive_id, remote_path, input_path):
    print("Comenzando descarga recursiva de SharePoint...")
    download_folder_recursive(token_manager, drive_id, remote_path, input_path)
    print("✅ Descarga completada.")


# Upload functions
def upload_file(token_manager, drive_id, remote_path, local_file_path):
    logger_instance = logging.getLogger("justicier")
    logger = build_process_logger(logger_instance, "upload_file")

    logger.info("Uploading from local path " + local_file_path + " to " + remote_path)
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/content"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Content-Type": "application/octet-stream"
    }

    with open(local_file_path, 'rb') as f:
        data = f.read()

    response = requests.put(url, headers=headers, data=data)
    response.raise_for_status()
    logger.info(f"✅ Upload Done")


def ensure_remote_folder(token_manager, drive_id, parent_path, folder_name):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{parent_path}:/children"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Content-Type": "application/json"
    }
    data = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "replace"
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code not in (200, 201):
        response.raise_for_status()

    return os.path.join(parent_path, folder_name).replace("\\", "/")


def upload_folder_recursive(token_manager, drive_id, local_folder_path, remote_folder_path):
    logger_instance = logging.getLogger("justicier")
    logger = build_process_logger(logger_instance, "Upload data results")

    for root, dirs, files in os.walk(local_folder_path):
        if len(files) == 0 and len(dirs) == 0:  # Ignore empty folders because they cause issue
            continue

        logger.debug("root: " + str(root) + " dirs: " + str(dirs) + " files: " + str(files))
        rel_path = os.path.relpath(root, local_folder_path)
        logger.debug("rel path: " + str(rel_path))
        sharepoint_current_path = os.path.normpath(os.path.join(remote_folder_path, rel_path)).replace("\\", "/")
        logger.debug("sharepoint current path: " + str(sharepoint_current_path))

        # Subir archivos
        for file_name in files:
            local_file = os.path.join(root, file_name)
            remote_file = f"{sharepoint_current_path}/{file_name}".strip("/")
            upload_file(token_manager, drive_id, remote_file, local_file)


def update_resultat_sharepoint_rest(item_id, link):
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
        "Accept": "application/json;odata=verbose"
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
        "X-HTTP-Method": "MERGE"
    }

    payload = {
        "__metadata": { "type": entity_type },
        "Resultats": {
            "__metadata": { "type": "SP.FieldUrlValue" },
            "Url": str(link),
            "Description": "Link a la carpeta de la justificacio"
        }
    }

    response = requests.post(update_url, headers=headers, json=payload)
    response.raise_for_status()
    print("✅ Successfully updated 'Resultat' field via SharePoint REST API.")


def get_result_column(item_id):
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Get list items
    list_resp = requests.get(
    f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items/{item_id}/fields",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    list_resp.raise_for_status()

    print(list_resp.json())


def print_columns():
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Get list items
    list_resp = requests.get(
    f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items?expand=fields,createdBy",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    list_resp.raise_for_status()

    print(list_resp.json())


def get_list_columns():
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    token_manager = get_token_manager()
    access_token = token_manager.get_token()
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/columns"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

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

    return columns


def update_list_item_field(item_id, updated_fields: dict):
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
        "Content-Type": "application/json"
    }

    response = requests.patch(
        patch_url,
        headers=headers,
        json=updated_fields
    )

    if response.status_code != 200:
        raise RuntimeError(f"Failed to update item {item_id}: {response.status_code} - {response.text}")

    return response.json()


def get_parameters_from_list(sharepoint_domain, site_name, list_name, job_id):
    token_manager = get_token_manager()
    access_token = token_manager.get_token()

    site_id = get_site_id(token_manager, sharepoint_domain, site_name)

    # Get list items
    list_resp = requests.get(
    f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items/{job_id}?expand=fields($select="
        f"Title,Nomdelapersona,Fusi_x00f3_NominaiJustificantBan,Tipusdidentificador,NAF,DNI,DataInici,"
        f"Datafinal,juntarpdfs,Fusi_x00f3_RLCRNT,Sol_x00b7_licitant,id),createdBy",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    list_resp.raise_for_status()

    # Search for the job ID
    if str(list_resp.json()["fields"].get("id")) == str(job_id):
        data = {
            'Title': list_resp.json()["fields"].get('Title'),
            'id_type': list_resp.json()["fields"].get('Tipusdidentificador'),
            'NAF': list_resp.json()["fields"].get('NAF'),
            'name': list_resp.json()["fields"].get('Nomdelapersona'),
            'DNI': list_resp.json()["fields"].get('DNI'),
            'begin': list_resp.json()["fields"].get('DataInici'),
            'end': list_resp.json()["fields"].get('Datafinal'),
            'author': list_resp.json()["fields"].get('user').get('email'),
            'merge_salary_bankproof': list_resp.json()["fields"].get('Fusi_x00f3_NominaiJustificantBan'),
            'merge_results': list_resp.json()["fields"].get('juntarpdfs'),
            'merge_RLC_RNT': list_resp.json()["fields"].get('Fusi_x00f3_RLCRNT')
        }

        return data

    raise ValueError(f"Job ID {job_id} not found in SharePoint List")


def get_sharepoint_web_url(token_manager, site_id, drive_id, folder_path):
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
    return item.get("webUrl")


