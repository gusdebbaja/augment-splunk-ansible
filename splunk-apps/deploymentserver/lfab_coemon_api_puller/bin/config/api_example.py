# API-specific variables
API_URL = 'https://api1.example.com/endpoint'
METHOD = 'POST'
PARAMS = {'key': 'value'}
HEADERS = {
    'Content-Type': 'application/xml',  # Changed to XML
    'Accept': 'application/xml'
}
BODY = '<root><data>example</data></root>'  # Default XML body
PROXY = None

# API-specific credentials
AUTH = {
    'type': 'basic',
    'username': 'your_username',
    'password': 'your_password'
}

# API-specific pre-processing
def preprocess_body(body):
    # Add API-specific pre-processing logic here
    # For example, you might want to add a timestamp to the XML
    from xml.etree import ElementTree as ET
    from datetime import datetime

    root = ET.fromstring(body)
    timestamp = ET.SubElement(root, 'timestamp')
    timestamp.text = datetime.now().isoformat()
    return ET.tostring(root, encoding='unicode')

# API-specific post-processing
def postprocess_response(response):
    # Add API-specific post-processing logic here
    # For example, you might want to extract certain data from the XML response
    from xml.etree import ElementTree as ET

    if response.headers.get('Content-Type') == 'application/xml':
        root = ET.fromstring(response.text)
        # Extract specific data from the XML
        # For example:
        # status = root.find('status').text
        # return {'status': status}
    return response.text

