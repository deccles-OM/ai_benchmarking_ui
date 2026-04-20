"""
AI Client abstraction layer for supporting multiple AI providers.
Currently supports Gemini, with extensibility for future providers.
"""
class AIClient:
    """Base client for AI providers."""
    
    def __init__(self, provider: str, api_key: str, custom_endpoint: str = None):
        """
        Initialize AI client for specified provider.
        
        Args:
            provider: AI provider name (e.g., 'gemini' or 'other')
            api_key: API key for the provider
            custom_endpoint: Optional custom endpoint URL for the API (required for 'other' provider)
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.custom_endpoint = custom_endpoint
        self.client = None
        
        if self.provider == 'gemini':
            # Use the new google.genai package (google.generativeai is deprecated)
            try:
                import google.genai as genai
            except ImportError as e:
                raise RuntimeError(
                    "The 'google-genai' package is required to use the Gemini provider. "
                    "Install it with 'pip install google-genai' or 'pip install -r requirements.txt'."
                ) from e

            try:
                # Create a client instance (no configure() needed with google.genai)
                self.genai = genai.Client(api_key=api_key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini client: {e}") from e
        
        elif self.provider == 'other':
            # Custom endpoint provider
            if not custom_endpoint:
                raise ValueError("Custom endpoint must be provided when using 'other' provider")
            # For custom endpoints, we'll handle them in generate_content
            self.custom_endpoint = custom_endpoint
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def test_connection(self):
        """
        Test connection to the AI provider.
        
        Returns:
            dict: {'success': bool, 'message': str, 'models': list}
        """
        if self.provider == 'gemini':
            try:
                # Use the google.genai Client API to list models
                models = self.genai.models.list()
                model_names = [m.name for m in models]
                return {
                    'success': True,
                    'message': 'Gemini API connection successful',
                    'models': model_names
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Connection failed: {str(e)}',
                    'models': []
                }
        
        elif self.provider == 'other':
            # Test custom endpoint
            try:
                import requests
                # Simple test - try to reach the endpoint
                response = requests.head(self.custom_endpoint, timeout=5)
                return {
                    'success': True,
                    'message': f'Custom endpoint connection successful (HTTP {response.status_code})',
                    'models': ['custom-model']
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Connection to custom endpoint failed: {str(e)}',
                    'models': []
                }
        
        return {'success': False, 'message': 'Unknown provider', 'models': []}
    
    def list_models(self):
        """
        List available models from the provider.
        
        Returns:
            list: List of model names/identifiers
        """
        if self.provider == 'gemini':
            try:
                models = self.genai.models.list()
                return [m.name for m in models]
            except Exception as e:
                print(f"Error listing models: {e}")
                return []
        
        elif self.provider == 'other':
            # For custom endpoints, return a generic model name
            return ['custom-model']
        
        return []
    
    def generate_content(self, model: str, contents: str, timeout_seconds: int = 300):
        """
        Generate content using the specified model with timeout support.
        
        Args:
            model: Model identifier
            contents: Prompt/content to send to model
            timeout_seconds: Maximum time to wait for response (default 300 seconds / 5 minutes)
            
        Returns:
            Response object from the provider
        """
        if self.provider == 'gemini':
            import threading
            response_holder = {'resp': None, 'error': None, 'timed_out': False}

            def call_api():
                try:
                    response_holder['resp'] = self.genai.models.generate_content(
                        model=model, 
                        contents=contents
                    )
                except Exception as e:
                    response_holder['error'] = e

            # Create and start the API call thread
            api_thread = threading.Thread(target=call_api, daemon=True)
            api_thread.start()
            
            # Wait for completion with timeout
            api_thread.join(timeout=timeout_seconds)

            # Check if thread is still running (timeout occurred)
            if api_thread.is_alive():
                response_holder['timed_out'] = True
                raise TimeoutError(
                    f"API call timed out after {timeout_seconds} seconds. "
                    f"The model may be slow or the API may be unresponsive. "
                    f"Try increasing the timeout or check your internet connection."
                )

            # Check for errors
            if response_holder['error']:
                raise response_holder['error']

            # Return the response
            if response_holder['resp'] is None and not response_holder['timed_out']:
                raise RuntimeError("API call completed but returned no response")
            
            return response_holder['resp']
        
        elif self.provider == 'other':
            # Handle custom endpoint
            import threading
            import requests
            import json
            
            response_holder = {'resp': None, 'error': None, 'timed_out': False}

            def call_api():
                try:
                    # Send request to custom endpoint
                    # Assuming standard format: POST with JSON body containing 'contents'
                    headers = {'Content-Type': 'application/json'}
                    if self.api_key:
                        headers['Authorization'] = f'Bearer {self.api_key}'
                    
                    payload = {
                        'model': model,
                        'contents': contents if isinstance(contents, str) else str(contents)
                    }
                    
                    response = requests.post(
                        self.custom_endpoint,
                        json=payload,
                        headers=headers,
                        timeout=timeout_seconds
                    )
                    response.raise_for_status()
                    
                    # Store the response
                    response_holder['resp'] = response.json()
                    
                except Exception as e:
                    response_holder['error'] = e

            # Create and start the API call thread
            api_thread = threading.Thread(target=call_api, daemon=True)
            api_thread.start()
            
            # Wait for completion with timeout
            api_thread.join(timeout=timeout_seconds)

            # Check if thread is still running (timeout occurred)
            if api_thread.is_alive():
                response_holder['timed_out'] = True
                raise TimeoutError(
                    f"Custom endpoint call timed out after {timeout_seconds} seconds. "
                    f"The endpoint may be slow or unresponsive."
                )

            # Check for errors
            if response_holder['error']:
                raise response_holder['error']

            # Return the response
            if response_holder['resp'] is None and not response_holder['timed_out']:
                raise RuntimeError("Custom endpoint returned no response")
            
            return response_holder['resp']
        
        raise ValueError(f"Provider {self.provider} does not support content generation")


def create_client(provider: str, api_key: str, custom_endpoint: str = None) -> AIClient:
    """
    Factory function to create an AI client.
    
    Args:
        provider: AI provider name (e.g., 'gemini')
        api_key: API key for the provider
        custom_endpoint: Optional custom endpoint URL for the API
        
    Returns:
        AIClient instance
    """
    return AIClient(provider, api_key, custom_endpoint)
