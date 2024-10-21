import yaml
from os.path import exists
from shutil import copy
from typing import Dict, List, Tuple, Optional
from Helper.log_level import Level
from REST import RestClient


class validable:
    def __init__(self, data: Dict, section: str,
                 defaults: Dict[str, Tuple[Optional[object], "Level"]]):
        self.data = data
        self.section = section
        self.defaults = defaults

    def _keyOrDefault(self, key: str):
        if key in self.data.keys():
            return self.data[key]
        else:
            default = self.defaults.get(key, None)
            return default[0] if default is not None else None

    @property
    def Validation(self) -> List[Tuple['Level', str]]:
        res = []
        for key in self.defaults.keys():
            if key not in self.data:
                default, level = self.defaults[key]
                defaultText = f", using default '{default}'" if default is not None else ""
                res.append((level, f"'{key}' not defined under '{self.section}'{defaultText}"))
        if len(res) == 0:
            values = '; '.join([f'{key}: {self.data[key]}' for key in self.defaults.keys()])
            res.append((Level.INFO, f'{self.section} [{values}]'))
        return res


class restApi(validable):
    def __init__(self, data: Dict, section: str, defaults: Dict[str, Tuple[Optional[object], "Level"]]):
        if 'Host' not in defaults.keys(): defaults['Host'] = (None, Level.ERROR)
        if 'Port' not in defaults.keys(): defaults['Port'] = (None, Level.ERROR)
        super().__init__(data, section, defaults)

    @property
    def Host(self):
        return self._keyOrDefault('Host')

    @property
    def Port(self):
        return self._keyOrDefault('Port')

    @property
    def Validation(self) -> List[Tuple['Level', str]]:
        res = super().Validation
        if all([e[0] == Level.INFO for e in res]):
            # No errors, but check if a rest server can be created with the configuration
            try:
                _ = RestClient(self.Host, self.Port if self.Port is not None else 80, "")
            except Exception as e:
                res.append((Level.ERROR, f'Exception creating {self.section} client: {e}'))
        return res


class loginRestApi(restApi):
    def __init__(self, data: Dict, section: str, defaults: Dict[str, Tuple[Optional[object], "Level"]]):
        if section == 'InfluxDb V2':
            super().__init__(data, section, defaults)
        else:
            if 'User' not in defaults.keys(): defaults['User'] = (None, Level.ERROR)
            if 'Password' not in defaults.keys(): defaults['Password'] = (None, Level.ERROR)
            super().__init__(data, section, defaults)

    @property
    def User(self):
        return self._keyOrDefault('User')

    @property
    def Password(self):
        return self._keyOrDefault('Password')


class enabledLoginRestApi(loginRestApi):
    def __init__(self, data: Dict, section: str, defaults: Dict):
        if 'Enabled' not in defaults.keys(): defaults['Enabled'] = (False, Level.WARNING)
        super().__init__(data, section, defaults)

    @property
    def Enabled(self):
        return self._keyOrDefault('Enabled')

    @property
    def Validation(self) -> List[Tuple['Level', str]]:
        if self.Enabled:
            return super().Validation
        else:
            return [(Level.INFO, f"{self.section} is disabled")]


class ConfigBase:
    def __init__(self, filename: str, defaultsFile: str):
        self.filename = filename
        self.defaultsFile = defaultsFile

    def Reload(self) -> Dict:
        if not exists(self.filename):
            copy(self.defaultsFile, self.filename)

        try:
            with open(self.filename, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except Exception as e:
            from Helper import Log
            Log.C(f"Exception while loading {self.filename} file: {e}")
            return {}

    def Validate(self):
        raise NotImplementedError
