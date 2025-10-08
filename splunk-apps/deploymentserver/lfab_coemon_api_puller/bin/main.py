import json
import yaml
import time
import os
import sys
import logging
from datetime import datetime, timedelta
from utils.logger import setup_logger
from utils.api_handler import APIHandler
from utils.oauth_handler import OAuthHandler
from utils.processor_registry import registry as processor_registry
import argparse
from utils.processors import register_processors
register_processors(processor_registry)

def load_config(config_file):
    """
    Load the configuration file that specifies API details and auth type.
    Supports both JSON and YAML formats.
    """
    try:
        file_ext = os.path.splitext(config_file)[1].lower()
        
        with open(config_file, 'r') as f:
            if file_ext in ['.yaml', '.yml']:
                # Load YAML configuration
                try:
                    return yaml.safe_load(f)
                except yaml.YAMLError as e:
                    logging.error(f"Failed to parse YAML configuration: {str(e)}")
                    sys.exit(1)
            else:
                # Default to JSON
                try:
                    return json.load(f)
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse JSON configuration: {str(e)}")
                    sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        sys.exit(1)

def save_config(config, filename):
    """
    Save configuration to a file in JSON or YAML format.
    
    Args:
        config: Configuration dictionary
        filename: Output filename (extension determines format)
    """
    try:
        file_ext = os.path.splitext(filename)[1].lower()
        
        with open(filename, 'w') as f:
            if file_ext in ['.yaml', '.yml']:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                logging.info(f"Configuration saved to {filename} in YAML format")
            else:
                json.dump(config, f, indent=2)
                logging.info(f"Configuration saved to {filename} in JSON format")
    except Exception as e:
        logging.error(f"Failed to save configuration: {str(e)}")

def json_to_yaml(json_file, yaml_file=None):
    """
    Convert a JSON configuration file to YAML.
    
    Args:
        json_file: Input JSON file
        yaml_file: Output YAML file (default: same name with .yaml extension)
    """
    if yaml_file is None:
        yaml_file = os.path.splitext(json_file)[0] + '.yaml'
        
    try:
        config = load_config(json_file)
        save_config(config, yaml_file)
    except Exception as e:
        logging.error(f"Failed to convert JSON to YAML: {str(e)}")

def cleanup_old_files(directory, days=7):
    """Delete files older than the specified number of days."""
    now = datetime.now()
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if now - file_time > timedelta(days=days):
                try:
                    os.remove(file_path)
                    logging.info(f"Deleted old file: {file_path}")
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {str(e)}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='API Polling System')
    parser.add_argument('--config', default='config.json', help='Path to config file (JSON or YAML)')
    parser.add_argument('--processors', help='Path to custom processors directory')
    parser.add_argument('--convert-to-yaml', help='Convert JSON config to YAML')
    args = parser.parse_args()

    # Handle JSON to YAML conversion if requested
    if args.convert_to_yaml:
        json_to_yaml(args.convert_to_yaml)
        return

    # Setup logging
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    logger = setup_logger(log_dir)
    
    # Load the specified configuration file
    config = load_config(args.config)
    
    # Load custom processors if specified
    #if args.processors:
    #    processor_path = os.path.abspath(args.processors)
    #    processor_registry.load_processors_from_directory(processor_path)
    #elif "processors_path" in config:
    #    processor_path = os.path.abspath(config["processors_path"])
    #    processor_registry.load_processors_from_directory(processor_path)

    # Initialize the appropriate auth handler based on the auth type
    auth_type = config.get("auth_type", "basic")
    auth_handler = None
    
    if auth_type.lower() == "basic":
        auth_handler = {"type": "basic", "username": config.get("username"), "password": config.get("password")}
    elif auth_type.lower() == "bearer":
        auth_handler = {"type": "bearer", "token": config.get("token")}
    elif auth_type.lower() == "oauth":
        oauth_config = config.get("oauth_config", {})
        auth_handler = OAuthHandler(
            client_id=oauth_config.get("client_id"),
            client_secret=oauth_config.get("client_secret"),
            token_url=oauth_config.get("token_url"),
            verify=oauth_config.get("verify", True)
        )
    else:
        logging.error(f"Unsupported authentication type: {auth_type}")
        sys.exit(1)
    
    # Initialize API handler
    api_handler = APIHandler(
        auth_handler=auth_handler, 
        proxy=config.get("proxy"), 
        verify=config.get("verify", True)
    )
    
    # Execute API calls based on configuration
    try:
        # Handle single APIs
        single_apis = config.get("single_apis", [])
        for api in single_apis:
            api_handler.call_single_api(api)
        
        # Handle nested APIs
        nested_apis = config.get("nested_apis", [])
        for api_pair in nested_apis:
            if isinstance(api_pair, dict) and "parent_api" in api_pair and "child_apis" in api_pair:
                parent_api = api_pair["parent_api"]
                child_apis = api_pair["child_apis"]
                api_handler.call_nested_apis(parent_api, child_apis)

        # Clean up old log files
        cleanup_days = config.get("cleanup_days", 7)
        cleanup_old_files(log_dir, days=cleanup_days)
        
    except Exception as e:
        logging.error(f"Error during API operations: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
