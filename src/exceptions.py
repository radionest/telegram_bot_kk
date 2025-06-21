"""Custom exceptions for the bot."""


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str):
        """Initialize configuration error.
        
        Args:
            message: Error message describing the configuration issue
        """
        self.message = message
        super().__init__(self.message)


class BotPermissionError(Exception):
    """Exception raised when bot lacks required permissions."""
    
    def __init__(self, message: str):
        """Initialize bot permission error.
        
        Args:
            message: Error message describing the permission issue
        """
        self.message = message
        super().__init__(self.message)


class APIError(Exception):
    """Exception raised for external API errors."""
    
    def __init__(self, message: str, api_name: str = ""):
        """Initialize API error.
        
        Args:
            message: Error message describing the API issue
            api_name: Name of the API that caused the error
        """
        self.message = message
        self.api_name = api_name
        super().__init__(self.message)
        

class ChatManagerError(Exception):
    """Exception raised for chat management errors.
    
    This exception is raised when errors occur during chat management operations
    such as setting up topics, managing permissions, or handling chat-related operations.
    """
    ...