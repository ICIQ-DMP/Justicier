from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.request import SharePointRequest


def get_client_ctx(subdomain: str, username: str, password: str):
    """
    Not working in ICIQ Sharepoint
    """
    site_url = "https://" + subdomain + ".sharepoint.com"

    print("username" + username + " pass " + password)
    return ClientContext(site_url).with_credentials(UserCredential(username, password))


def get_request_ctx(subdomain: str, username: str, password: str):
    """
    Not working in ICIQ Sharepoint
    """
    site_url = "https://" + subdomain + ".sharepoint.com"
    return SharePointRequest(site_url).with_credentials(UserCredential(username, password))

