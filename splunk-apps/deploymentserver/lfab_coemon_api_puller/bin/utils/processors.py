"""
Custom processors for API requests and responses.

This module provides three types of processors:
1. Preprocessors: Modify API requests before they're sent
2. Postprocessors: Transform API responses after they're received
3. Output processors: Control how processed data is saved or output
"""
import json
import logging
import os
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

# =====================
# PREPROCESSORS
# =====================

def preprocess_update_time_range(api_config: Dict, **kwargs) -> Dict:
    """
    Update time range parameters in the request body.
    
    Args:
        api_config: API configuration
        time_range_hours: Hours to look back (default: 24)
        
    Returns:
        Dict: Updated API configuration
    """
    try:
        # Make a copy of the API config to avoid modifying the original
        updated_config = api_config.copy()
        if 'body' not in updated_config:
            updated_config['body'] = {}
        
        # Calculate time range
        time_range_hours = kwargs.get('time_range_hours', 24)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # Format times as ISO strings
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()
        
        # Update request body with time range
        body = updated_config['body']
        if isinstance(body, dict):
            # Replace placeholders in any string value
            for key, value in body.items():
                if isinstance(value, str):
                    body[key] = value.replace('{start_time}', start_time_str).replace('{end_time}', end_time_str)
        elif isinstance(body, str):
            # Replace placeholders in the entire body string
            updated_config['body'] = body.replace('{start_time}', start_time_str).replace('{end_time}', end_time_str)
        
        logging.info(f"Updated time range: {start_time_str} to {end_time_str}")
        return updated_config
        
    except Exception as e:
        logging.error(f"Error updating time range: {str(e)}")
        return api_config

def preprocess_add_headers(api_config: Dict, **kwargs) -> Dict:
    """
    Add custom headers to the API request.
    
    Args:
        api_config: API configuration
        headers: Dictionary of headers to add
        
    Returns:
        Dict: Updated API configuration
    """
    try:
        # Make a copy of the API config to avoid modifying the original
        updated_config = api_config.copy()
        if 'headers' not in updated_config:
            updated_config['headers'] = {}
        
        # Add custom headers
        headers = kwargs.get('headers', {})
        updated_config['headers'].update(headers)
        
        logging.info(f"Added custom headers: {list(headers.keys())}")
        return updated_config
        
    except Exception as e:
        logging.error(f"Error adding headers: {str(e)}")
        return api_config

def preprocess_template_url(api_config: Dict, **kwargs) -> Dict:
    """
    Apply variable substitution in URL using template values.
    
    Args:
        api_config: API configuration
        variables: Dictionary of variables for substitution
        
    Returns:
        Dict: Updated API configuration
    """
    try:
        # Make a copy of the API config to avoid modifying the original
        updated_config = api_config.copy()
        if 'url' not in updated_config:
            return updated_config
        
        # Replace variables in URL
        variables = kwargs.get('variables', {})
        url = updated_config['url']
        
        for var_name, var_value in variables.items():
            placeholder = '{' + var_name + '}'
            if placeholder in url:
                url = url.replace(placeholder, str(var_value))
        
        updated_config['url'] = url
        logging.info(f"URL after template substitution: {url}")
        return updated_config
        
    except Exception as e:
        logging.error(f"Error applying URL template: {str(e)}")
        return api_config

def preprocess_pagination_params(api_config: Dict, **kwargs) -> Dict:
    """
    Add pagination parameters to the API request.
    
    Args:
        api_config: API configuration
        page_param: Name of the page parameter (default: "page")
        size_param: Name of the page size parameter (default: "size")
        page: Page number (default: 1)
        size: Page size (default: 100)
        
    Returns:
        Dict: Updated API configuration
    """
    try:
        # Make a copy of the API config to avoid modifying the original
        updated_config = api_config.copy()
        if 'params' not in updated_config:
            updated_config['params'] = {}
        
        # Get pagination parameters
        page_param = kwargs.get('page_param', 'page')
        size_param = kwargs.get('size_param', 'size')
        page = kwargs.get('page', 1)
        size = kwargs.get('size', 100)
        
        # Add pagination parameters
        updated_config['params'][page_param] = page
        updated_config['params'][size_param] = size
        
        logging.info(f"Added pagination parameters: {page_param}={page}, {size_param}={size}")
        return updated_config
        
    except Exception as e:
        logging.error(f"Error adding pagination parameters: {str(e)}")
        return api_config

# =====================
# POSTPROCESSORS
# =====================

