from typing import Dict
from .Tasks.PreRun import CheckResources, Instantiate, Coordinate
from .executor_base import ExecutorBase
from tempfile import TemporaryDirectory
from time import sleep
from Helper import Level


class PreRunner(ExecutorBase):
    def __init__(self, params: Dict, tempFolder: TemporaryDirectory = None):
        super().__init__(params, "PreRunner", tempFolder)

    def Run(self):
        self.SetStarted()

        self.AddMessage("Configuration completed", 10)

        try:
            Coordinate(self.Log, self).Start()
        except Exception as e:
            self.Log(Level.ERROR, f'Unable to continue. Coordination failed: {e}')
            raise e

        self.AddMessage("Coordination completed", 30)

        available = False
        while not available:
            parent = self.findParent()
            if parent is None or parent.Cancelled:
                # A cancelled experiment will usually be removed before reaching this point, hence the uncertainty
                raise RuntimeError("Experiment errored, cancelled or not found. Aborting")

            result = CheckResources(self.Log, self.ExecutionId, self.Configuration.Requirements,
                                    self.Configuration.NetworkServices, self).Start()
            available = result['Available']
            feasible = result['Feasible']
            if not feasible:
                self.AddMessage('Instantiation impossible. Aborting')
                self.Log(Level.ERROR,
                         'Unable to continue. Not enough total resources on VIMs for network services deployment')
                raise RuntimeError("Not enough VIM resources for experiment.")
            if not available:
                self.AddMessage('Not available')
                sleep(10)

        result = Instantiate(self.Log, self.TempFolder, self, self.Configuration.NetworkServices,
                             self.Configuration.Nest, self.Descriptor.Slice).Start()

        # Save the Slice Id (if any) for the Decommission step
        self.params['DeployedSliceId'] = result.get('DeployedSliceId', None)

        self.AddMessage('Instantiation completed', 80)

        self.SetFinished(percent=100)
