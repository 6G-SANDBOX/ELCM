from Task import Task
from Helper import Level
from typing import Dict
import re


class PublishFromSource(Task):
    def __init__(self, name, parent, params, logMethod):
        super().__init__(name, parent, params, logMethod, None)
        self.paramRules = {
            'Pattern': (None, True),
            'Keys': ([], False),
            'Path': (None, False),  # Mandatory only for PublishFromFile, handled below
            'VerdictOnMatch': ("NotSet", False),
            'VerdictOnNoMatch': ("NotSet", False),
        }

    def Run(self):
        self.Log(Level.INFO, f'Running task {self.name} with params: {self.params}')

        filePath = self.params["Path"]
        pattern = self.params["Pattern"]
        keys = self.params["Keys"]
        onMatch = self.GetVerdictFromName(self.params["VerdictOnMatch"])
        onNoMatch = self.GetVerdictFromName(self.params["VerdictOnNoMatch"])

        self.Log(Level.DEBUG, f"Looking for pattern: '{pattern}'; Assigning groups as:")

        try:
            for index, key in keys:
                self.Log(Level.DEBUG, f"  {index}: {key}")
        except Exception as e:
            self.SetVerdictOnError()
            raise RuntimeError(f"Invalid 'Keys' definition: {e}")

        regex = re.compile(pattern)

        matchFound = False
        for line in self.generator({"Path": filePath}):
            match = regex.match(line)
            if match:
                self.Log(Level.INFO, f"Match found: {match.string}")
                matchFound = True
                for index, key in keys:
                    self.Publish(key, match.group(index))
        self.Verdict = onMatch if matchFound else onNoMatch

    def generator(self, params: Dict):
        raise NotImplementedError()

    def raiseConfigError(self, variable: str):
        self.SetVerdictOnError()
        raise RuntimeError(f"'{variable}' not defined, please review the Task configuration.")


class PublishFromPreviousTaskLog(PublishFromSource):
    def __init__(self, logMethod, parent, params):
        super().__init__("Publish From Previous Task Log", parent, params, logMethod)

    def generator(self, params: Dict):
        logMessages = self.parent.PreviousTaskLog
        for message in logMessages:
            yield message


class PublishFromFile(PublishFromSource):
    def __init__(self, logMethod, parent, params):
        super().__init__("Publish From File", parent, params, logMethod)

    def generator(self, params: Dict):
        filePath = params["Path"]
        if filePath is None:
            self.raiseConfigError("Path")
        with open(filePath, 'r', encoding='utf-8') as file:
            for line in file:
                yield line