def postprocess_filter_response(response, **kwargs) -> Dict:
    """
    Filter response to include only specified fields.
    
    Args:
        response: API response object
        fields: List of fields to keep
        
    Returns:
        Dict: Filtered response data
    """
    try:
        # Parse the JSON response
        data = response.json()
        
        # Get the list of fields to keep
        fields = kwargs.get('fields', [])
        if not fields:
            logging.warning("No fields specified for filter_response processor")
            return data
        
        # Filter the response
        if isinstance(data, dict):
            filtered_data = {k: v for k, v in data.items() if k in fields}
            logging.info(f"Filtered response to {len(filtered_data)} fields")
            return filtered_data
        elif isinstance(data, list):
            filtered_data = []
            for item in data:
                if isinstance(item, dict):
                    filtered_item = {k: v for k, v in item.items() if k in fields}
                    filtered_data.append(filtered_item)
                else:
                    filtered_data.append(item)
            logging.info(f"Filtered {len(data)} list items")
            return filtered_data
        else:
            logging.warning("Response data is not a dict or list, cannot filter")
            return data
        
    except Exception as e:
        logging.error(f"Error filtering response: {str(e)}")
        return None

def postprocess_flatten_json(response, **kwargs) -> Dict:
    """
    Flatten JSON response to a single line for easier log ingestion.
    
    Args:
        response: API response object
        add_metadata: Whether to add metadata to the response
        
    Returns:
        Dict: Special format for output handler
    """
    try:
        # Parse the JSON response
        data = response.json()
        
        # Add optional metadata if requested
        if kwargs.get("add_metadata", False):
            if isinstance(data, dict):
                data["_metadata"] = {
                    "endpoint": response.url,
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Convert back to JSON string without pretty-printing (no indent)
        flat_json = json.dumps(data, separators=(',', ':'))
        
        # Special handling to indicate this is a string output
        return {"__flatten_json_output": flat_json}
        
    except Exception as e:
        logging.error(f"Error flattening JSON response: {str(e)}")
        return None

def postprocess_split_json_array(response, **kwargs) -> Dict:
    """
    Split a JSON array into individual objects, one per line.
    
    Args:
        response: API response object
        array_path: JSON path to the array (e.g., "conversations" or "data.items")
        add_metadata: Whether to add metadata to each item
        parent_fields: Fields from parent object to include in each item
        
    Returns:
        Dict: Special format for output handler
    """
    try:
        # Get the JSON response
        data = response.json()
        
        # Get the array path from kwargs
        array_path = kwargs.get("array_path", None)
        if not array_path:
            logging.error("No array_path specified for split_json_array processor")
            return None
        
        # Navigate to the specified array
        array_data = data
        path_parts = array_path.split('.')
        for part in path_parts:
            if part in array_data:
                array_data = array_data[part]
            else:
                logging.error(f"Path {array_path} not found in response")
                return None
        
        # Ensure we have an array
        if not isinstance(array_data, list):
            logging.error(f"Path {array_path} does not point to an array")
            return None
        
        # Add metadata to each item if requested
        if kwargs.get("add_metadata", False):
            parent_info = {}
            # Add any parent fields specified in parent_fields
            parent_fields = kwargs.get("parent_fields", [])
            for field in parent_fields:
                if isinstance(data, dict) and field in data:
                    parent_info[field] = data[field]
                    
            # Add parent info and timestamp to each item
            for item in array_data:
                if isinstance(item, dict):
                    item["_parent"] = parent_info
                    item["_timestamp"] = datetime.now().isoformat()
        
        # Convert each array item to a single-line JSON string
        json_lines = [json.dumps(item, separators=(',', ':')) for item in array_data]
        
        # Return special format to indicate this is an array split output
        return {"__split_json_output": json_lines}
        
    except Exception as e:
        logging.error(f"Error splitting JSON array: {str(e)}")
        return None

def postprocess_transform_keys(response, **kwargs) -> Dict:
    """
    Transform keys in a JSON response (e.g., to make them Splunk-friendly).
    
    Args:
        response: API response object
        replacements: Dictionary of key replacements
        case: Transform case ('lower', 'upper', 'snake', or None)
        
    Returns:
        Dict: Transformed response data
    """
    try:
        # Parse the JSON response
        data = response.json()
        
        # Get replacements and case transformation
        replacements = kwargs.get('replacements', {})
        case = kwargs.get('case', None)
        
        # Helper function to transform a single key
        def transform_key(key):
            # First apply any direct replacements
            if key in replacements:
                key = replacements[key]
            
            # Then apply case transformation
            if case == 'lower':
                return key.lower()
            elif case == 'upper':
                return key.upper()
            elif case == 'snake':
                # Convert camelCase or PascalCase to snake_case
                import re
                s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
                return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
            else:
                return key
        
        # Helper function to recursively transform keys in a dictionary
        def transform_dict(d):
            if not isinstance(d, dict):
                return d
            
            result = {}
            for k, v in d.items():
                new_key = transform_key(k)
                if isinstance(v, dict):
                    result[new_key] = transform_dict(v)
                elif isinstance(v, list):
                    result[new_key] = [transform_dict(item) if isinstance(item, dict) else item for item in v]
                else:
                    result[new_key] = v
            return result
        
        # Transform the data
        if isinstance(data, dict):
            result = transform_dict(data)
            logging.info("Transformed keys in response dictionary")
            return result
        elif isinstance(data, list):
            result = [transform_dict(item) if isinstance(item, dict) else item for item in data]
            logging.info(f"Transformed keys in {len(result)} list items")
            return result
        else:
            logging.warning("Response data is not a dict or list, cannot transform keys")
            return data
        
    except Exception as e:
        logging.error(f"Error transforming keys: {str(e)}")
        return None

def postprocess_extract_nested(response, **kwargs) -> Any:
    """
    Extract a nested value from a complex API response.
    
    Args:
        response: API response object
        path: List or dot-notation string path to the nested value
        default: Default value if path not found
        
    Returns:
        Any: Extracted value
    """
    try:
        # Parse the JSON response
        data = response.json()
        
        # Get the path to the nested value
        path = kwargs.get('path', [])
        default = kwargs.get('default', None)
        
        # Convert string path to list if needed
        if isinstance(path, str):
            path = path.split('.')
        
        # Navigate to the value
        value = data
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list) and key.isdigit():
                index = int(key)
                if 0 <= index < len(value):
                    value = value[index]
                else:
                    logging.warning(f"Index {index} out of range in path {path}")
                    return default
            else:
                logging.warning(f"Path {path} not found in response")
                return default
        
        logging.info(f"Extracted value at path {path}")
        return value
        
    except Exception as e:
        logging.error(f"Error extracting nested value: {str(e)}")
        return None

