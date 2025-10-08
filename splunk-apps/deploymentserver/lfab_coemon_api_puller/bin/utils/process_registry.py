import os
import sys
import logging
import importlib.util
import inspect
from typing import Dict, Callable, Any, List, Optional, Union

class ProcessorRegistry:
    """
    Registry for API processors that handle data before and after API calls.
    """
    def __init__(self):
        """Initialize the processor registry."""
        self.preprocessors = {}
        self.postprocessors = {}
        self.output_processors = {}
    
    def register_preprocessor(self, name: str, processor_func: Callable) -> None:
        """
        Register a preprocessor function.
        
        Args:
            name: Name of the preprocessor
            processor_func: Preprocessor function
        """
        if name in self.preprocessors:
            logging.warning(f"Overriding existing preprocessor: {name}")
        
        self.preprocessors[name] = processor_func
        logging.info(f"Registered preprocessor: {name}")
    
    def register_postprocessor(self, name: str, processor_func: Callable) -> None:
        """
        Register a postprocessor function.
        
        Args:
            name: Name of the postprocessor
            processor_func: Postprocessor function
        """
        if name in self.postprocessors:
            logging.warning(f"Overriding existing postprocessor: {name}")
        
        self.postprocessors[name] = processor_func
        logging.info(f"Registered postprocessor: {name}")
    
    def register_output_processor(self, name: str, processor_func: Callable) -> None:
        """
        Register an output processor function.
        
        Args:
            name: Name of the output processor
            processor_func: Output processor function
        """
        if name in self.output_processors:
            logging.warning(f"Overriding existing output processor: {name}")
        
        self.output_processors[name] = processor_func
        logging.info(f"Registered output processor: {name}")
    
    def load_processors_from_directory(self, directory: str) -> None:
        """
        Load processors from a directory.
        
        Args:
            directory: Path to directory containing processor modules
        """
        if not os.path.isdir(directory):
            logging.error(f"Processor directory not found: {directory}")
            return
        
        # Add the directory to Python path if not already there
        if directory not in sys.path:
            sys.path.append(directory)
        
        # Load each Python file in the directory
        for filename in os.listdir(directory):
            if filename.endswith('.py') and not filename.startswith('__'):
                self._load_processor_module(os.path.join(directory, filename))
    
    def _load_processor_module(self, file_path: str) -> None:
        """
        Load a processor module from a file.
        
        Args:
            file_path: Path to the processor module file
        """
        try:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logging.error(f"Failed to load processor module spec: {file_path}")
                return
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if the module has a register_processors function
            if hasattr(module, 'register_processors'):
                module.register_processors(self)
                logging.info(f"Registered processors from module: {module_name}")
            else:
                # Auto-discover processor functions
                self._auto_discover_processors(module)
                
        except Exception as e:
            logging.error(f"Error loading processor module {file_path}: {str(e)}")
    
    def _auto_discover_processors(self, module) -> None:
        """
        Auto-discover processor functions in a module based on naming conventions.
        
        Args:
            module: Python module to scan for processors
        """
        module_name = module.__name__
        functions_count = 0
        
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            # Check for processor function naming conventions
            if name.startswith('preprocess_'):
                processor_name = name[len('preprocess_'):]
                self.register_preprocessor(processor_name, obj)
                functions_count += 1
            elif name.startswith('postprocess_'):
                processor_name = name[len('postprocess_'):]
                self.register_postprocessor(processor_name, obj)
                functions_count += 1
            elif name.startswith('output_'):
                processor_name = name[len('output_'):]
                self.register_output_processor(processor_name, obj)
                functions_count += 1
        
        if functions_count > 0:
            logging.info(f"Auto-discovered {functions_count} processors from module: {module_name}")
    
    def run_preprocessor(self, name: str, api_config: Dict, **kwargs) -> Dict:
        """
        Run a preprocessor.
        
        Args:
            name: Name of the preprocessor
            api_config: API configuration dictionary
            **kwargs: Additional arguments to pass to the preprocessor
            
        Returns:
            Dict: Modified API configuration
        """
        if name not in self.preprocessors:
            logging.error(f"Preprocessor not found: {name}")
            return api_config
        
        try:
            result = self.preprocessors[name](api_config, **kwargs)
            return result if result is not None else api_config
        except Exception as e:
            logging.error(f"Error running preprocessor {name}: {str(e)}")
            return api_config
    
    def run_postprocessor(self, name: str, response, **kwargs) -> Any:
        """
        Run a postprocessor.
        
        Args:
            name: Name of the postprocessor
            response: API response
            **kwargs: Additional arguments to pass to the postprocessor
            
        Returns:
            Any: Processed response
        """
        if name not in self.postprocessors:
            logging.error(f"Postprocessor not found: {name}")
            return response
        
        try:
            result = self.postprocessors[name](response, **kwargs)
            return result if result is not None else response
        except Exception as e:
            logging.error(f"Error running postprocessor {name}: {str(e)}")
            return response
    
    def run_output_processor(self, name: str, data, endpoint: str, **kwargs) -> bool:
        """
        Run an output processor.
        
        Args:
            name: Name of the output processor
            data: Data to output
            endpoint: API endpoint for file naming
            **kwargs: Additional arguments to pass to the output processor
            
        Returns:
            bool: Success flag
        """
        if name not in self.output_processors:
            logging.error(f"Output processor not found: {name}")
            return False
        
        try:
            return self.output_processors[name](data, endpoint, **kwargs)
        except Exception as e:
            logging.error(f"Error running output processor {name}: {str(e)}")
            return False


# Create a global registry instance
registry = ProcessorRegistry()
