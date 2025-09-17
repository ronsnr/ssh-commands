#!/usr/bin/env python3
"""
Example script demonstrating SSH command execution
This is a simple example showing how to use the SSH executor
"""

from ssh_executor import SSHCommandExecutor
import os
import sys

def example_usage():
    """Example of how to use the SSHCommandExecutor class directly."""
    
    # Example connection parameters (modify these for your environment)
    hostname = "127.0.0.1"  # localhost for testing
    username = "testuser"
    password = "testpass"
    commands_file = "commands.txt"
    
    print("SSH Command Executor Example")
    print("=" * 40)
    print(f"Target: {hostname}")
    print(f"User: {username}")
    print(f"Commands file: {commands_file}")
    print()
    
    # Create executor instance
    executor = SSHCommandExecutor(
        hostname=hostname,
        username=username,
        password=password
    )
    
    try:
        # Attempt to connect
        print("Attempting to connect...")
        if executor.connect():
            print("✓ Connection successful")
            
            # Execute commands from file
            print("Executing commands from file...")
            success = executor.execute_commands_from_file(commands_file)
            
            if success:
                print("✓ All commands executed successfully")
            else:
                print("⚠ Some commands failed")
        else:
            print("✗ Connection failed")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        executor.disconnect()

def create_test_commands():
    """Create a simple test commands file."""
    test_commands = [
        "# Test commands for demonstration",
        "echo 'Hello from SSH!'",
        "date",
        "whoami",
        "pwd",
        "echo 'Test completed'"
    ]
    
    with open("test_commands.txt", "w") as f:
        f.write("\n".join(test_commands))
    
    print("Created test_commands.txt with sample commands")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-test":
        create_test_commands()
    else:
        print("This is an example script. To use it:")
        print("1. Modify the connection parameters in the script")
        print("2. Run: python example.py")
        print("3. Or run: python example.py --create-test to create test commands")
        print()
        print("For actual usage, use ssh_executor.py or ssh_executor_config.py")