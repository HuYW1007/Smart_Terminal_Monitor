import os
import yaml

class Config:
    def __init__(self):
        self.config_path = os.path.expanduser("~/.smart_term_config.yaml")
        self.provider = "openai"
        self.api_key = ""
        self.model = "gpt-4o"
        self.base_url = None
        self.language = None
        self.max_context_chars = 10000
        self.log_summary_length = 100

    def load(self):
        """
        Loads configuration from file or environment variables.
        """
        # Check current directory, then package directory, then home directory
        package_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths = [
            "smart_term_config.yaml",
            os.path.join(package_dir, "smart_term_config.yaml"),
            os.path.expanduser("~/.smart_term_config.yaml")
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                self.config_path = path
                break
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        # Normalize keys to handle potential leading/trailing whitespace
                        data = {k.strip(): v for k, v in data.items() if isinstance(k, str)}
                        
                        self.provider = data.get('provider', self.provider)
                        self.api_key = data.get('api_key', self.api_key)
                        self.model = data.get('model', self.model)
                        self.base_url = data.get('base_url', self.base_url)
                        self.language = data.get('language', self.language)
                        self.max_context_chars = data.get('max_context_chars', self.max_context_chars)
                        self.log_summary_length = data.get('log_summary_length', self.log_summary_length)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")
        
        # Environment variables override config file
        self.api_key = os.environ.get("SMART_TERM_API_KEY", self.api_key)
        self.base_url = os.environ.get("SMART_TERM_BASE_URL", self.base_url)

    def save(self):
        """
        Saves the current configuration to the config file.
        """
        data = {
            'provider': self.provider,
            'api_key': self.api_key,
            'model': self.model,
            'base_url': self.base_url,
            'language': self.language,
            'max_context_chars': self.max_context_chars,
            'log_summary_length': self.log_summary_length
        }
        
        # If config_path doesn't exist (new install), default to current dir or home
        if not self.config_path or not os.path.exists(self.config_path):
             self.config_path = "smart_term_config.yaml"

        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            print(f"Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
