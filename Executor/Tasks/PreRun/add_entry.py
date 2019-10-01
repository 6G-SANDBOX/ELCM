from Task import Task
from Helper import Level
from time import sleep


class AddExecutionEntry(Task):
    def __init__(self, logMethod):
        super().__init__("Add Execution Entry", None, logMethod, None)

    def Run(self):
        self.Log(Level.INFO, 'Sending entry information')
        sleep(3)
        self.Log(Level.INFO, 'Information sent')
