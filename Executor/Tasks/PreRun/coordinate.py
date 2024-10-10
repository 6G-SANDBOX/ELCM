from Task import Task
from Helper import Level
from Settings import Config
from time import sleep
from Interfaces import RemoteApi
from Data import ExperimentType


class Coordinate(Task):
    def __init__(self, logMethod, parent):
        super().__init__("Coordinate", parent, None, logMethod, None)

    def Run(self):
        descriptor = self.parent.Descriptor

        if descriptor.Type == ExperimentType.Distributed:
            eastWest = Config().EastWest
            if eastWest.Enabled:
                if descriptor.RemoteDescriptor is None:  # We are the remote side
                    self.parent.RemoteId = descriptor.Extra.get('PeerId')
                else:  # We are the main side
                    remote = descriptor.Remote
                    host, port = eastWest.GetRemote(remote)
                    if host is not None:
                        remoteApi = RemoteApi(host, port)
                        self.parent.RemoteApi = remoteApi

                        self.Log(Level.INFO, f"Sending execution request to remote '{remote}'")
                        self.parent.RemoteId = remoteApi.Run(descriptor.RemoteDescriptor)

                        if self.parent.RemoteId is not None:
                            self.Log(Level.INFO, 'Remote Execution ID received.')
                        else:
                            raise RuntimeError(f"Unable to retrieve Execution ID from remote '{remote}'")
                    else:
                        raise RuntimeError(f"Unknown remote '{remote}'.")
            else:
                raise RuntimeError("Unable to run distributed experiment while East/West interface is disabled.")
        else:
            self.Log(Level.INFO, 'Not a distributed experiment, skipping coordination.')
