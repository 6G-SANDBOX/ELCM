from Task import Task
from Helper import utils

cola=utils.cola

class stop_task(Task):


    def __init__(self, logMethod, parent, params):
        super().__init__("STOP_TASK", parent, params, logMethod, None)
        self.paramRules = {
            
            'ExecutionId': (None, True),
            'NAME': (None, True)
        }
    

    def Run(self):

        cola.put_nowait(self.params['NAME']+"_"+str(self.params['ExecutionId']))