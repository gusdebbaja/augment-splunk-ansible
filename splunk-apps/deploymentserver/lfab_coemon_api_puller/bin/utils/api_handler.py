import requests
import json
import logging
import os
from datetime import datetime
import time
from utils.processor_registry import registry
from urllib3.exceptions import InsecureRequestWarning

class APIHandler:
    def __init__(self, auth_handler, verify, proxy=None):
        """
        Initialize the API Handler with authentication details and proxy settings.
        
        Args:
            auth_handler: Authentication handler object or dictionary with auth details
            proxy: Proxy server URL if needed
            verify: SSL verification flag
        """
        self.auth_handler = auth_handler
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.verify = verify
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        self.session = requests.Session()
        
    def _prepare_headers(self):
        """Prepare request headers based on authentication type."""
        headers = {'Content-Type': 'application/json'}
        
        if isinstance(self.auth_handler, dict):
            auth_type = self.auth_handler.get("type", "").lower()
            
            if auth_type == "basic":
                # Basic auth is handled by requests directly through auth parameter
                pass
            elif auth_type == "bearer":
                headers['Authorization'] = f"Bearer {self.auth_handler.get('token')}"
        else:
            # For OAuth handler, get the token
            token = self.auth_handler.get_token()
            if token:
                headers['Authorization'] = f"Bearer {token}"
                
        return headers
    
    def _get_auth(self):
        """Get auth tuple for basic authentication."""
        if isinstance(self.auth_handler, dict) and self.auth_handler.get("type") == "basic":
            return (self.auth_handler.get("username"), self.auth_handler.get("password"))
        return None
    
    def _save_response(self, endpoint, response_data, is_error=False, status_code=None):
        """
        Save processed API response to file.
        
        Args:
            endpoint: API endpoint URL
            response_data: Processed response data to save
            is_error: Whether this is an error response
            status_code: HTTP status code (for error responses)
        """
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a filename based on the endpoint and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        endpoint_name = endpoint.split('/')[-1].replace('?', '_').replace('&', '_')
        
        # Determine file path based on whether it's an error
        if is_error:
            filename = f"error_{endpoint_name}_{timestamp}.log"
        else:
            filename = f"{endpoint_name}_{timestamp}.log"
            
        file_path = os.path.join(log_dir, filename)
        
        try:
            # Save to file, handling different types of response data
            with open(file_path, 'w') as f:
                if isinstance(response_data, dict):
                    # Check if this is a special output format from a processor
                    if "__flatten_json_output" in response_data:
                        # Direct string output from flatten_json processor
                        f.write(response_data["__flatten_json_output"])
                    elif "__split_json_output" in response_data:
                        # Multiple JSON lines from split_json_array processor
                        f.write("\n".join(response_data["__split_json_output"]))
                    else:
                        # Regular JSON object
                        json.dump(response_data, f, indent=2)
                elif isinstance(response_data, str):
                    # String output
                    f.write(response_data)
                elif is_error and status_code:
                    # Error details
                    f.write(f"Status code: {status_code}\n")
                    f.write(f"Response: {response_data}\n")
                else:
                    # Fallback: convert to string
                    f.write(str(response_data))
                    
            logging.info(f"{'Error ' if is_error else ''}Response from {endpoint} saved to {file_path}")
            
        except Exception as e:
            logging.error(f"Failed to save {'error ' if is_error else ''}response from {endpoint}: {str(e)}")
    
    def call_single_api(self, api_config):
        """
        Call a single API endpoint with preprocessing, postprocessing, and save the response.
        
        Args:
            api_config: Dictionary containing API configuration:
                - url: API endpoint URL
                - method: HTTP method (GET, POST, etc.)
                - params: Query parameters
                - headers: Additional headers
                - body: Request body
                - interval: Polling interval in seconds
                - verify: SSL verification flag
                - preprocess: Preprocessor configuration
                - postprocess: Postprocessor configuration
                - output: Output processor configuration
        """
        # Apply preprocessor if configured
        if "preprocess" in api_config and isinstance(api_config["preprocess"], dict):
            preprocess_config = api_config["preprocess"]
            preprocess_name = preprocess_config.get("name")
            preprocess_args = preprocess_config.get("args", {})
            
            if preprocess_name:
                logging.info(f"Running preprocessor: {preprocess_name}")
                api_config = registry.run_preprocessor(preprocess_name, api_config, **preprocess_args)
        
        url = api_config.get("url")
        method = api_config.get("method", "GET").upper()
        params = api_config.get("params", {})
        custom_headers = api_config.get("headers", {})
        body = api_config.get("body", {})
        verify = api_config.get("verify", self.verify)
        
        # Merge default headers with custom headers
        headers = self._prepare_headers()
        headers.update(custom_headers)
        
        try:
            logging.info(f"Calling {method} {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=body if body else None,
                auth=self._get_auth(),
                proxies=self.proxies,
                verify=verify,
                timeout=30
            )
            
            # Log the response status
            logging.info(f"Response status: {response.status_code}")
            
            # Save error responses separately
            if response.status_code >= 400:
                self._save_response(url, response.text, is_error=True, status_code=response.status_code)
                return response
            
            # Process the response if it was successful
            processed_data = None
            
            try:
                # First try to parse as JSON
                response_data = response.json()
                processed_data = response_data
                
                # Apply postprocessor if configured
                if "postprocess" in api_config and isinstance(api_config["postprocess"], dict):
                    postprocess_config = api_config["postprocess"]
                    postprocess_name = postprocess_config.get("name")
                    postprocess_args = postprocess_config.get("args", {})
                    
                    if postprocess_name:
                        logging.info(f"Running postprocessor: {postprocess_name}")
                        post_result = registry.run_postprocessor(postprocess_name, response, **postprocess_args)
                        
                        # Improved error handling
                        if post_result is not None:
                            processed_data = post_result
                        else:
                            # Handle failed postprocessor by using the original response data
                            logging.warning(f"Postprocessor {postprocess_name} returned None or failed. Using original response data.")
                            try:
                                processed_data = response.json()  # Try to parse as JSON first
                            except ValueError:
                                processed_data = response.text  # Fall back to text if not JSON
                
            except ValueError:
                # Not JSON, use text
                processed_data = response.text
            
            # Apply output processor if configured
            if "output" in api_config and isinstance(api_config["output"], dict):
                output_config = api_config["output"]
                output_name = output_config.get("name")
                output_args = output_config.get("args", {})
                
                if output_name:
                    logging.info(f"Running output processor: {output_name}")
                    success = registry.run_output_processor(output_name, processed_data, url, **output_args)
                    if success:
                        # If the output processor handled saving, we're done
                        return response
            
            # Save the processed response using the default method
            self._save_response(url, processed_data)
            
            return response
            
        except Exception as e:
            logging.error(f"Error calling {url}: {str(e)}")
            return None
    
    def call_nested_apis(self, parent_api_config, child_api_configs):
        """
        Call a parent API, then call child APIs using values from the parent response.
        
        This method is flexible to handle different parent response structures:
        1. A list of items (each item can be used for URL substitution)
        2. A single object with fields that can be used for URL substitution
        3. A nested structure where items_path points to a list or values
        
        Args:
            parent_api_config: Configuration for the parent API
            child_api_configs: List of configurations for child APIs
        """
        # Call the parent API
        parent_response = self.call_single_api(parent_api_config)
        
        if not parent_response or parent_response.status_code >= 400:
            logging.error(f"Failed to get response from parent API {parent_api_config.get('url')}")
            return
        
        try:
            parent_data = parent_response.json()
            logging.error(f"Parent API response: {parent_data}.")
            items_path = parent_api_config.get("items_path", "")
            
            # Determine how to process the parent response based on its structure and config
            if items_path:
                # Navigate to the specified path in the response
                target_data = parent_data
                for part in items_path.split('.'):
                    if not part:
                        continue
                    
                    if isinstance(target_data, dict) and part in target_data:
                        target_data = target_data[part]
                    elif isinstance(target_data, list) and part.isdigit():
                        idx = int(part)
                        if 0 <= idx < len(target_data):
                            target_data = target_data[idx]
                        else:
                            logging.error(f"Index {idx} out of range in items_path")
                            return
                    else:
                        logging.error(f"Cannot find '{part}' in response at path '{items_path}'")
                        return
            else:
                # If no items_path is specified, use the entire response
                target_data = parent_data
            
            # Determine how to iterate based on the structure of the target data
            if isinstance(target_data, list):
                # Case 1: Target is a list - process each item in the list
                items_to_process = target_data
                logging.info(f"Processing list of {len(items_to_process)} items from parent API")
            elif isinstance(target_data, dict):
                # Case 2: Target is a dictionary - use it as a single item
                items_to_process = [target_data]
                logging.info("Processing single dictionary item from parent API")
            else:
                # Case 3: Target is a primitive value - wrap it in a dictionary with the path's last part as key
                key_name = items_path.split('.')[-1] if items_path else "value"
                items_to_process = [{key_name: target_data}]
                logging.info(f"Processing primitive value '{target_data}' as dictionary with key '{key_name}'")
            
            # Process each item and call child APIs
            for item in items_to_process:
                # For primitive values wrapped in dictionaries, log the item being processed
                if not isinstance(item, dict):
                    logging.warning(f"Item is not a dictionary: {item}. Creating a default key.")
                    item = {"item": item}
                    
                logging.debug(f"Processing item: {item}")
                
                for child_config in child_api_configs:
                    # Make a copy of the child config
                    child_api = child_config.copy()
                    
                    # Replace placeholders in URL with values from the item
                    url = child_api.get("url", "")
                    original_url = url
                    
                    # Handle dictionary items
                    if isinstance(item, dict):
                        for key, value in item.items():
                            placeholder = f"{{{key}}}"
                            if placeholder in url:
                                url = url.replace(placeholder, str(value))
                    
                    # Check if all placeholders were replaced
                    if '{' in url and '}' in url:
                        logging.warning(f"Some placeholders not replaced in URL: {url}")
                        
                        # You could either skip this child API or try to find the values elsewhere
                        # Option 1: Skip this child API for this item
                        # continue
                        
                        # Option 2: Try to find values in the parent data as a fallback
                        if isinstance(parent_data, dict):
                            for key, value in parent_data.items():
                                placeholder = f"{{{key}}}"
                                if placeholder in url:
                                    url = url.replace(placeholder, str(value))
                    
                    # If we still have unresolved placeholders, log an error and skip
                    if '{' in url and '}' in url:
                        logging.error(f"Unresolved placeholders in URL: {url}. Skipping this child API call.")
                        continue
                    
                    child_api["url"] = url
                    logging.info(f"Calling child API: {url} (original: {original_url})")
                    
                    # Call the child API
                    self.call_single_api(child_api)
                    
                    # Respect the interval between API calls
                    interval = child_api.get("interval", 1)
                    if interval > 0:
                        time.sleep(interval)
                        
        except Exception as e:
            logging.error(f"Error processing nested APIs: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
