import logging
import os
from datetime import datetime

def setup_logger(log_dir=None):
    """
    Set up logging configuration.
    
    Args:
        log_dir: Directory to store log files
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamp for the log filename
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"api_poller_{timestamp}.log")
    
    # Set up logging format and handlers
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    # console_handler.setFormatter(formatter)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    # logger.addHandler(console_handler)
    
    logging.info("Logger initialized")
    return logger
