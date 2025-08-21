"""
Centralized error handling utilities for the AI Content Generation Suite
"""

import logging
from typing import Any, Optional, Dict
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Base exception for service errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class WebScrapingError(ServiceError):
    """Error during web scraping operations"""
    pass


class LLMGenerationError(ServiceError):
    """Error during LLM generation"""
    pass


class ValidationError(ServiceError):
    """Error during input validation"""
    pass


class RateLimitError(ServiceError):
    """Rate limit exceeded error"""
    pass


def async_error_handler(fallback_value: Any = None, log_errors: bool = True):
    """
    Decorator for handling errors in async functions
    
    Args:
        fallback_value: Value to return on error
        log_errors: Whether to log errors
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                
                # Re-raise custom errors
                if isinstance(e, ServiceError):
                    raise
                
                # Return fallback for other errors
                return fallback_value
        return wrapper
    return decorator


def retry_async(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying async functions with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator


def validate_input(validation_func):
    """
    Decorator for input validation
    
    Args:
        validation_func: Function that validates input and raises ValidationError if invalid
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            validation_func(*args, **kwargs)
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            validation_func(*args, **kwargs)
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def handle_api_response(response, success_status_codes: list = None):
    """
    Standard handler for API responses
    
    Args:
        response: HTTP response object
        success_status_codes: List of status codes considered successful
    
    Returns:
        Response data if successful
    
    Raises:
        ServiceError: If response indicates failure
    """
    if success_status_codes is None:
        success_status_codes = [200, 201, 204]
    
    if response.status_code not in success_status_codes:
        error_msg = f"API request failed with status {response.status_code}"
        
        # Try to extract error details from response
        try:
            error_details = response.json()
        except:
            error_details = {"response_text": response.text[:500]}
        
        if response.status_code == 429:
            raise RateLimitError(error_msg, "RATE_LIMIT", error_details)
        elif response.status_code >= 500:
            raise ServiceError(error_msg, "SERVER_ERROR", error_details)
        elif response.status_code >= 400:
            raise ValidationError(error_msg, "CLIENT_ERROR", error_details)
        else:
            raise ServiceError(error_msg, "UNKNOWN_ERROR", error_details)
    
    # Parse successful response
    try:
        return response.json()
    except:
        return response.text


def safe_get(dictionary: dict, *keys, default: Any = None):
    """
    Safely get nested dictionary values
    
    Args:
        dictionary: Dictionary to search
        *keys: Keys to traverse
        default: Default value if key not found
    
    Returns:
        Value at nested key or default
    """
    current = dictionary
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current