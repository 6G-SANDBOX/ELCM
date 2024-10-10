from Task import Task
from Helper import Level
import paramiko

class CliSsh(Task):
    def __init__(self, logMethod, parent, params):
        
        super().__init__("CLI SSH", parent, params, logMethod, None)
        self.paramRules = {
            'Hostname': (None, True),          # Hostname of the SSH server (required)
            'Port': (22, False),               # SSH port (default is 22)
            'Username': (None, True),          # Username for SSH connection (required)
            'Certificate': (None, True),       # Path to the private key (required)
            'Command': (None, True)            # Command to execute (required)
        }

    def Run(self):
        hostname = self.params['Hostname']
        port = self.params['Port']
        username = self.params['Username']
        certificate_path = self.params['Certificate']
        command = self.params['Command']
        # Create an SSH client
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Load the private key
            private_key = paramiko.RSAKey.from_private_key_file(certificate_path)
            # Connect to the server using the private key
            client.connect(hostname=hostname, port=port, username=username, pkey=private_key)
            # Execute the command
            stdin, stdout, stderr = client.exec_command(command)
            output = stdout.read().decode('utf-8', errors='ignore').splitlines()  
            error_output = stderr.read().decode('utf-8', errors='ignore').splitlines()  

            if output:
                self.Log(Level.INFO, "Output:")
                self.Log(Level.INFO, "\n")
                for line in output:
                    self.Log(Level.INFO, line)
                self.Log(Level.INFO, "\n")
            if error_output:
                self.Log(Level.ERROR, "Error Output:")
                self.Log(Level.ERROR, "\n")
                for line in error_output:
                    self.Log(Level.ERROR, line)
                self.Log(Level.ERROR, "\n")


        except paramiko.AuthenticationException:
            # Log authentication errors
            self.Log(Level.ERROR, "Authentication failed, please verify your credentials.")
        except paramiko.SSHException as sshException:
            # Log SSH-related errors
            self.Log(Level.ERROR, f"SSH error: {str(sshException)}")
        except Exception as e:
            self.Log(Level.ERROR, f"Connection or execution error: {str(e)}")
        finally:
            # Close the SSH connection
            client.close()