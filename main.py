import sys
import os
try:
    from .monitor import TerminalMonitor
    from .config import Config
except ImportError:
    # Fallback for running directly
    from monitor import TerminalMonitor
    from config import Config

def main():
    """
    Main entry point for the Smart Terminal Monitor.
    """
    try:
        # Load configuration
        config = Config()
        config.load()

        print(f"DEBUG: Loaded config from {config.config_path}")
        print(f"DEBUG: Provider: {config.provider}")
        print(f"DEBUG: Model: {config.model}")
        print(f"DEBUG: API Key: {'*' * 5 + config.api_key[-4:] if config.api_key else 'None'}")

        # Initialize monitor
        monitor = TerminalMonitor(config)
        
        # Start the shell wrapper
        monitor.run()
        
    except Exception as e:
        print(f"Error starting Smart Terminal Monitor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
