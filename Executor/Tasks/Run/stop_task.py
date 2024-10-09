from Task import Task
from Helper import utils

class StopTask(Task):


    def __init__(self, logMethod, parent, params):
        super().__init__("STOP_TASK", parent, params, logMethod, None)
        self.paramRules = {
            
            'ExecutionId': (None, True),
            'Name': (None, True)
        }
    

    def Run(self):

        new_task=self.params['Name']+"_"+str(self.params['ExecutionId'])
        utils.task_list.append(new_task)