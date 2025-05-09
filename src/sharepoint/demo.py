import os
import json

def demo_request():
    from . import get_request_ctx

    subdomain = os.getenv('SUBDOMAIN')
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')

    ctx = get_request_ctx(subdomain, username, password)
    response = ctx.execute_request("web")
    json_r = json.loads(response.content)
    web_title = json_r['d']['Title']
    print("Web title: {0}".format(web_title))


def demo_client():
    from . import get_client_ctx

    subdomain = os.getenv('SUBDOMAIN')
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')

    ctx = get_client_ctx(subdomain, username, password)
    web = ctx.web.get().execute_query()
    print("Web title: {0}".format(web.properties['Title']))