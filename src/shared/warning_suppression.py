"""
Warning Suppression Utilities
Suppress Azure/aiohttp warnings for cleaner console output
"""
import warnings
import os
import logging


def setup_warning_suppression():
    """Set up comprehensive warning suppression for Azure/aiohttp"""
    warnings.filterwarnings('ignore', category=ResourceWarning)
    warnings.filterwarnings('ignore', message='Unclosed client session')
    warnings.filterwarnings('ignore', message='Unclosed connector')
    warnings.filterwarnings('ignore', message='SSL shutdown timed out')
    warnings.filterwarnings('ignore', message='Connection lost')
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    warnings.simplefilter('ignore', ResourceWarning)
    
    # Completely suppress asyncio and aiohttp logging
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.CRITICAL)
    logging.basicConfig(level=logging.CRITICAL)
    
    # Set environment variables for warning suppression
    os.environ['PYTHONWARNINGS'] = 'ignore::ResourceWarning'
    os.environ['AZURE_CLI_DISABLE_CONNECTION_VERIFICATION'] = 'true'