# =====================
# OUTPUT PROCESSORS
# =====================

def output_csv_file(data, endpoint, **kwargs) -> bool:
    """
    Save API response as CSV file.
    
    Args:
        data: API response data (processed)
        endpoint: API endpoint URL
        filename: Custom filename (default: based on endpoint)
        fields: List of fields to include (default: all)
        headers: Whether to include headers (default: True)
        directory: Output directory (default: logs directory)
        
    Returns:
        bool: Success flag
    """
    try:
        # Create output directory if it doesn't exist
        directory = kwargs.get('directory')
        if directory is None:
            directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(directory, exist_ok=True)
        
        # Determine filename
        custom_filename = kwargs.get('filename')
        if custom_filename:
            filename = custom_filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            endpoint_name = endpoint.split('/')[-1].replace('?', '_').replace('&', '_')
            filename = f"{endpoint_name}_{timestamp}.csv"
        
        file_path = os.path.join(directory, filename)
        
        # Prepare data for CSV
        if isinstance(data, dict):
            rows = [data]
        elif isinstance(data, list):
            rows = data
        else:
            logging.error(f"Cannot convert data type {type(data)} to CSV")
            return False
        
        # Filter fields if specified
        fields = kwargs.get('fields')
        if not fields and rows:
            # Get all fields from the first row
            if isinstance(rows[0], dict):
                fields = list(rows[0].keys())
        
        # Write CSV file
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields, extrasaction='ignore')
            
            # Write headers if requested (default: True)
            if kwargs.get('headers', True):
                writer.writeheader()
            
            # Write data rows
            for row in rows:
                if isinstance(row, dict):
                    writer.writerow(row)
        
        logging.info(f"Response from {endpoint} saved as CSV to {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error saving response as CSV: {str(e)}")
        return False

