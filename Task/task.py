from typing import Callable, Dict, Optional, Union, Tuple, Any, List
from Helper import Log, Level
from Settings import Config


class Task:
    def __init__(self, name: str, parent, params: Optional[Dict] = None,
                 logMethod: Optional[Callable] = None,
                 conditionMethod: Optional[Callable] = None):
        from Executor import ExecutorBase, Verdict
        from Composer import TaskDefinition

        self.name = name
        self.params = {} if params is None else params
        self.paramRules: Dict[str, Tuple[Any, bool]] = {}  # Dict[<ParameterName>: (<Default>, <Mandatory>)]
        self.parent: ExecutorBase = parent
        self.logMethod = Log.Log if logMethod is None else logMethod
        self.condition = conditionMethod
        self.Vault = {}
        self.LogMessages = []
        self.Verdict = Verdict.NotSet
        self.Label = None
        self.Children: List[TaskDefinition] = []

    def Start(self) -> Dict:
        from Executor import Verdict

        if self.Label is None:
            self.Label = self.name

        identifier = self.name if self.Label is None else f'{self.Label}({self.name})'
        if self.condition is None or self.condition():
            self.Log(Level.INFO, f"[Starting Task '{identifier}']")
            self.Log(Level.DEBUG, f'Params: {self.params}')
            if self.SanitizeParams():
                self.Run()
                self.Log(Level.INFO, f"[Task '{identifier}' finished (verdict: '{self.Verdict.name}')]")
            else:
                message = f"[Task '{identifier}' aborted due to incorrect parameters ({self.params})]"
                self.Log(Level.ERROR, message)
                self.Verdict = Verdict.Error
                raise RuntimeError(message)
            self.Log(Level.DEBUG, f'Params: {self.params}')
        else:
            self.Log(Level.INFO, f"[Task '{identifier}' not started (condition false)]")
        return self.params

    def Publish(self, key: str, value: object):
        self.Log(Level.DEBUG, f'Published value "{value}" under key "{key}"')
        self.Vault[key] = value

    def Run(self) -> None:
        raise NotImplementedError

    def Log(self, level: Union[Level, str], msg: str):
        self.logMethod(level, f"{self.Label}||{msg}")
        self.LogMessages.append(msg)

    def SanitizeParams(self):
        for key, value in self.paramRules.items():
            default, mandatory = value
            if key not in self.params.keys():
                if mandatory:
                    self.Log(Level.ERROR, f"Parameter '{key}' is mandatory but was not configured for the task.")
                    return False
                else:
                    self.params[key] = default
                    self.Log(Level.DEBUG, f"Parameter '{key}' set to default ({str(default)}).")
        return self.inDepthSanitizeParams()

    def inDepthSanitizeParams(self):
        return True  # Allow subclasses to perform extra checks on the parameters when needed

    def SetVerdictOnError(self):
        from Executor import Verdict
        verdict = self.params.get('VerdictOnError', None)
        if verdict is None:
            verdict = Config().VerdictOnError
        try:
            self.Verdict = Verdict[verdict]
        except KeyError as e:
            raise RuntimeError(f"Unrecognized Verdict '{verdict}'") from e

    def GetVerdictFromName(self, name: str):
        from Executor import Verdict
        try:
            return Verdict[name]
        except KeyError:
            self.SetVerdictOnError()
            self.Log(Level.ERROR, f"Unrecognized Verdict '{name}'")
            return None
