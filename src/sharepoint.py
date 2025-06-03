import os
import time

import requests
from requests.exceptions import HTTPError

from TokenManager import TokenManager


def get_site_id(token_manager, domain, site_name):
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_name}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['id']


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
            return  # Éxito, salimos de la función

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
    print("Uploading from local path " + local_file_path + " to " + remote_path)
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/content"
    headers = {
        "Authorization": f"Bearer {token_manager.get_token()}",
        "Content-Type": "application/octet-stream"
    }

    with open(local_file_path, 'rb') as f:
        data = f.read()

    response = requests.put(url, headers=headers, data=data)
    response.raise_for_status()
    print(f"✅ Subido: {remote_path}")


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
    for root, dirs, files in os.walk(local_folder_path):
        if len(files) == 0 and len(dirs) == 0:  # Ignore empty folders because they cause issue
            continue

        print("root: " + str(root) + " dirs: " + str(dirs) + " files: " + str(files))
        rel_path = os.path.relpath(root, local_folder_path)
        print("rel path: " + str(rel_path))
        sharepoint_current_path = os.path.normpath(os.path.join(remote_folder_path, rel_path)).replace("\\", "/")
        print("sharepoint current path: " + str(sharepoint_current_path))

        # Subir archivos
        for file_name in files:
            local_file = os.path.join(root, file_name)
            remote_file = f"{sharepoint_current_path}/{file_name}".strip("/")
            print("local file: " + local_file + " remote file: " + remote_file)
            upload_file(token_manager, drive_id, remote_file, local_file)
