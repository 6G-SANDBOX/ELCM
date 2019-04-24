from typing import Dict
from .Tasks.PreRun import CheckAvailable, AddExperimentEntry
from .executor_base import ExecutorBase
from tempfile import TemporaryDirectory
from time import sleep


class PreRunner(ExecutorBase):
    def __init__(self, params: Dict, tempFolder: TemporaryDirectory = None):
        super().__init__(params, "PreRunner", tempFolder)

    def Run(self):
        self.SetStarted()

        self.AddMessage("Configuration completed", 30)
        available = False
        while not available:
            result = CheckAvailable(self.Log, self.Id).Start()
            available = result['Available']
            if not available:
                self.AddMessage('Not available')
                sleep(10)

        self.AddMessage('Resources granted', 80)
        AddExperimentEntry(self.Log).Start()
        self.AddMessage('Experiment registered', 80)

        self.SetFinished(percent=100)