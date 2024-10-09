from typing import Dict, List, Tuple
from Helper.log_level import Level
from .config_base import ConfigBase, enabledLoginRestApi

class MQTT_Api(enabledLoginRestApi):
    def __init__(self, data: Dict):
        super().__init__(data, 'MQTT_Api', {})


class MQTTConfig(ConfigBase):
    data=None
    Validation: List[Tuple['Level', str]] = []

    def __init__(self, forceReload=False):
        super().__init__('MQTT.yml', 'Settings/default_mqtt_config')
        if self.data is None or forceReload:
            MQTTConfig.data = self.Reload()
            self.Validate()
    @property
    def MQTT_Api(self):
        return MQTT_Api(MQTTConfig.data.get('MQTT_Api', {}))
    
    @property
    def user(self):
        return MQTTConfig.data.get('MQTT_Api', None)
    
    def Validate(self):
        MQTTConfig.Validation = []

        for entry in [self.MQTT_Api]:
            MQTTConfig.Validation.extend(entry.Validation)