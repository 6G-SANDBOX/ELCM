from Task import Task
from Helper import Level
from time import sleep


class RequestResults(Task):
    def __init__(self, logMethod):
        super().__init__("Request Results", None, logMethod, None)

    def Run(self):
        self.Log(Level.INFO, 'Requesting execution results')
        sleep(3)
        self.Log(Level.INFO, 'Completed')
