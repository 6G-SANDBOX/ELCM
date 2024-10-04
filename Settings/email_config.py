from typing import Dict, List, Tuple
from Helper.log_level import Level
from .config_base import ConfigBase, enabledLoginRestApi

class EMAIL_Api(enabledLoginRestApi):
    def __init__(self, data: Dict):
        super().__init__(data, 'EMAIL_Api', {})


class EmailConfig(ConfigBase):
    data = None
    Validation: List[Tuple['Level', str]] = []

    def __init__(self, forceReload=False):
        super().__init__('email.yml', 'Settings/default_email_config')
        if self.data is None or forceReload:
            EmailConfig.data = self.Reload()
            self.Validate()

    @property
    def EMAIL_Api(self):
        return EMAIL_Api(EmailConfig.data.get('EMAIL_Api', {}))
    
    @property
    def user(self):
        return EmailConfig.data.get('EMAIL_Api', None)
    
    def Validate(self):
        EmailConfig.Validation = []

        for entry in [self.EMAIL_Api]:
            EmailConfig.Validation.extend(entry.Validation)
