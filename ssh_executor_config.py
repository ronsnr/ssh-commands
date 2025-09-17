#!/usr/bin/env python3
"""
SSH Command Executor with Configuration File Support
Connects to a remote server via SSH and executes commands from a commands.txt file.
Uses config.json for connection parameters.
"""

import json
import os
import sys
from ssh_executor import SSHCommandExecutor


def load_config(config_file: str = "config.json") -> dict:
    """
    Load SSH connection configuration from JSON file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    default_config = {
        "hostname": "",
        "username": "",
        "password": "",
        "key_filename": "",
        "port": 22,
        "commands_file": "commands.txt"
    }
    
    if not os.path.exists(config_file):
        print(f"Configuration file {config_file} not found. Creating template...")
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"Please edit {config_file} with your SSH connection details")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        if not config.get("hostname") or not config.get("username"):
            print("Error: hostname and username are required in config file")
            return None
        
        return config
    
    except json.JSONDecodeError as e:
        print(f"Error parsing configuration file: {e}")
        return None
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None


def main():
    """Main function using configuration file."""
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    
    config = load_config(config_file)
    if not config:
        sys.exit(1)
    
    # Create SSH executor instance
    executor = SSHCommandExecutor(
        hostname=config["hostname"],
        username=config["username"],
        password=config.get("password") or None,
        key_filename=config.get("key_filename") or None,
        port=config.get("port", 22)
    )
    
    commands_file = config.get("commands_file", "commands.txt")
    
    try:
        # Connect to the remote server
        if not executor.connect():
            print("Failed to establish SSH connection")
            sys.exit(1)
        
        # Execute commands from file
        success = executor.execute_commands_from_file(commands_file)
        
        if success:
            print("All commands executed successfully")
        else:
            print("Some commands failed to execute")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        executor.disconnect()


if __name__ == "__main__":
    main()