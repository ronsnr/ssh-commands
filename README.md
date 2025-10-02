# SSH Commands Executor

A Python script that automates SSH connections and executes predefined commands from a text file on remote servers.

## Features

- Establishes SSH connections to remote servers
- Executes commands from a configurable text file
- Supports both password and key-based authentication
- Provides detailed logging and error handling
- Command-line and configuration file interfaces
- Handles command failures gracefully

## Requirements

- Python 3.6+
- paramiko library

## Installation

1. Clone this repository:
```bash
git clone https://github.com/ronsnr/ssh-commands.git
cd ssh-commands
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Method 1: Command Line Interface

```bash
python ssh_executor.py <hostname> <username> <commands_file> [password] [key_file] [port]
```

**Examples:**

Using password authentication (password will be prompted):
```bash
python ssh_executor.py 192.168.1.100 myuser commands.txt
```

Using SSH key authentication:
```bash
python ssh_executor.py 192.168.1.100 myuser commands.txt '' ~/.ssh/id_rsa
```

Using custom port:
```bash
python ssh_executor.py 192.168.1.100 myuser commands.txt '' ~/.ssh/id_rsa 2222
```

### Method 2: Configuration File Interface

1. Create a configuration file by running:
```bash
python ssh_executor_config.py
```

2. Edit the generated `config.json` file with your connection details:
```json
{
    "hostname": "your-server-ip-or-hostname",
    "username": "your-username",
    "password": "your-password-or-leave-empty-for-key-auth",
    "key_filename": "/path/to/your/private/key",
    "port": 22,
    "commands_file": "commands.txt"
}
```

3. Run the script:
```bash
python ssh_executor_config.py
```

## Commands File Format

The `commands.txt` file contains the commands to execute on the remote server. Format rules:

- One command per line
- Lines starting with `#` are treated as comments and ignored
- Empty lines are ignored
- Commands are executed in the order they appear

**Example commands.txt:**
```bash
# System information
whoami
hostname
uname -a

# Directory listing
ls -la
pwd

# System resources
df -h
free -m
```

## Authentication Methods

### Password Authentication
The script will prompt for the password during execution.

### SSH Key Authentication
Set the `key_filename` field in config.json to point to your private key file, or pass it as a command line argument. Leave the password field empty when using key authentication.

## Error Handling

The script includes comprehensive error handling for:

- SSH connection failures
- Authentication errors
- Command execution failures
- File not found errors
- Network connectivity issues

All operations are logged with timestamps and appropriate log levels.

## Security Considerations

- Store SSH keys securely with appropriate file permissions (600)
- Avoid storing passwords in configuration files in production
- Use key-based authentication when possible
- Consider using SSH agent for key management
- Validate commands before execution to prevent security issues

## Output

The script provides:

- Real-time command execution status
- STDOUT and STDERR output from each command
- Success/failure count summary
- Detailed logging information

## Example Output

```
2024-01-15 10:30:00,123 - INFO - Connecting to 192.168.1.100:22 as myuser
2024-01-15 10:30:01,456 - INFO - SSH connection established successfully
2024-01-15 10:30:01,457 - INFO - Loaded 5 commands from commands.txt
2024-01-15 10:30:01,458 - INFO - Executing command 1/5
2024-01-15 10:30:01,459 - INFO - Executing command: whoami
2024-01-15 10:30:01,678 - INFO - Command executed successfully (exit code: 0)
STDOUT:
myuser

2024-01-15 10:30:02,180 - INFO - Execution complete: 5/5 commands successful
All commands executed successfully
2024-01-15 10:30:02,181 - INFO - SSH connection closed
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. See the repository for license details.