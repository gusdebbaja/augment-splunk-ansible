import requests
from requests.auth import HTTPBasicAuth

def get_auth_instance(auth):
    if not auth:
        return None
    if auth['type'] == 'basic':
        return HTTPBasicAuth(auth['username'], auth['password'])
    elif auth['type'] == 'oauth':
        return {"Authorization": f"Bearer {auth['token']}"}
    # Add other auth types if needed
    return None

def make_api_request(url, method, params=None, headers=None, body=None, auth=None, proxy=None):
    method = method.lower()
    auth_instance = get_auth_instance(auth)

    if headers.get('Content-Type') == 'application/json':
        json = body
        data = None
    else:
        data = body
        json = None

    try:
        response = requests.request(method, url, params=params, headers=headers, data=data, json=json, auth=auth_instance, proxies=proxy)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response
    except requests.RequestException as e:
        log_error(f"Request failed: {e}")
        raise e