def output_jsonl_file(data, endpoint, **kwargs) -> bool:
    """
    Save API response as JSONL file (one JSON object per line).
    
    Args:
        data: API response data (processed)
        endpoint: API endpoint URL
        filename: Custom filename (default: based on endpoint)
        directory: Output directory (default: logs directory)
        
    Returns:
        bool: Success flag
    """
    try:
        # Create output directory if it doesn't exist
        directory = kwargs.get('directory')
        if directory is None:
            directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(directory, exist_ok=True)
        
        # Determine filename
        custom_filename = kwargs.get('filename')
        if custom_filename:
            filename = custom_filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            endpoint_name = endpoint.split('/')[-1].replace('?', '_').replace('&', '_')
            filename = f"{endpoint_name}_{timestamp}.jsonl"
        
        file_path = os.path.join(directory, filename)
        
        # Prepare data for JSONL
        if isinstance(data, dict):
            lines = [json.dumps(data, separators=(',', ':'))]
        elif isinstance(data, list):
            lines = [json.dumps(item, separators=(',', ':')) for item in data]
        elif "__split_json_output" in data:
            # Handle special output from split_json_array processor
            lines = data["__split_json_output"]
        elif "__flatten_json_output" in data:
            # Handle special output from flatten_json processor
            lines = [data["__flatten_json_output"]]
        else:
            logging.error(f"Cannot convert data type {type(data)} to JSONL")
            return False
        
        # Write JSONL file
        with open(file_path, 'w') as f:
            for line in lines:
                f.write(line + '\n')
        
        logging.info(f"Response from {endpoint} saved as JSONL to {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error saving response as JSONL: {str(e)}")
        return False

def output_splunk_hec(data, endpoint, **kwargs) -> bool:
    """
    Send API response to Splunk HTTP Event Collector.
    
    Args:
        data: API response data (processed)
        endpoint: API endpoint URL
        hec_url: Splunk HEC URL
        token: Splunk HEC token
        sourcetype: Splunk sourcetype (default: api_poller)
        source: Splunk source (default: endpoint URL)
        index: Splunk index (optional)
        verify: SSL verification flag (default: True)
        
    Returns:
        bool: Success flag
    """
    try:
        import requests
        
        # Get Splunk HEC configuration
        hec_url = kwargs.get('hec_url')
        token = kwargs.get('token')
        
        if not hec_url or not token:
            logging.error("Missing required HEC URL or token")
            return False
        
        # Get event parameters
        sourcetype = kwargs.get('sourcetype', 'api_poller')
        source = kwargs.get('source', endpoint)
        index = kwargs.get('index')
        verify = kwargs.get('verify', True)
        
        # Build event metadata
        event_metadata = {
            "sourcetype": sourcetype,
            "source": source
        }
        
        if index:
            event_metadata["index"] = index
        
        # Prepare data for HEC
        if isinstance(data, (dict, list)):
            # JSON data
            events = []
            
            if isinstance(data, dict):
                # Single event
                event = {
                    "event": data,
                    **event_metadata
                }
                events.append(event)
            elif isinstance(data, list):
                # Multiple events
                for item in data:
                    event = {
                        "event": item,
                        **event_metadata
                    }
                    events.append(event)
            
            # Send events to HEC
            headers = {
                "Authorization": f"Splunk {token}",
                "Content-Type": "application/json"
            }
            
            # Batch or single event
            if len(events) == 1:
                response = requests.post(
                    hec_url,
                    json=events[0],
                    headers=headers,
                    verify=verify
                )
            else:
                response = requests.post(
                    hec_url,
                    data="\n".join(json.dumps(event) for event in events),
                    headers=headers,
                    verify=verify
                )
            
            if response.status_code not in (200, 201):
                logging.error(f"Error sending to Splunk HEC: {response.status_code} - {response.text}")
                return False
            
            logging.info(f"Sent {len(events)} events to Splunk HEC")
            return True
            
        else:
            logging.error(f"Cannot send data type {type(data)} to Splunk HEC")
            return False
        
    except Exception as e:
        logging.error(f"Error sending to Splunk HEC: {str(e)}")
        return False

def register_processors(registry):
    """
    Register custom processors with the registry.
    
    Args:
        registry: Processor registry
    """
    # Register preprocessors
    registry.register_preprocessor("update_time_range", preprocess_update_time_range)
    registry.register_preprocessor("add_headers", preprocess_add_headers)
    registry.register_preprocessor("template_url", preprocess_template_url)
    registry.register_preprocessor("pagination_params", preprocess_pagination_params)
    
    # Register postprocessors
    registry.register_postprocessor("filter_response", postprocess_filter_response)
    registry.register_postprocessor("flatten_json", postprocess_flatten_json)
    registry.register_postprocessor("split_json_array", postprocess_split_json_array)
    registry.register_postprocessor("transform_keys", postprocess_transform_keys)
    registry.register_postprocessor("extract_nested", postprocess_extract_nested)
    
    # Register output processors
    registry.register_output_processor("csv_file", output_csv_file)
    registry.register_output_processor("jsonl_file", output_jsonl_file)
    registry.register_output_processor("splunk_hec", output_splunk_hec)
