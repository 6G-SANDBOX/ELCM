from typing import Dict, List, Tuple
from Helper.log_level import Level
from .config_base import ConfigBase, enabledLoginRestApi

class KAFKA_Api(enabledLoginRestApi):
    def __init__(self, data: Dict):
        super().__init__(data, 'KAFKA_Api', {})


class KAFKAConfig(ConfigBase):
    data=None
    Validation: List[Tuple['Level', str]] = []

    def __init__(self, forceReload=False):
        super().__init__('KAFKA.yml', 'Settings/default_kafka_config')
        if self.data is None or forceReload:
            KAFKAConfig.data = self.Reload()
            self.Validate()
    @property
    def KAFKA_Api(self):
        return KAFKA_Api(KAFKAConfig.data.get('KAFKA_Api', {}))
    
    @property
    def user(self):
        return KAFKAConfig.data.get('KAFKA_Api', None)
    
    def Validate(self):
        KAFKAConfig.Validation = []

        for entry in [self.KAFKA_Api]:
            KAFKAConfig.Validation.extend(entry.Validation)