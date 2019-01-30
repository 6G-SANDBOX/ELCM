from Helper import Child, Level
from typing import Dict
from time import sleep
from datetime import datetime
from .api import Api
from enum import Enum, unique


@unique
class Status(Enum):
    Init, Waiting, Running, Cancelled, Errored, Finished = range(6)

    def label(self):
        if self.name == 'Cancelled': return 'label-warning'
        if self.name == 'Errored': return 'label-danger'
        if self.name == 'Finished': return 'label-success'
        return 'label-info'


class Executor(Child):
    api = None

    def __init__(self, params: Dict):
        now = datetime.utcnow()
        super().__init__(f"Executor{now.strftime('%y%m%d%H%M%S%f')}")
        self.params = params
        self.Id = params['Id']
        self.Created = now
        self.Started = None
        self.Finished = None
        self.Status = Status.Init

        if self.api is None: self.api=Api('127.0.0.1', '5000')

    def Run(self):
        self.Log(Level.INFO, "Starting")
        self.Started = datetime.utcnow()
        self.api.NotifyStart(self.Id)
        self.Status = Status.Running
        
        for _ in range(1, 30):
            if self.stopRequested:
                self.Log(Level.INFO, "Received stop request, exiting")
                self.Status = Status.Cancelled
                break
            self.Log(Level.DEBUG, 'Ping')
            sleep(1)
        else:
            self.Status = Status.Finished

        self.Finished = datetime.utcnow()
        self.api.NotifyStop(self.Id)
        self.Log(Level.INFO, "Exited")


