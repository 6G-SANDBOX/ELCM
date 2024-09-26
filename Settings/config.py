from os.path import exists, abspath, realpath, join
from os import getenv
from typing import Dict, List, Tuple, Optional
import logging
import platform
from Helper.log_level import Level
from .config_base import validable, restApi, enabledLoginRestApi, ConfigBase


class Grafana(restApi):
    def __init__(self, data: Dict):
        defaults = {
            'Enabled': (False, Level.WARNING),
            'Bearer': ('', Level.WARNING),
            'ReportGenerator': ('', Level.WARNING)
        }
        super().__init__(data, "Grafana", defaults)

    @property
    def Enabled(self):
        return self._keyOrDefault('Enabled')

    @property
    def Bearer(self):
        return self._keyOrDefault('Bearer')

    @property
    def ReportGenerator(self):
        return self._keyOrDefault('ReportGenerator')

    @property
    def Validation(self) -> List[Tuple['Level', str]]:
        if not self.Enabled:
            return [(Level.INFO, "Grafana is disabled")]
        else:
            return super().Validation


class EastWest(validable):
    def __init__(self, data: Dict):
        defaults = {'Enabled': (False, Level.WARNING), 'Timeout': (120, Level.INFO)}
        super().__init__(data, 'EastWest', defaults)

    @property
    def Enabled(self):
        return self._keyOrDefault('Enabled')

    @property
    def Timeout(self):
        return self._keyOrDefault('Timeout')

    def GetRemote(self, name: str) -> Tuple[Optional[str], Optional[int]]:
        if self.Enabled:
            remotes = self.data.get('Remotes', {})
            if name in remotes.keys():
                remote = remotes[name]
                return remote.get('Host', None), remote.get('Port', None)
        return None, None


class TapConfig(validable):
    def __init__(self, data: Dict):
        defaults = {
            'Enabled': (False, Level.WARNING),
            'OpenTap': (True, Level.WARNING),
            'Exe': ('tap.exe', Level.WARNING),
            'Folder': ('C:/Program Files/OpenTAP', Level.WARNING),
            'Results': ('C:/Program Files/OpenTAP/Results', Level.WARNING),
            'EnsureClosed': (False, Level.WARNING),
            'EnsureAdbClosed': (False, Level.WARNING),
        }
        super().__init__(data, 'Tap', defaults)

    @property
    def Enabled(self):
        return self._keyOrDefault('Enabled')

    @property
    def OpenTap(self):
        return self._keyOrDefault('OpenTap')

    @property
    def Exe(self):
        return self._keyOrDefault('Exe')

    @property
    def Folder(self):
        return self._keyOrDefault('Folder')

    @property
    def Results(self):
        return self._keyOrDefault('Results')

    @property
    def EnsureClosed(self):
        return self._keyOrDefault('EnsureClosed')

    @property
    def EnsureAdbClosed(self):
        return self._keyOrDefault('EnsureAdbClosed')

    @property
    def Path(self): return realpath(join(self.Folder, self.Exe))

    @property
    def Validation(self) -> List[Tuple['Level', str]]:
        if not self.Enabled:
            if 'Enabled' in self.data.keys():
                return [(Level.INFO, "TAP is disabled")]
            else:
                return [(Level.ERROR, "'Enabled' key not in 'Tap' configuration. Assuming Disabled.")]
        else:
            return super().Validation


class Portal(restApi):
    def __init__(self, data: Dict):
        defaults = {
            'Enabled': (False, Level.WARNING)
        }
        super().__init__(data, 'Portal', defaults)

    @property
    def Enabled(self):
        return self._keyOrDefault('Enabled')

    @property
    def Validation(self) -> List[Tuple['Level', str]]:
        if self.Enabled:
            return super().Validation
        else:
            return [(Level.INFO, "Portal is disabled")]


class SliceManager(restApi):
    def __init__(self, data: Dict):
        super().__init__(data, 'SliceManager', {})


