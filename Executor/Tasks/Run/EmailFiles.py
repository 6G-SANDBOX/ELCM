from Task import Task
import os
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from Settings import EmailConfig
from Helper import Level

class EmailFiles(Task):

    def __init__(self, logMethod, parent, params):
        super().__init__("EMAIL FILES", parent, params, logMethod, None)
        self.paramRules = {
            'ExecutionId': (None, True),      
            'Email': (None, True),            
            'DirectoryPath': (None, False),
            'DeleteOriginal': (False, False),
            'DeleteZip': (False, False)
        }

    def Run(self):
        
        executionId = self.params['ExecutionId']
        email_info = EmailConfig()
        info = email_info.user
        email_user = info.get("User", None)
        email_password = info.get("Password", None)
        email_port = int(info.get("Port", None))
        email_server = info.get("Server", None)
        email = self.params.get("Email", None)        
        directory_path = self.params.get("DirectoryPath") or self.parent.TempFolder
        delete_original = self.params.get("DeleteOriginal", False)
        delete_zip = self.params.get("DeleteZip", False)
        
        # Check for missing configuration or parameters
        missing_params = []
        if email_user is None:
            missing_params.append("email_user")
        if email_password is None:
            missing_params.append("email_password")
        if email_port is None:
            missing_params.append("email_port")
        if email_server is None:
            missing_params.append("email_server")
        if directory_path is None:
            missing_params.append("directory_path")
        # Return error if any parameter is missing
        if missing_params:
            self.Log(Level.ERROR, f"Missing parameters: {', '.join(missing_params)}")
            return 
         
        zip_file_path = os.path.join(directory_path, f"zip_{executionId}.zip")  # Define the path of the final ZIP file

        # Filter and collect files containing the ExecutionId in their name
        try:
            files_to_compress = []
            for foldername, subfolders, filenames in os.walk(directory_path):
                for filename in filenames:
                    if executionId in filename:
                        file_path = os.path.join(foldername, filename)
                        files_to_compress.append((file_path, os.path.relpath(file_path, directory_path)))
            
            # If no files are found, log a warning and exit
            if not files_to_compress:
                self.Log(Level.WARNING, f'No files found for ExecutionId: {executionId}')
                return

            # Create the ZIP file with the filtered files
            with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                for file_path, arcname in files_to_compress:
                    zipf.write(file_path, arcname=arcname)  # Write each file to the ZIP
            self.Log(Level.INFO, f'ZIP file created at {zip_file_path}')

        except Exception as e:
            # Log any error that occurs during the ZIP file creation
            self.Log(Level.ERROR, f'Error creating ZIP file: {e}')
            return

        # Set up email details
        server_smtp = email_server
        port = email_port
        user = email_user
        password = email_password
        email_to = email
        subject = f"EXPERIMENT - {executionId}"
        body = f"EXPERIMENT {executionId} finished"

        # Create the email message
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = user
        message["To"] = email_to

        # Attach the email body
        message.attach(MIMEText(body, 'plain'))

        # Attach the ZIP file to the email
        try:
            with open(zip_file_path, 'rb') as zip_file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(zip_file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(zip_file_path)}')
                message.attach(part)
        except Exception as e:
            self.Log(Level.ERROR, f'Error attaching file: {e}')
            return

        # Send the email: try TLS first, then SSL fallback
        try:
            server = smtplib.SMTP(server_smtp, port)
            server.starttls()
            server.login(user, password)
            server.sendmail(user, email_to, message.as_string())
            server.quit()
            self.Log(Level.INFO, f'Email successfully sent to {email_to}')
        except Exception as e_tls:
            try:
                server = smtplib.SMTP_SSL(server_smtp, port)
                server.login(user, password)
                server.sendmail(user, email_to, message.as_string())
                server.quit()
                self.Log(Level.INFO, f'Email successfully sent to {email_to}')
            except Exception as e_ssl:
                self.Log(Level.ERROR, f'Error sending email with TLS: {e_tls}; SSL fallback also failed: {e_ssl}')
                return

        if delete_original is True:
            # Delete the original files that were compressed
            try:
                for file_path, _ in files_to_compress:
                    os.remove(file_path)
                self.Log(Level.INFO, f'Original files in {directory_path} deleted.')
            except Exception as e:
                self.Log(Level.ERROR, f'Error deleting original files: {e}')

        if delete_zip is True:
            # Delete the ZIP file after sending the email
            try:
                os.remove(zip_file_path)
                self.Log(Level.INFO, f'ZIP file {zip_file_path} deleted after sending email.')
            except Exception as e:
                self.Log(Level.ERROR, f'Error deleting ZIP file: {e}')