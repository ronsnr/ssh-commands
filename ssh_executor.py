#!/usr/bin/env python3
"""
SSH Command Executor
Connects to a remote server via SSH and executes commands from a file.
"""

import sys
import os
import argparse
import time
import logging
from typing import List, Optional
import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError
import getpass

from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    
    def connect(self, legacy_crypto: bool = False) -> bool:
        """
        Establish SSH connection to the remote server.
        
        Args:
            legacy_crypto: If True, enable legacy crypto algorithms for compatibility.
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to {self.hostname}:{self.port} as {self.username}")
            self.logger.debug(f"Password provided: {'Yes' if self.password else 'No'}")
            self.logger.debug(f"Key file provided: {self.key_filename if self.key_filename else 'No'}")

            connect_kwargs = {
                "hostname": self.hostname,
                "port": self.port,
                "username": self.username,
            }

            if legacy_crypto:
                self.logger.info("Enabling legacy crypto algorithms for compatibility.")
                connect_kwargs["disabled_algorithms"] = {
                    "kex": ["diffie-hellman-group-exchange-sha256"],
                    "ciphers": ["aes256-ctr", "aes192-ctr", "aes128-ctr"]
                }

            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            
            if not self.password and not self.key_filename:
                self.password = getpass.getpass(prompt="Enter your SSH password: ")
                if not self.password:
                    self.logger.error("No authentication method provided (password or key)")
                    return False

            if self.key_filename and os.path.exists(self.key_filename):
                connect_kwargs["key_filename"] = self.key_filename
                self.client.connect(**connect_kwargs)
            elif self.password:
                connect_kwargs["password"] = self.password
                self.client.connect(**connect_kwargs)
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
    
    def execute_commands_from_file(self, commands_file: str, parallel: bool = False, max_workers: Optional[int] = None) -> bool: # noqa: E501
        """
        Execute all commands from the specified file.
        
        Args:
            commands_file: Path to the commands file
            parallel: If True, execute commands in parallel.
            max_workers: Maximum number of threads for parallel execution.
            
        Returns:
            True if all commands executed successfully, False otherwise
        """
        commands = self.load_commands(commands_file)
        if not commands:
            return False
        
        success_count = 0
        total_commands = len(commands)

        if parallel:
            self.logger.info(f"Executing {total_commands} commands in parallel (max_workers={max_workers or 'default'})...")
            results = {}
            
            # Determine the number of workers and chunk the commands
            num_workers = min(max_workers or os.cpu_count() * 2 or 1, total_commands)
            chunk_size = (total_commands + num_workers - 1) // num_workers # Ceiling division
            command_chunks = [commands[i:i + chunk_size] for i in range(0, total_commands, chunk_size)]

            worker_func = partial(_execute_command_chunk_worker, self.hostname, self.username, self.password, self.key_filename, self.port, legacy_crypto=self.client.get_transport().disabled_algorithms is not None)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit each chunk of commands to a worker
                future_to_chunk = {executor.submit(worker_func, chunk, i): chunk for i, chunk in enumerate(command_chunks, 1)}
                
                for future in as_completed(future_to_chunk):
                    chunk_results = future.result()
                    try:
                        # Process and print results as they come in
                        for command, (exit_code, stdout, stderr) in chunk_results.items():
                            results[command] = (exit_code, stdout, stderr)
                            if exit_code == 0:
                                success_count += 1
                    except Exception as exc:
                        self.logger.error(f"A worker thread generated an exception: {exc}")

            # Print results in original order
            for command in commands:
                exit_code, stdout, stderr = results.get(command, (-1, "", "Command not executed or result missing"))
                print("-" * 40)
                print(f"COMMAND: {command}")
                if stdout:
                    print(f"STDOUT:\n{stdout}")
                if stderr:
                    print(f"STDERR:\n{stderr}")
                
                if exit_code != 0:
                    self.logger.error(f"Command failed (exit code {exit_code}): {command}")
                print("-" * 40)

        else: # Sequential execution
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

def _execute_command_chunk_worker(hostname: str, username: str, password: Optional[str], 
                                  key_filename: Optional[str], port: int, 
                                  command_chunk: List[str], worker_id: int,
                                  legacy_crypto: bool = False) -> dict[str, tuple[int, str, str]]:
    """
    A worker function to execute a chunk of commands over a single, persistent SSH session.
    This is designed to be called by the ThreadPoolExecutor.
    """
    worker_logger = logging.getLogger(f"worker-{worker_id}")
    results = {}

    executor = SSHCommandExecutor(
        hostname=hostname,
        username=username,
        password=password,
        key_filename=key_filename,
        port=port
    )
    executor.logger.setLevel(logging.WARNING)

    worker_logger.info(f"Starting to process {len(command_chunk)} commands.")
    if executor.connect(legacy_crypto=legacy_crypto):
        try:
            for command in command_chunk:
                results[command] = executor.execute_command(command)
        finally:
            executor.disconnect()
    else:
        worker_logger.error(f"Could not connect to {hostname}. Skipping {len(command_chunk)} commands.")
        for command in command_chunk:
            results[command] = (-1, "", f"Worker failed to connect to {hostname}")
    
    worker_logger.info("Finished processing command chunk.")
    return results

def main():
    """Main function to run the SSH command executor."""
    parser = argparse.ArgumentParser(description="SSH Command Executor")
    parser.add_argument("hostname", help="Remote server hostname or IP")
    parser.add_argument("username", help="SSH username")
    parser.add_argument("commands_file", help="Path to the file with commands to execute")
    parser.add_argument("-p", "--password", help="SSH password (will prompt if not provided and key is not used)")
    parser.add_argument("-k", "--key_file", help="Path to private key file")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--parallel", action="store_true", help="Execute commands in parallel")
    parser.add_argument("--workers", type=int, help="Number of parallel workers (default: None)")
    parser.add_argument("--legacy-crypto", action="store_true", help="Enable legacy crypto for devices like Palo Alto firewalls")

    args = parser.parse_args()
    
    try:
        run_execution(args)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def run_execution(args: argparse.Namespace):
    """Handles the setup and execution of commands."""
    executor = SSHCommandExecutor(
        hostname=args.hostname,
        username=args.username,
        password=args.password,
        key_filename=args.key_file,
        port=args.port
    )

    try:
        # For sequential execution, we establish one persistent connection.
        # For parallel, workers manage their own connections.
        if not args.parallel and not executor.connect(legacy_crypto=args.legacy_crypto):
            sys.exit(1)

        success = executor.execute_commands_from_file(
            args.commands_file,
            parallel=args.parallel,
            max_workers=args.workers
        )

        if not success:
            sys.exit(1)
    finally:
        executor.disconnect()


if __name__ == "__main__":
    main()