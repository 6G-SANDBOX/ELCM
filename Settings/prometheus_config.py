from typing import Dict, List, Tuple
from Helper.log_level import Level
from .config_base import ConfigBase, enabledLoginRestApi

class PROMETHEUS_Api(enabledLoginRestApi):
    def __init__(self, data: Dict):
        super().__init__(data, 'PROMETHEUS_Api', {})


class PROMETHEUSConfig(ConfigBase):
    data=None
    Validation: List[Tuple['Level', str]] = []

    def __init__(self, forceReload=False):
        super().__init__('PROMETHEUS.yml', 'Settings/default_prometheus_config')
        if self.data is None or forceReload:
            PROMETHEUSConfig.data = self.Reload()
            self.Validate()
    @property
    def PROMETHEUS_Api(self):
        return PROMETHEUS_Api(PROMETHEUSConfig.data.get('PROMETHEUS_Api', {}))
    
    @property
    def user(self):
        return PROMETHEUSConfig.data.get('PROMETHEUS_Api', None)
    
    def Validate(self):
        PROMETHEUSConfig.Validation = []

        for entry in [self.PROMETHEUS_Api]:
            PROMETHEUSConfig.Validation.extend(entry.Validation)