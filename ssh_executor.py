#!/usr/bin/env python3
"""
SSH Command Executor
Connects to a remote server via SSH and executes commands from a commands.txt file.
"""

import sys
import os
import time
import logging
from typing import List, Optional
import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError


class SSHCommandExecutor:
    """Class to handle SSH connections and command execution."""
    
    def __init__(self, hostname: str, username: str, password: Optional[str] = None, 
                 key_filename: Optional[str] = None, port: int = 22):
        """
        Initialize SSH connection parameters.
        
        Args:
            hostname: Remote server hostname or IP
            username: SSH username
            password: SSH password (optional if using key)
            key_filename: Path to private key file (optional)
            port: SSH port (default: 22)
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.client = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """
        Establish SSH connection to the remote server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddHostKey())
            
            self.logger.info(f"Connecting to {self.hostname}:{self.port} as {self.username}")
            
            if self.key_filename and os.path.exists(self.key_filename):
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_filename
                )
            elif self.password:
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password
                )
            else:
                self.logger.error("No authentication method provided (password or key)")
                return False
            
            self.logger.info("SSH connection established successfully")
            return True
            
        except AuthenticationException:
            self.logger.error("Authentication failed")
            return False
        except NoValidConnectionsError:
            self.logger.error(f"Unable to connect to {self.hostname}:{self.port}")
            return False
        except SSHException as e:
            self.logger.error(f"SSH connection error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during connection: {e}")
            return False
    
    def execute_command(self, command: str) -> tuple[int, str, str]:
        """
        Execute a single command on the remote server.
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self.client:
            raise Exception("SSH connection not established")
        
        try:
            self.logger.info(f"Executing command: {command}")
            stdin, stdout, stderr = self.client.exec_command(command)
            
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            if exit_code == 0:
                self.logger.info(f"Command executed successfully (exit code: {exit_code})")
            else:
                self.logger.warning(f"Command failed with exit code: {exit_code}")
            
            return exit_code, stdout_data, stderr_data
            
        except Exception as e:
            self.logger.error(f"Error executing command '{command}': {e}")
            return -1, "", str(e)
    
    def load_commands(self, commands_file: str) -> List[str]:
        """
        Load commands from a text file.
        
        Args:
            commands_file: Path to the commands file
            
        Returns:
            List of commands to execute
        """
        try:
            if not os.path.exists(commands_file):
                self.logger.error(f"Commands file not found: {commands_file}")
                return []
            
            with open(commands_file, 'r') as f:
                commands = []
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        commands.append(line)
                        self.logger.debug(f"Loaded command {line_num}: {line}")
            
            self.logger.info(f"Loaded {len(commands)} commands from {commands_file}")
            return commands
            
        except Exception as e:
            self.logger.error(f"Error loading commands from {commands_file}: {e}")
            return []
    
    def execute_commands_from_file(self, commands_file: str) -> bool:
        """
        Execute all commands from the specified file.
        
        Args:
            commands_file: Path to the commands file
            
        Returns:
            True if all commands executed successfully, False otherwise
        """
        commands = self.load_commands(commands_file)
        if not commands:
            self.logger.error("No commands to execute")
            return False
        
        success_count = 0
        total_commands = len(commands)
        
        for i, command in enumerate(commands, 1):
            self.logger.info(f"Executing command {i}/{total_commands}")
            exit_code, stdout, stderr = self.execute_command(command)
            
            if stdout:
                print(f"STDOUT:\n{stdout}")
            if stderr:
                print(f"STDERR:\n{stderr}")
            
            if exit_code == 0:
                success_count += 1
            else:
                self.logger.error(f"Command failed: {command}")
            
            # Small delay between commands
            time.sleep(0.5)
        
        self.logger.info(f"Execution complete: {success_count}/{total_commands} commands successful")
        return success_count == total_commands
    
    def disconnect(self):
        """Close the SSH connection."""
        if self.client:
            self.client.close()
            self.logger.info("SSH connection closed")


def main():
    """Main function to run the SSH command executor."""
    if len(sys.argv) < 4:
        print("Usage: python ssh_executor.py <hostname> <username> <commands_file> [password] [key_file] [port]")
        print("Example: python ssh_executor.py 192.168.1.100 user commands.txt mypassword")
        print("Example: python ssh_executor.py 192.168.1.100 user commands.txt '' ~/.ssh/id_rsa")
        sys.exit(1)
    
    hostname = sys.argv[1]
    username = sys.argv[2]
    commands_file = sys.argv[3]
    password = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
    key_filename = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
    port = int(sys.argv[6]) if len(sys.argv) > 6 else 22
    
    # Create SSH executor instance
    executor = SSHCommandExecutor(
        hostname=hostname,
        username=username,
        password=password,
        key_filename=key_filename,
        port=port
    )
    
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