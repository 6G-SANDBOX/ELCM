from Task import Task
import smtplib
from email.mime.text import MIMEText
from Settings import EmailConfig

class EmailNotification(Task):


    def __init__(self, logMethod, parent, params):
        super().__init__("EMAIL", parent, params, logMethod, None)
        self.paramRules = {
            'ExecutionId': (None, True),
            'EMAIL': (None, True),
            'SERVER': (None,True),
            'PORT': (None,True)
        }
    
    def Run(self):
        
        executionId = self.params['ExecutionId']
        email_info = EmailConfig()
        info = email_info.user
        email_user = info.get("User", None)
        email_password = info.get("Password", None)
        email=self.params['EMAIL']
        email_server=self.params['SERVER']
        email_port=int(self.params['PORT'])
        
        server_smtp = email_server
        port = email_port

        user = email_user
        password = email_password

        
        email_to = email
        subject = "EXPERIMENT - "+str(executionId)
        body = "EXPERIMENT "+str(executionId)+" finished"

        
        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = user
        message["To"] = email_to

        
        server = smtplib.SMTP(server_smtp, port)
        server.starttls()
        server.login(user, password)

        
        server.sendmail(user, email_to, message.as_string())
        server.quit()