class InfluxDb(enabledLoginRestApi):
    def __init__(self, data: Dict):
        defaults = {
            'Database': (None, Level.ERROR),
        }
        super().__init__(data, 'InfluxDb', defaults)

    @property
    def Database(self):
        return self._keyOrDefault('Database')


class Logging(validable):
    def __init__(self, data: Dict):
        defaults = {
            'Folder': ('Logs', Level.WARNING),
            'AppLevel': ('info', Level.WARNING),
            'LogLevel': ('debug', Level.WARNING)
        }
        super().__init__(data, 'Logging', defaults)

    @staticmethod
    def toLogLevel(level: Optional[str]) -> int:
        if level is None or level.lower() == 'debug': return logging.DEBUG
        if level.lower() == 'info': return logging.INFO
        if level.lower() == 'warning': return logging.WARNING
        if level.lower() == 'error': return logging.ERROR
        return logging.CRITICAL

    @property
    def Folder(self):
        folder = self._keyOrDefault("Folder")
        return abspath(folder)

    @property
    def AppLevel(self):
        return self.toLogLevel(self._keyOrDefault("AppLevel"))

    @property
    def LogLevel(self):
        return self.toLogLevel(self._keyOrDefault("LogLevel"))


class Metadata(validable):
    def __init__(self, data: Dict):
        defaults = {
            "HostIp": ("127.0.0.1", Level.INFO),
            "Facility": ("", Level.INFO),
        }
        super().__init__(data, 'Metadata', defaults)

        self.HostName = platform.node()

    @property
    def HostIp(self): return self._keyOrDefault("HostIp")

    @property
    def Facility(self): return self._keyOrDefault("Facility")


class Config(ConfigBase):
    FILENAME = 'config.yml'

    data = None
    Validation: List[Tuple['Level', str]] = []

    def __init__(self, forceReload = False):
        super().__init__('config.yml', 'Settings/default_config')
        if self.data is None or forceReload:
            Config.data = self.Reload()
            self.Validate()

    @property
    def Logging(self):
        return Logging(Config.data.get('Logging', {}))

    @property
    def Portal(self):
        return Portal(Config.data.get('Portal', {}))

    @property
    def TempFolder(self):
        return Config.data.get('TempFolder', 'Temp')

    @property
    def ResultsFolder(self):
        return Config.data.get('ResultsFolder', 'Results')

    @property
    def VerdictOnError(self):
        return Config.data.get('VerdictOnError', 'Error')

    @property
    def Tap(self):
        return TapConfig(Config.data.get('Tap', {}))

    @property
    def Grafana(self):
        return Grafana(Config.data.get('Grafana', {}))

    @property
    def SliceManager(self):
        return SliceManager(Config.data.get('SliceManager', {}))

    @property
    def InfluxDb(self):
        return InfluxDb(Config.data.get('InfluxDb', {}))

    @property
    def Metadata(self):
        return Metadata(Config.data.get('Metadata', {}))

    @property
    def EastWest(self):
        return EastWest(Config.data.get('EastWest', {}))

    def Validate(self):
        def _validateSingle(key: str, default: str):
            if key not in Config.data:
                Config.Validation.append((Level.INFO, f"{key} not defined, using '{default}'"))

        Config.Validation = []
        keys = set(Config.data.keys())
        keys.discard('Flask')
        keys.discard('TempFolder')
        keys.discard('ResultsFolder')
        keys.discard('VerdictOnError')

        if getenv('SECRET_KEY') is None:
            Config.Validation.append((Level.CRITICAL,
                                      "SECRET_KEY not defined. Use environment variables or set a value in .flaskenv"))

        for key, default in [('TempFolder', 'Temp'), ('ResultsFolder', 'Results'), ('VerdictOnError', 'Error')]:
            _validateSingle(key, default)

        for entry in [self.Logging, self.Portal, self.SliceManager, self.Tap,
                      self.Grafana, self.InfluxDb, self.Metadata, self.EastWest, ]:
            Config.Validation.extend(entry.Validation)
            keys.discard(entry.section)

        if len(keys) != 0:
            Config.Validation.append((Level.WARNING, f"Unrecognized keys found: {(', '.join(keys))}"))
