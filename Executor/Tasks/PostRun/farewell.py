from Task import Task
from Helper import Level
from Settings import Config
from time import sleep
from Interfaces import RemoteApi
from Data import ExperimentType


class Farewell(Task):
    def __init__(self, logMethod, parent):
        super().__init__("Farewell", parent, None, logMethod, None)

    def Run(self):

        descriptor = self.parent.Descriptor
        if descriptor.Type == ExperimentType.Distributed:
            eastWest = Config().EastWest
            if eastWest.Enabled:
                from Experiment import ExperimentStatus

                remoteApi: RemoteApi = self.parent.RemoteApi
                remoteId = self.parent.RemoteId

                self.Log(Level.INFO, "Waiting for remote side to reach Post-Run (or higher)")
                status = ExperimentStatus.Init
                retries = 5

                while status.value < ExperimentStatus.PostRun.value and retries > 0:
                    status, _ = remoteApi.GetStatus(remoteId)
                    if status is None:
                        self.Log(Level.WARNING, f"Could not retrieve status from remote side (Retries: {retries})")
                        status = ExperimentStatus.Init
                        retries -= 1
                        sleep(5)

                if status.value >= ExperimentStatus.PostRun.value:
                    self.Log(Level.INFO, f"Remote side finished Run stage with status {status.name}")
                else:
                    self.Log(Level.ERROR, "Could not coordinate execution end with remote. " 
                                          "Remote side results may be inconsistent.")
            else:
                raise RuntimeError("Unable to run distributed experiment while East/West interface is disabled.")
        else:
            self.Log(Level.INFO, 'Not a distributed experiment, skipping farewell.')
